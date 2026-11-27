#!/bin/zsh
# zoom_join.sh <zoom link | meeting ID> [passcode] [--until HH:MM]
# Opens the meeting straight in the Zoom app (zoommtg://, no browser prompt) and clicks through the
# video preview — 참가 only after the camera reads off — and the "join with computer audio" dialog.
# If the host has not started yet, Zoom shows a waiting screen and joins by itself when it starts.
# Then it reads the 회의 menu and switches the mic and camera off if they are on: the preview can be skipped.
# Exit 0 = in the meeting with mic and camera confirmed off (or a meeting was already open: left untouched),
#      5 = in the meeting but mic/camera could not be confirmed off, 4 = not in by --until (default: 10 min), 2 = bad link.
HERE=${0:A:h}; source $HERE/_common.sh
zmodload zsh/zutil; zparseopts -D -E -- -until:=U
deadline=$(( $(date +%s) + 600 )); [[ -n ${U[2]} ]] && deadline=$(epoch_at ${U[2]})
link=${1:-}; id= pwd=
if [[ $link =~ '^[0-9 -]{9,}$' ]]; then id=${link//[ -]/}; pwd=${2:-}
elif [[ $link =~ '(/j/|confno=)([0-9]+)' ]]; then id=$match[2]; [[ $link =~ '[?&]pwd=([^&#]+)' ]] && pwd=$match[1]
else echo "usage: zoom_join.sh <https://…zoom.us/j/ID?pwd=… | zoommtg://… | meeting ID [passcode]> [--until HH:MM]" >&2; exit 2
fi

ui() {  # one step of the join UI; warns once if Accessibility is missing
  local r=$(osascript $HERE/zoom_ui.applescript join 2>&1)
  if [[ $r == *(-25211|-1719|-1743|assistive|보조)* ]]; then
    (( warned++ )) || log "손쉬운 사용 권한이 없어 Zoom 버튼을 누를 수 없음: 시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용 → 터미널 앱 켜기"
  elif [[ $r != (none|no-zoom|) ]]; then log "Zoom 클릭: $r"; fi
  REPLY=$r
}
warned=0
meeting_window && { log "이미 회의 창이 있음"; exit 0 }
defaults write us.zoom.xos kZMUserDefaultMeetingStartWithVideo -bool false 2>/dev/null  # best effort; the preview step is what guarantees it
log "Zoom 입장: $id"
open "zoommtg://zoom.us/join?action=join&confno=$id${pwd:+&pwd=$pwd}"
until meeting_window; do
  (( $(date +%s) >= deadline )) && { log "마감까지 회의 창이 안 뜸 (호스트 미시작·수업 없음·입장 실패)"; exit 4 }
  ui; sleep 3
done
log "회의 입장 확인"
for i in {1..10}; do ui; [[ $REPLY == audio-joined ]] && break; sleep 2; done   # audio dialog can come a few seconds late
# The preview (where the camera is turned off) is sometimes skipped, and nothing above mutes the mic:
# read the 회의 menu, switch off whatever is on, and read it again.
st=
for i in {1..5}; do
  items=$(osascript $HERE/zoom_ui.applescript av-off 2>&1)
  st=$(zoom_av_state "${(@s:|:)items}")
  av_is_off "$st" && break
  sleep 2
done
log "상태: $st"
av_is_off "$st" || { log "마이크·카메라가 꺼졌는지 확인하지 못함 (회의 메뉴: $items)"; exit 5 }
exit 0
