# Sourced by the other scripts (zsh). Resolves plugin paths and per-lecture state.
ROOT=${0:A:h:h}
BIN=$ROOT/bin
AUDIOTEE=$BIN/audiotee
WINREC=$BIN/winrec2
MLX=${commands[mlx_whisper]:-$HOME/.local/bin/mlx_whisper}
WHISPER_MODEL=${LECTURE_WHISPER_MODEL:-mlx-community/whisper-large-v3-turbo}
WHISPER_LANG=${LECTURE_LANG:-ko}
SEGMENT_SEC=300

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
