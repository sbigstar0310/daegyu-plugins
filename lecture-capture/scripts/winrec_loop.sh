#!/bin/zsh
# Records the Zoom meeting window while the audio tap is alive; restarts if capture exits.
# winrec2 emits raw BGRA at a constant fps (latest frame repeated) and ffmpeg encodes it into
# 5-minute mkv segments named by wall-clock start time (merge.py aligns them to audio by name).
# A capture that stays alive but delivers no frames (it attached to a window that then closed, e.g.
# after a rejoin) is restarted once ffmpeg's frame count stops moving for LECTURE_STALL_SEC (issue #42).
source ${0:A:h}/_common.sh
D=$1; AT=$(pid_of $D audiotee)
MID=$D/$MIDDIR
OWNER=${LECTURE_WINDOW_OWNER:-Zoom}
titles_spec=${LECTURE_WINDOW_TITLE:-"Zoom 회의|Zoom Meeting"}
TITLES=("${(@s:|:)titles_spec}")
FPS=${LECTURE_FPS:-10}
WIDTH=${LECTURE_VIDEO_WIDTH:-1280}
FIFO=$D/.video.fifo
PROG=$MID/logs/ffmpeg_video.progress
STALL=${LECTURE_STALL_SEC:-60} STEP=${LECTURE_STALL_CHECK_SEC:-5} KILLWAIT=${LECTURE_STALL_KILL_SEC:-5}
# Exactly one SIGINT to winrec2; ffmpeg then finalizes on EOF.
trap 'p=$(cat $D/.winrec.pid 2>/dev/null); alive "$p" && kill -INT $p; wait; exit 0' INT TERM
W= H=
while alive $AT; do
  for t in "${TITLES[@]}"; do
    if [[ -z $W ]]; then                       # size fixed once so all segments concat cleanly
      wh=($($WINREC --size $OWNER $t $WIDTH 2>/dev/null)) || continue
      (( $#wh == 2 )) || continue
      W=$wh[1] H=$wh[2]
    fi
    rm -f $FIFO; mkfifo $FIFO
    rm -f $PROG
    ffmpeg -hide_banner -loglevel error -progress $PROG -stats_period $STEP -f rawvideo -pix_fmt bgra -s ${W}x${H} -r $FPS -i $FIFO \
      -c:v libx264 -preset veryfast -crf 26 -g $(( FPS * 5 )) -pix_fmt yuv420p \
      -f segment -segment_time $SEGMENT_SEC -reset_timestamps 1 -strftime 1 $MID/video/v_%H%M%S.mkv 2>>$MID/logs/ffmpeg_video.log &
    echo $! > $D/.vffmpeg.pid
    $WINREC $OWNER $t $W $H $FPS > $FIFO 2>>$MID/logs/winrec.log &
    echo $! > $D/.winrec.pid
    wp=$(cat $D/.winrec.pid) prev=-1 still=0
    while alive $wp; do
      sleep $STEP
      cur=$(progress_frame $PROG)
      still=$(stall_secs $prev $cur $still $STEP); prev=$cur
      if (( still >= STALL )); then
        log "멈춤: ${STALL}초 동안 새 프레임 없음 → 캡처 다시 시작"
        kill -INT $wp 2>/dev/null           # one SIGINT, as the trap does; TERM only if it ignores it
        for i in {1..$KILLWAIT}; do alive $wp || break; sleep 1; done
        alive $wp && kill -TERM $wp 2>/dev/null
        break
      fi
    done
    wait $wp
    wait $(cat $D/.vffmpeg.pid)               # EOF on the fifo → ffmpeg closes the segment
    alive $AT || break
  done
  sleep 2
done
rm -f $FIFO
