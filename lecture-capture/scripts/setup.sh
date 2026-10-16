#!/bin/zsh
# Idempotent: builds AudioTee + winrec2 into the plugin's bin/, installs mlx-whisper, checks ffmpeg.
set -e
source ${0:A:h}/_common.sh
mkdir -p $BIN $ROOT/vendor

command -v ffmpeg >/dev/null || { echo "ffmpeg 없음: brew install ffmpeg"; exit 1; }
command -v swift >/dev/null || { echo "swift 없음: xcode-select --install"; exit 1; }

if [[ ! -x $AUDIOTEE ]]; then
  [[ -d $ROOT/vendor/audiotee ]] || git clone -q --depth 1 https://github.com/makeusabrew/audiotee $ROOT/vendor/audiotee
  (cd $ROOT/vendor/audiotee && swift build -c release 2>&1 | tail -1)
  cp $ROOT/vendor/audiotee/.build/release/audiotee $AUDIOTEE
fi
echo "audiotee: $AUDIOTEE"

if [[ ! -x $WINREC || $ROOT/scripts/winrec2/main.swift -nt $WINREC ]]; then
  swiftc -O $ROOT/scripts/winrec2/main.swift -o $WINREC
fi
echo "winrec2:  $WINREC"

if [[ ! -x $MLX ]]; then
  command -v uv >/dev/null || { echo "uv 없음: brew install uv"; exit 1; }
  uv tool install mlx-whisper >/dev/null
  MLX=$HOME/.local/bin/mlx_whisper
fi
echo "whisper:  $MLX"

cat <<'MSG'

권한 확인 (처음 한 번):
  시스템 설정 → 개인정보 보호 및 보안 → 화면 및 시스템 오디오 녹음
  → 지금 쓰는 터미널 앱(Ghostty/Terminal/iTerm)을 켜기.
  권한이 없으면 오류 없이 무음(-91 dB / -inf)만 녹음됩니다.
MSG
