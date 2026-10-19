#!/bin/zsh
# start.sh [dir] — start audio tap, Zoom-window video and live transcription in the background.
# Exit 3 = started but the self-test heard silence (permission missing or lecture not playing).
source ${0:A:h}/_common.sh
D=$(lecture_dir $1)
MID=$D/$MIDDIR
[[ -x $AUDIOTEE && -x $WINREC ]] || { echo "먼저 setup.sh 실행"; exit 1; }
if alive "$(pid_of $D audiotee)"; then echo "이미 녹음 중: $D"; exit 1; fi
mkdir -p $MID/audio $MID/video $MID/transcript $MID/logs
rm -f $D/.pids $D/.audio.fifo; mkfifo $D/.audio.fifo

nohup $AUDIOTEE --sample-rate 16000 > $D/.audio.fifo 2>$MID/logs/audiotee.log &
print "audiotee=$!\nstarted=$(date +%s)" >> $D/.pids
nohup ffmpeg -hide_banner -loglevel error -f s16le -ar 16000 -ac 1 -i $D/.audio.fifo \
  -f segment -segment_time $SEGMENT_SEC -c:a pcm_s16le $MID/audio/part_%03d.wav \
  > $MID/logs/ffmpeg_audio.log 2>&1 &
print "ffmpeg=$!" >> $D/.pids
nohup ${0:A:h}/winrec_loop.sh $D > $MID/logs/winrec_loop.log 2>&1 &
print "winrec_loop=$!" >> $D/.pids
nohup ${0:A:h}/live_tx.sh $D > $MID/logs/live_tx.log 2>&1 &
print "live_tx=$!" >> $D/.pids
echo "녹음 시작: $D"

# Self-test: a separate 5 s tap (ffmpeg buffers the live segment, so reading it this early sees nothing).
probe=$(mktemp); $AUDIOTEE --sample-rate 16000 > $probe 2>/dev/null & tp=$!
sleep 5; kill $tp 2>/dev/null; wait $tp 2>/dev/null
db=$(mean_db $probe -raw); rm -f $probe
sleep 2
echo "자체 점검: 평균 ${db:-?} dB, 영상 $(ls $MID/video 2>/dev/null | wc -l | tr -d ' ')개"
if [[ -z $db || $db == -inf || ${db%.*} -lt -60 ]]; then
  cat <<'MSG'
!!!!!!!! 무음입니다 !!!!!!!!
- 강연 소리가 지금 나오고 있는지 확인
- 시스템 설정 → 화면 및 시스템 오디오 녹음 → 터미널 앱 권한 (켠 뒤 터미널 재시작 필요할 수 있음)
녹음은 계속 돌고 있습니다. 고친 뒤 stop.sh → start.sh 로 다시 시작하세요.
MSG
  exit 3
fi
