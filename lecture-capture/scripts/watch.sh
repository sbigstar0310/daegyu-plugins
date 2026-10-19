#!/bin/zsh
# Health check for the Monitor tool: one line per finished segment, ALERT lines on failure.
# Keep this a script file: zsh glob qualifiers fail inside Monitor's eval.
setopt nullglob
source ${0:A:h}/_common.sh
D=$(existing_dir $1) || exit 1
MID=$D/$MIDDIR
seen=" ${(j: :)${(@f)$(ls $MID/transcript 2>/dev/null | grep '^part_.*txt$')}} "
alerted=""
while true; do
  for t in $MID/transcript/part_*.txt; do
    [[ $seen == *" ${t:t} "* ]] && continue
    seen="$seen${t:t} "; n=${t:t:r}
    echo "$(date +%H:%M) $n 완료 | 글자수 $(wc -m < $t | tr -d ' ') | 평균 $(mean_db $MID/audio/$n.wav) dB | 영상 $(du -sh $MID/video | cut -f1)"
  done
  for p in audiotee winrec_loop live_tx; do
    if ! alive "$(pid_of $D $p)" && [[ $alerted != *" $p "* ]]; then
      echo "$(date +%H:%M) ALERT $p 종료됨"; alerted="$alerted $p "
    fi
  done
  [[ -f $D/.stopped ]] && { echo "$(date +%H:%M) 녹음 종료됨 (stop.sh)"; exit 0; }
  sleep 20
done
