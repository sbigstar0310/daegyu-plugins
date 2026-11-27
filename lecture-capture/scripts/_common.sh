# Sourced by the other scripts (zsh). Resolves plugin paths and per-lecture state.
ROOT=${0:A:h:h}
BIN=$ROOT/bin
AUDIOTEE=$BIN/audiotee
WINREC=$BIN/winrec2
MLX=${commands[mlx_whisper]:-$HOME/.local/bin/mlx_whisper}
WHISPER_MODEL=${LECTURE_WHISPER_MODEL:-mlx-community/whisper-large-v3-turbo}
WHISPER_LANG=${LECTURE_LANG:-ko}
SEGMENT_SEC=300
MIDDIR=intermediate   # per-lecture subfolder for intermediate files; merge.py's MID must match

# Whisper on silence hallucinates "감사합니다"/"Thank you"; these flags suppress most of it.
whisper() {  # whisper <wav> <outdir> [extra args...]
  local wav=$1 out=$2; shift 2
  $MLX $wav --model $WHISPER_MODEL --language $WHISPER_LANG --output-dir $out --verbose False \
    --hallucination-silence-threshold 2 --condition-on-previous-text False "$@" >/dev/null 2>&1
}

lecture_dir() {  # lecture_dir [dir] -> absolute dir (default ~/Desktop/lecture_YYYYMMDD_HHMM)
  local d=${1:-${LECTURE_ROOT:-$HOME/Desktop}/lecture_$(date +%Y%m%d_%H%M)}
  print -r -- ${d:A}
}

pid_of() {  # pid_of <dir> <name>  -> pid from <dir>/.pids, empty if absent
  [[ -f $1/.pids ]] && sed -n "s/^$2=//p" $1/.pids | tail -1
}

alive() { [[ -n $1 ]] && kill -0 $1 2>/dev/null }

mean_db() {  # mean_db <wav or raw s16le with -raw>
  if [[ $2 == -raw ]]; then
    ffmpeg -hide_banner -f s16le -ar 16000 -ac 1 -i $1 -af volumedetect -f null - 2>&1
  else
    ffmpeg -hide_banner -i $1 -af volumedetect -f null - 2>&1
  fi | sed -n 's/.*mean_volume: \([-0-9.inf]*\) dB.*/\1/p'
}

existing_dir() {  # existing_dir [dir] -> given dir, else the newest ~/Desktop/lecture_* that has .pids
  if [[ -n $1 ]]; then print -r -- ${1:A}; return; fi
  local c=(${LECTURE_ROOT:-$HOME/Desktop}/lecture_*/.pids(N.om))
  [[ -n $c ]] && print -r -- ${c[1]:h} || { echo "녹음 폴더를 찾을 수 없음" >&2; return 1; }
}

python_is_usable() {  # false if python3 is missing or is macOS's /usr/bin/python3 stub on a Mac without Xcode CLT (running it opens an installer)
  local py=$(command -v python3)
  [[ -n $py ]] || return 1
  [[ $py != /usr/bin/python3 ]] || xcode-select -p >/dev/null 2>&1
}

run_python() {  # run_python <script> [args...] — python3 when usable, else a Python that uv manages (downloaded once)
  if python_is_usable; then python3 -I "$@"
  else uv run --no-project --managed-python python -I "$@"; fi
}

meeting_window() {  # true if the Zoom meeting window is up. Asks Accessibility (System Events), never
  # ScreenCaptureKit: a `winrec2 --size` query kills a live capture stream (-3805, issue #41), so this is
  # what every caller uses, recording or not. Without Accessibility permission it falls back to SCK.
  local t q= r p=${LECTURE_AX_PROCESS:-zoom.us}
  pgrep -xq $p || return 1   # not running: asking System Events about a missing process stalls for 10-40 s
  for t in "${(@s:|:)${LECTURE_WINDOW_TITLE:-Zoom 회의|Zoom Meeting}}"; do q+="${q:+ or }(exists window \"$t\")"; done
  r=$(osascript -e "tell application \"System Events\" to tell process \"$p\" to ($q)" 2>&1)
  case $r in
    true) return 0 ;;
    false|*-1728*|*-600*) return 1 ;;   # no window / the app isn't running
    *) meeting_window_sck ;;            # no Accessibility permission: the old check
  esac
}

meeting_window_sck() {  # ScreenCaptureKit window lookup. Never call it while a capture is running.
  local t
  for t in "${(@s:|:)${LECTURE_WINDOW_TITLE:-Zoom 회의|Zoom Meeting}}"; do
    $WINREC --size ${LECTURE_WINDOW_OWNER:-Zoom} $t 1280 >/dev/null 2>&1 && return 0
  done
  return 1
}

progress_frame() {  # progress_frame <ffmpeg -progress file> -> last frame count, 0 if none yet
  local f=0
  [[ -r $1 ]] && f=$(grep -a '^frame=' $1 2>/dev/null | tail -1 | cut -d= -f2)
  print -r -- ${f:-0}
}

stall_secs() {  # stall_secs <prev frame> <cur frame> <secs without new frames> <step> -> new secs without frames
  (( $2 != $1 )) && print 0 || print $(( $3 + $4 ))
}

epoch_at() {  # epoch_at HH:MM[:SS] -> epoch seconds for that time today
  local t=$1; [[ $t == *:*:* ]] || t+=":00"   # date -j fills unparsed fields from now, so give it the seconds
  date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%Y-%m-%d) $t" +%s
}

# Zoom's meeting window shows no toolbar buttons to Accessibility, but the 회의/Meeting menu always
# names the action, which gives the state away: "오디오 음소거" (mute) is listed while the mic is on.
zoom_av_state() {  # zoom_av_state <menu item names...> -> "mic:on|off|none|unknown cam:on|off|unknown"
  local mic=unknown cam=unknown i
  for i in "$@"; do
    case ${i:l} in
      "오디오 음소거"|"mute audio"|"mute") mic=on ;;
      "오디오 음소거 해제"|"unmute audio"|"unmute") mic=off ;;
      "오디오 연결"|"오디오 참가"|"join audio"|"connect audio") [[ $mic == unknown ]] && mic=none ;;
      "비디오 중지"|"stop video") cam=on ;;
      "비디오 시작"|"start video") cam=off ;;
    esac
  done
  print -r -- "mic:$mic cam:$cam"
}

av_is_off() {  # av_is_off "<zoom_av_state output>" -> true only if the camera is off and the mic is off or not connected
  [[ $1 == (mic:off|mic:none)" cam:off" ]]
}

join_gate() {  # join_gate <now> <until> <meeting window up 0|1> -> join | wait | giveup
  # A meeting window that is up before we join belongs to another meeting: never record or close it.
  if (( $3 == 0 )); then print join
  elif (( $1 < $2 )); then print wait
  else print giveup; fi
}

warn_due() {  # warn_due <now> <warn epoch or ""> <joined 0|1> -> true when the "not in yet" alert should fire
  [[ -n $2 ]] && (( $1 >= $2 && $3 == 0 ))
}

log() { print -r -- "[$(date +%H:%M:%S)] $*" }
