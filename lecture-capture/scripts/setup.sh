#!/bin/zsh
# Idempotent: puts AudioTee + winrec2 into the plugin's bin/, installs mlx-whisper, checks ffmpeg.
# The two helpers are downloaded prebuilt from this plugin version's GitHub release (no Xcode CLT
# needed); if that fails, or LECTURE_BUILD_FROM_SOURCE=1, they are compiled with swift instead.
set -e
source ${0:A:h}/_common.sh
mkdir -p $BIN $ROOT/vendor

REPO=sbigstar0310/daegyu-plugins
VERSION=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' $ROOT/.claude-plugin/plugin.json)
TAG=lecture-capture-v$VERSION

command -v ffmpeg >/dev/null || { echo "ffmpeg 없음: brew install ffmpeg"; exit 1; }

fetch_prebuilt() {  # downloads both helpers, verifies SHA256SUMS, installs into $BIN
  [[ $(uname -m) == arm64 ]] || return 1
  local base=${LECTURE_RELEASE_BASE:-https://github.com/$REPO/releases/download/$TAG} tmp=$(mktemp -d) n
  curl -fsSL $base/SHA256SUMS -o $tmp/SHA256SUMS || { rm -rf $tmp; return 1; }
  for n in audiotee winrec2; do
    curl -fsSL $base/$n-arm64 -o $tmp/$n-arm64 || { rm -rf $tmp; return 1; }
  done
  (cd $tmp && shasum -a 256 -c SHA256SUMS >/dev/null 2>&1) || { echo "체크섬 불일치: 다운로드 폐기"; rm -rf $tmp; return 1; }
  for n in audiotee winrec2; do
    install -m 755 $tmp/$n-arm64 $BIN/$n
    xattr -d com.apple.quarantine $BIN/$n 2>/dev/null || true
  done
  rm -rf $tmp
}

build_from_source() {
  command -v swift >/dev/null || { echo "swift 없음: xcode-select --install"; return 1; }
  if [[ ! -x $AUDIOTEE ]]; then
    local ref=$(<$ROOT/scripts/AUDIOTEE_REF) src=$ROOT/vendor/audiotee
    if [[ ! -d $src ]]; then
      mkdir -p $src && git -C $src init -q
      git -C $src fetch -q --depth 1 https://github.com/makeusabrew/audiotee $ref
      git -C $src checkout -q FETCH_HEAD
    fi
    (cd $src && swift build -c release 2>&1 | tail -1)
    cp $src/.build/release/audiotee $AUDIOTEE
  fi
  if [[ ! -x $WINREC || $ROOT/scripts/winrec2/main.swift -nt $WINREC ]]; then
    swiftc -O $ROOT/scripts/winrec2/main.swift -o $WINREC
  fi
}

if [[ -n $LECTURE_BUILD_FROM_SOURCE ]]; then
  build_from_source
elif [[ ! -x $AUDIOTEE || ! -x $WINREC ]]; then
  if fetch_prebuilt; then
    echo "받은 파일: $TAG"
  else
    echo "미리 빌드된 파일을 받지 못해 소스에서 빌드합니다 (Xcode CLT 필요)"
    build_from_source
  fi
fi
echo "audiotee: $AUDIOTEE"
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
