#!/bin/zsh
# Records the Zoom meeting window while the audio tap is alive; restarts if capture exits.
# winrec2 emits raw BGRA at a constant fps (latest frame repeated) and ffmpeg encodes it into
# 5-minute mkv segments named by wall-clock start time (merge.py aligns them to audio by name).
source ${0:A:h}/_common.sh
D=$1; AT=$(pid_of $D audiotee)
MID=$D/$MIDDIR
OWNER=${LECTURE_WINDOW_OWNER:-Zoom}
titles_spec=${LECTURE_WINDOW_TITLE:-"Zoom 회의|Zoom Meeting"}
TITLES=("${(@s:|:)titles_spec}")
FPS=${LECTURE_FPS:-10}
WIDTH=${LECTURE_VIDEO_WIDTH:-1280}
FIFO=$D/.video.fifo
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
    ffmpeg -hide_banner -loglevel error -f rawvideo -pix_fmt bgra -s ${W}x${H} -r $FPS -i $FIFO \
      -c:v libx264 -preset veryfast -crf 26 -g $(( FPS * 5 )) -pix_fmt yuv420p \
      -f segment -segment_time $SEGMENT_SEC -strftime 1 $MID/video/v_%H%M%S.mkv 2>>$MID/logs/ffmpeg_video.log &
    echo $! > $D/.vffmpeg.pid
    $WINREC $OWNER $t $W $H $FPS > $FIFO 2>>$MID/logs/winrec.log &
    echo $! > $D/.winrec.pid
    wait $(cat $D/.winrec.pid)
    wait $(cat $D/.vffmpeg.pid)               # EOF on the fifo → ffmpeg closes the segment
    alive $AT || break
  done
  sleep 2
done
rm -f $FIFO
