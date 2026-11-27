#!/bin/zsh
# auto_lecture.sh <zoom link | meeting ID> [passcode] [--at HH:MM] [--until HH:MM] [--end HH:MM] [--dir D]
#                 [--warn HH:MM] [--no-record]
# Unattended lecture: wait for --at (default now) → zoom_join.sh (camera and mic forced off) → start.sh → when
# the meeting window has been gone 3 min, or at --end, leave the meeting (zoom_leave.sh) and run stop.sh.
# Not in the meeting by --until (default --at + 45 min) → leaves the waiting room and gives up without recording.
# A meeting already open at --at is someone else's (another class): wait for it to close, never record or leave it.
#   --warn HH:MM   alert (with a sound) if not in by then, but keep trying until --until
#   --no-record    join only: no start.sh/stop.sh, never leaves; keeps the Mac awake until the meeting ends or --end
#   --end defaults to --at + 3 h. --dir defaults to lecture_dir. LECTURE_MUTE=1 mutes the speakers (the tap still records).
# Waits on the wall clock in 20 s steps (one long sleep stalls while the Mac sleeps) and keeps the Mac awake
# from then on; a closed lid still sleeps it. Run detached, on the day:
#   nohup $S/auto_lecture.sh "<link>" --at 15:55 --end 18:00 --dir D > D.log 2>&1 &!
HERE=${0:A:h}; source $HERE/_common.sh
zmodload zsh/zutil; zparseopts -D -E -- -at:=A -until:=U -end:=E -dir:=DIR -warn:=W -no-record=NR
(( $# )) || { sed -n '2,13p' ${0:A}; exit 2 }
t_at=$(date +%s); [[ -n ${A[2]} ]] && t_at=$(epoch_at ${A[2]})
t_until=$(( t_at + 2700 )); [[ -n ${U[2]} ]] && t_until=$(epoch_at ${U[2]})
t_end=$(( t_at + 10800 )); [[ -n ${E[2]} ]] && t_end=$(epoch_at ${E[2]})
t_warn=; [[ -n ${W[2]} ]] && t_warn=$(epoch_at ${W[2]})
record=1; [[ -n $NR ]] && record=0
POLL=${LECTURE_POLL_SEC:-20} GONE=${LECTURE_GONE_SEC:-180}   # overridable for tests
D=; (( record )) && D=$(lecture_dir ${DIR[2]:-})
note() { osascript -e "display notification \"$1\" with title \"lecture-capture\" sound name \"Glass\"" 2>/dev/null }
hm() { date -r $1 +%H:%M }

caffeinate -i -w $$ &
log "입장 대기 → $(hm $t_at) (입장 마감 $(hm $t_until), 종료 $(hm $t_end)${t_warn:+, 미입장 알림 $(hm $t_warn)}) · ${D:-녹화 안 함}"
while (( $(date +%s) < t_at )); do sleep $POLL; done
(( $(date +%s) >= t_until )) && { log "깨어나 보니 입장 마감이 지남"; note "자동 입장 실패: 맥이 잠들어 있었음"; exit 4 }
caffeinate -dimsu -w $$ &
[[ ${LECTURE_MUTE:-0} == 1 ]] && osascript -e 'set volume with output muted'

# "Not in yet" alert: a watcher that fires once at --warn unless the join has finished by then.
joined=$(mktemp -u)
if [[ -n $t_warn ]]; then
  { until warn_due $(date +%s) $t_warn $([[ -e $joined ]] && print 1 || print 0); do
      [[ -e $joined ]] && exit 0
      sleep 1
    done
    log "$(hm $t_warn)까지 아직 입장 못 함 → 알림"
    note "$(hm $t_warn)인데 아직 수업에 못 들어갔어요: 계속 시도 중 (마감 $(hm $t_until))" } &!
fi

# Another meeting already open is not the lecture: wait it out, never join over it, record it or close it.
told=0
while :; do
  case $(join_gate $(date +%s) $t_until $(meeting_window && print 1 || print 0)) in
    join) break ;;
    wait) (( told++ )) || { log "다른 회의가 열려 있음 → 닫힐 때까지 기다림"; note "다른 회의가 열려 있어 끝날 때까지 기다려요 (마감 $(hm $t_until))" }
          sleep $POLL ;;
    giveup) log "입장 마감까지 다른 회의가 열려 있음 → 포기"; note "자동 입장 포기: 다른 회의가 계속 열려 있음"; exit 4 ;;
  esac
done

$HERE/zoom_join.sh "$@" --until $(date -r $t_until +%H:%M:%S); rc=$?
if (( rc == 4 || rc == 2 )); then
  $HERE/zoom_leave.sh   # don't sit in the waiting room and join later with nothing recording
  note "자동 입장 실패: 회의 창이 안 뜸"; exit 4
fi
touch $joined
if (( rc == 5 )); then note "입장했지만 카메라·마이크가 꺼졌는지 확인하지 못함: 직접 확인해 주세요"
else note "회의 입장 완료 (카메라·마이크 꺼짐)"; fi

if (( record )); then log "녹음 시작"; $HERE/start.sh $D; log "start.sh exit=$?"; fi

gone=0
while (( $(date +%s) < t_end )); do
  sleep $POLL
  if meeting_window; then gone=0; else gone=$((gone + POLL)); fi
  (( gone >= GONE )) && { log "회의 창이 ${GONE}초간 없음 → 종료"; break }
done
rm -f $joined
(( record )) || { log "입장만 하는 모드: 끝 (회의에서 나가지 않음)"; exit 0 }
meeting_window && { log "종료 시각 → 회의 나가기"; $HERE/zoom_leave.sh }
log "정지·병합"; $HERE/stop.sh $D; log "완료: $D"
note "강의 녹화·전사 완료"
