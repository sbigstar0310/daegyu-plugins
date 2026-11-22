-- zoom_ui.applescript join|leave — does one step of Zoom's join or leave UI per call and prints what it did.
-- Needs Accessibility (손쉬운 사용) for the terminal app. Called in a loop by zoom_join.sh / zoom_leave.sh.
--   join:  video preview → turn the camera off, press 참가/Join only once it reads "currently off"
--          ("preview-joined", or "preview-video-on" if it would not turn off); "join with computer audio"
--          dialog → press it ("audio-joined"); else "none".
--   leave: "회의 나가기"/"Leave Meeting" confirmation → press it ("left"); meeting or waiting-room window →
--          press its close button, which brings up that confirmation ("closing"); else "nothing".
on run argv
	set mode to item 1 of argv
	tell application "System Events"
		if not (exists process "zoom.us") then return "no-zoom"
		tell process "zoom.us"
			if mode is "join" then
				repeat with w in windows
					try
						set jb to (first button of w whose description is "참가" or description is "Join")
						set tg to tab group 1 of w
						set vb to (first button of tg whose description starts with "Video")
						if description of vb contains "currently on" then click vb
						delay 1
						if description of (first button of tg whose description starts with "Video") contains "currently off" then
							click jb
							return "preview-joined"
						end if
						return "preview-video-on"
					end try
					try
						click (first button of w whose description contains "컴퓨터 오디오" or name contains "컴퓨터 오디오" or description contains "Computer Audio" or name contains "Computer Audio")
						return "audio-joined"
					end try
				end repeat
				return "none"
			else if mode is "leave" then
				repeat with w in windows
					try
						click (first button of w whose description is "회의 나가기" or description is "Leave Meeting" or description is "Leave meeting")
						return "left"
					end try
				end repeat
				repeat with w in windows
					set n to ""
					try
						set n to name of w as text
					end try
					set isWaiting to false
					try
						set isWaiting to exists (first button of w whose description is "스피커 및 마이크 테스트" or description is "Test Speaker and Microphone")
					end try
					if n is "Zoom 회의" or n is "Zoom Meeting" or isWaiting then
						click (first button of w whose description is "닫기 버튼" or subrole is "AXCloseButton")
						return "closing"
					end if
				end repeat
				return "nothing"
			end if
		end tell
	end tell
	return "bad-mode"
end run
