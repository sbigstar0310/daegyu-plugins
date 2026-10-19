#!/bin/zsh
# stop.sh [dir] [--no-merge] — stop everything, finish transcription, then merge outputs:
#   lecture_audio.m4a, transcript_full.txt (+ .srt), lecture.mp4 (mkv segments + aligned audio).
setopt nullglob
source ${0:A:h}/_common.sh
D=$(existing_dir ${1:#--*}) || exit 1
MID=$D/$MIDDIR
[[ -f $D/.pids ]] || { echo ".pids 없음: $D"; exit 1; }

# Video first: the loop's trap sends winrec2 exactly one SIGINT; ffmpeg finalizes the mkv on EOF.
if alive "$(pid_of $D winrec_loop)"; then
  kill -TERM $(pid_of $D winrec_loop)
elif alive "$(cat $D/.winrec.pid 2>/dev/null)"; then
  kill -INT $(cat $D/.winrec.pid)
fi
for i in {1..30}; do alive "$(cat $D/.vffmpeg.pid 2>/dev/null)" || break; sleep 1; done
# Audio: killing the tap closes the fifo, so ffmpeg finalizes the last segment's header.
alive "$(pid_of $D audiotee)" && kill -TERM $(pid_of $D audiotee)
for i in {1..30}; do alive "$(pid_of $D ffmpeg)" || break; sleep 1; done
touch $D/.stopped
echo "녹음 종료. 남은 구간 받아쓰는 중..."
for i in {1..600}; do alive "$(pid_of $D live_tx)" || break; sleep 2; done
rm -f $D/.audio.fifo $D/.video.fifo
[[ $* == *--no-merge* ]] && exit 0

parts=($MID/audio/part_*.wav)
if (( $#parts )); then
  printf "file '%s'\n" $parts > $D/.audio_list.txt
  ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $D/.audio_list.txt -c:a aac -b:a 64k $D/lecture_audio.m4a
  echo "오디오: $D/lecture_audio.m4a"
fi

run_python ${0:A:h}/merge.py $D $SEGMENT_SEC
