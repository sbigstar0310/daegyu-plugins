#!/bin/zsh
# Transcribes each finished 5-minute segment; after the tap stops, finishes the rest and exits.
setopt nullglob
source ${0:A:h}/_common.sh
D=$1; AT=$(pid_of $D audiotee)
while true; do
  running=0; alive $AT && running=1
  ff_done=1; alive "$(pid_of $D ffmpeg)" && ff_done=0
  for f in $D/audio/part_*.wav; do
    n=${f:t:r}; next=$D/audio/part_$(printf %03d $(( 10#${n#part_} + 1 ))).wav
    [[ -e $D/transcript/$n.txt ]] && continue
    [[ -e $next ]] || (( ff_done )) || continue   # segment still being written
    whisper $f $D/transcript --output-format all
  done
  (( running || ! ff_done )) || break
  sleep 30
done
