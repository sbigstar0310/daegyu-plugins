#!/bin/zsh
# doctor.sh [--quick] [--warm] — check, before a lecture, that everything is installed and working.
#   --quick  skip the 5 s audio test and the Whisper test (static checks only, no sound is played)
#   --warm   also download the Whisper model now if it is not cached yet
# Exit 0 = ready (warnings allowed), 1 = something that blocks recording is missing or broken.
# Safe while a lecture is recording: it opens no capture stream on the Zoom window (only the
# size query) and skips the audio test then, because the test tone would end up in the recording.
setopt nullglob
source ${0:A:h}/_common.sh
autoload -U is-at-least

quick=0 warm=0
for a in "$@"; do
  case $a in
    --quick) quick=1 ;;
    --warm) warm=1 ;;
    *) echo "usage: doctor.sh [--quick] [--warm]"; exit 2 ;;
  esac
done

G= R= Y= N=
[[ -t 1 ]] && { G=$'\e[32m' R=$'\e[31m' Y=$'\e[33m' N=$'\e[0m' }
fails=0 warns=0
ok()   { print -r -- "${G}✓${N} $1" }
bad()  { print -r -- "${R}✗${N} $1"; [[ -n $2 ]] && print -r -- "    → $2"; fails=$(( fails + 1 )) }
warn() { print -r -- "${Y}!${N} $1"; [[ -n $2 ]] && print -r -- "    → $2"; warns=$(( warns + 1 )) }
head_() { print -r -- ""; print -r -- "$1" }

OUT_ROOT=${LECTURE_ROOT:-$HOME/Desktop}

# A lecture is recording if any lecture folder has a live audiotee pid.
recording=
for p in $OUT_ROOT/lecture_*/.pids; do
  alive "$(pid_of ${p:h} audiotee)" && { recording=${p:h}; break }
done

head_ "시스템"
[[ $(uname -m) == arm64 ]] && ok "Apple Silicon" \
  || bad "Apple Silicon이 아닙니다 ($(uname -m))" "mlx-whisper는 Apple Silicon에서만 돌아갑니다"
ver=$(sw_vers -productVersion)
is-at-least 14.2 $ver && ok "macOS $ver (14.2 이상)" \
  || bad "macOS $ver: 14.2 이상이 필요합니다" "시스템 오디오 tap(Core Audio tap)이 14.2부터 있습니다"

head_ "도구"
if command -v ffmpeg >/dev/null; then
  ok "ffmpeg $(ffmpeg -version 2>/dev/null | sed -n '1s/^ffmpeg version \([^ ]*\).*/\1/p')"
  ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264 \
    && ok "ffmpeg에 libx264 인코더 있음" \
    || bad "ffmpeg에 libx264 인코더가 없습니다" "brew reinstall ffmpeg"
else
  bad "ffmpeg 없음" "brew install ffmpeg"
fi
command -v ffprobe >/dev/null && ok "ffprobe" || bad "ffprobe 없음 (ffmpeg와 함께 설치됨)" "brew install ffmpeg"
command -v uv >/dev/null && ok "uv" || bad "uv 없음" "brew install uv"
# stop.sh runs merge.py with python3, or with a uv-managed Python when python3 is unusable (see run_python).
if python_is_usable; then
  ok "python3 ($(command -v python3))"
elif command -v uv >/dev/null; then
  warn "쓸 수 있는 python3가 없습니다 (없거나 Xcode CLT 설치 창을 띄우는 껍데기)" \
       "병합(merge.py)은 uv가 받아 온 Python으로 돌아갑니다. 처음 한 번 네트워크가 필요하니 미리 받기: uv python install"
else
  bad "python3도 uv도 없어 종료 후 병합(merge.py)을 돌릴 수 없습니다" "brew install uv"
fi

head_ "이 플러그인의 실행 파일"
for b in $AUDIOTEE $WINREC; do
  n=${b:t}
  if [[ ! -x $b ]]; then
    bad "$n 없음: $b" "scripts/setup.sh"
    continue
  fi
  if ! codesign -v $b >/dev/null 2>&1; then
    bad "$n 서명이 올바르지 않습니다" "scripts/setup.sh (다시 받기: rm $b 후 실행)"
  elif xattr -p com.apple.quarantine $b >/dev/null 2>&1; then
    warn "$n 에 quarantine 표시가 있어 실행이 막힐 수 있습니다" "xattr -d com.apple.quarantine $b"
  elif [[ $n == audiotee ]] && ! $b --help >/dev/null 2>&1; then
    bad "$n 이 실행되지 않습니다" "scripts/setup.sh"
  else
    ok "$n"
  fi
done

