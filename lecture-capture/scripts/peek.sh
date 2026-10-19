#!/bin/zsh
# peek.sh [dir] — transcribe the segment that is still being recorded and print it.
setopt nullglob
source ${0:A:h}/_common.sh
D=$(existing_dir $1) || exit 1
MID=$D/$MIDDIR
parts=($MID/audio/part_*.wav); f=${parts[-1]}
[[ -n $f ]] || { echo "녹음 파일 없음"; exit 1; }
tmp=$(mktemp -d)
ffmpeg -hide_banner -loglevel error -y -f s16le -ar 16000 -ac 1 -i =(tail -c +45 $f) $tmp/${f:t}
whisper $tmp/${f:t} $tmp --output-format txt
echo "== ${f:t} (진행 중 구간) =="; cat $tmp/${f:t:r}.txt
rm -rf $tmp
