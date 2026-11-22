#!/bin/zsh
# zoom_leave.sh — leave the Zoom meeting or waiting room: close its window and confirm "회의 나가기".
# Never quits Zoom itself. Exit 0 = nothing left to leave, 1 = still in.
HERE=${0:A:h}; source $HERE/_common.sh
for i in {1..6}; do
  r=$(osascript $HERE/zoom_ui.applescript leave 2>&1)
  [[ $r == (nothing|no-zoom) ]] && break
  log "Zoom 나가기: $r"; sleep 1
done
sleep 1
meeting_window && { log "회의 창이 아직 있음"; exit 1 }
exit 0