head_ "전사 (Whisper)"
model_dir=${HF_HOME:-$HOME/.cache/huggingface}/hub/models--${WHISPER_MODEL//\//--}
if [[ ! -x $MLX ]]; then
  bad "mlx_whisper 없음" "scripts/setup.sh"
else
  ok "mlx_whisper"
  if [[ -d $model_dir ]]; then
    ok "모델 받아 둠: $WHISPER_MODEL"
  elif (( warm )); then
    echo "  모델을 받는 중입니다 (처음 한 번, 시간이 걸립니다)..."
  else
    warn "모델 아직 안 받음: $WHISPER_MODEL" \
         "첫 전사 때 자동으로 받아져 첫 5분 구간이 늦어집니다. 미리 받기: scripts/doctor.sh --warm"
  fi
  if (( ! quick )) && [[ -d $model_dir || $warm == 1 ]]; then
    tmp=$(mktemp -d)
    ffmpeg -hide_banner -loglevel error -f lavfi -i anullsrc=r=16000:cl=mono -t 1 $tmp/s.wav 2>/dev/null
    if whisper $tmp/s.wav $tmp --output-format txt && [[ -e $tmp/s.txt ]]; then
      ok "전사 시험 통과 (무음 1초를 받아써 봄)"
    else
      bad "전사 시험 실패: mlx_whisper가 끝까지 돌지 못했습니다" \
          "직접 실행해 오류 보기: $MLX $tmp/s.wav --model $WHISPER_MODEL --language $WHISPER_LANG"
    fi
    [[ -d $model_dir ]] || warn "모델 폴더를 찾지 못했습니다: $model_dir"
    rm -rf $tmp
  fi
fi

head_ "녹음 환경"
if [[ -n $recording ]]; then
  warn "지금 녹음 중입니다: $recording" "소리 시험은 녹음에 섞이므로 건너뜁니다"
elif (( quick )); then
  warn "소리 시험을 건너뜀 (--quick)" "권한은 이 시험으로만 확인할 수 있습니다"
elif [[ -x $AUDIOTEE ]] && command -v afplay >/dev/null && command -v ffmpeg >/dev/null; then
  echo "  5초 동안 짧은 신호음이 납니다 (시스템 소리를 잡을 수 있는지 시험)"
  tmp=$(mktemp -d)
  ffmpeg -hide_banner -loglevel error -f lavfi -i "sine=frequency=660:duration=3" -af volume=0.3 $tmp/tone.wav 2>/dev/null
  $AUDIOTEE --sample-rate 16000 > $tmp/probe.raw 2>/dev/null & tp=$!
  sleep 1
  afplay $tmp/tone.wav & ap=$!
  sleep 4
  kill $tp 2>/dev/null; wait $tp 2>/dev/null
  kill $ap 2>/dev/null; wait $ap 2>/dev/null
  db=$(mean_db $tmp/probe.raw -raw)
  if [[ ! -s $tmp/probe.raw ]]; then
    bad "audiotee가 아무 소리도 내보내지 않았습니다" "다시 시도하고, 계속되면 scripts/setup.sh"
  elif [[ -z $db || $db == -inf || ${db%.*} -lt -60 ]]; then
    bad "시스템 소리가 잡히지 않았습니다 (무음, 평균 ${db:-?} dB)" \
        "시스템 설정 → 개인정보 보호 및 보안 → 화면 및 시스템 오디오 녹음 → 지금 쓰는 터미널 앱 켜기 (켠 뒤 터미널 재시작이 필요할 수 있음). 시스템 음소거도 확인"
  else
    ok "시스템 소리가 잡힘 (평균 $db dB): 권한 정상"
  fi
  rm -rf $tmp
fi

if pgrep -x zoom.us >/dev/null; then
  found=
  if [[ -x $WINREC ]]; then
    titles_spec=${LECTURE_WINDOW_TITLE:-"Zoom 회의|Zoom Meeting"}
    for t in "${(@s:|:)titles_spec}"; do
      wh=$($WINREC --size ${LECTURE_WINDOW_OWNER:-Zoom} $t 1280 2>/dev/null) && { found=$wh; break }
    done
  fi
  if [[ -n $found ]]; then
    ok "Zoom 회의 창을 찾음 (영상 ${found// /x})"
  else
    warn "Zoom은 켜져 있지만 회의 창을 찾지 못했습니다" \
         "회의에 들어간 뒤 다시 실행하세요. 계속 안 보이면 화면 녹화 권한도 확인 (녹음 시작 후에도 영상만 빠질 수 있음)"
  fi
else
  warn "Zoom이 실행 중이 아닙니다" "강의에 들어간 뒤 시작해도 됩니다. 영상은 회의 창이 보일 때부터 녹화됩니다"
fi

head_ "저장 공간"
mkdir -p $OUT_ROOT 2>/dev/null
if [[ -w $OUT_ROOT ]]; then
  free_gb=$(df -k $OUT_ROOT | awk 'NR==2 { print int($4 / 1024 / 1024) }')
  if (( free_gb < 2 )); then
    warn "$OUT_ROOT 여유 공간이 ${free_gb} GB 뿐입니다" "LECTURE_ROOT=<다른 폴더> 로 저장 위치를 바꿀 수 있습니다"
  else
    ok "$OUT_ROOT 에 쓸 수 있음 (여유 ${free_gb} GB)"
  fi
else
  bad "$OUT_ROOT 에 쓸 수 없습니다" "LECTURE_ROOT=<쓸 수 있는 폴더> 로 저장 위치를 바꾸세요"
fi

print -r -- ""
if (( fails )); then
  print -r -- "${R}문제 ${fails}개${N}, 경고 ${warns}개: 위의 ✗ 부터 해결하세요."
  exit 1
fi
print -r -- "${G}준비 완료${N} (경고 ${warns}개)"
exit 0
