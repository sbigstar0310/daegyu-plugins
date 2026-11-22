#!/bin/zsh
# auto_lecture.sh <zoom link | meeting ID> [passcode] [--at HH:MM] [--until HH:MM] [--end HH:MM] [--dir D]
# Unattended lecture: wait for --at (default now) → zoom_join.sh → start.sh → when the meeting window has
# been gone 3 min, or at --end, leave the meeting (zoom_leave.sh) and run stop.sh. A notification reports it.
# Not in the meeting by --until (default --at + 45 min) → leaves the waiting room and gives up without recording.
#   --end defaults to --at + 3 h. --dir defaults to lecture_dir. LECTURE_MUTE=1 mutes the speakers (the tap still records).
# Waits on the wall clock in 20 s steps (one long sleep stalls while the Mac sleeps) and keeps the Mac awake
# from then on; a closed lid still sleeps it. Run detached, on the day:
#   nohup $S/auto_lecture.sh "<link>" --at 15:55 --end 18:00 --dir D > D.log 2>&1 &!
HERE=${0:A:h}; source $HERE/_common.sh
zmodload zsh/zutil; zparseopts -D -E -- -at:=A -until:=U -end:=E -dir:=DIR
(( $# )) || { sed -n '2,9p' ${0:A}; exit 2 }
t_at=$(date +%s); [[ -n ${A[2]} ]] && t_at=$(epoch_at ${A[2]})
t_until=$(( t_at + 2700 )); [[ -n ${U[2]} ]] && t_until=$(epoch_at ${U[2]})
t_end=$(( t_at + 10800 )); [[ -n ${E[2]} ]] && t_end=$(epoch_at ${E[2]})
D=$(lecture_dir ${DIR[2]:-})
note() { osascript -e "display notification \"$1\" with title \"lecture-capture\"" 2>/dev/null }
hm() { date -r $1 +%H:%M }

caffeinate -i -w $$ &
log "입장 대기 → $(hm $t_at) (입장 마감 $(hm $t_until), 종료 $(hm $t_end)) · $D"
while (( $(date +%s) < t_at )); do sleep 20; done
(( $(date +%s) >= t_until )) && { log "깨어나 보니 입장 마감이 지남"; note "자동 입장 실패: 맥이 잠들어 있었음"; exit 4 }
caffeinate -dimsu -w $$ &
[[ ${LECTURE_MUTE:-0} == 1 ]] && osascript -e 'set volume with output muted'
$HERE/zoom_join.sh "$@" --until $(hm $t_until) || {
  $HERE/zoom_leave.sh   # don't sit in the waiting room and join later with nothing recording
  note "자동 입장 실패: 회의 창이 안 뜸"; exit 4 }
log "녹음 시작"; $HERE/start.sh $D; log "start.sh exit=$?"

gone=0
while (( $(date +%s) < t_end )); do
  sleep 30
  if meeting_window; then gone=0; else gone=$((gone + 30)); fi
  (( gone >= 180 )) && { log "회의 창이 3분간 없음 → 종료"; break }
done
meeting_window && { log "종료 시각 → 회의 나가기"; $HERE/zoom_leave.sh }
log "정지·병합"; $HERE/stop.sh $D; log "완료: $D"
note "강의 녹화·전사 완료"
