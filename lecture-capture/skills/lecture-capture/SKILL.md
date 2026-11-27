---
name: lecture-capture
description: Record, transcribe and summarize a live Zoom lecture on macOS — system audio via a Core Audio tap (the user keeps listening on AirPods/headphones), Zoom-window-only video, live Korean Whisper transcription in 5-minute segments, periodic health checks, and structured lecture notes at the end. Use when the user says "강의 녹음", "줌 강연 녹화", "강의 정리해줘", "강연 같이 녹음해서 정리", "record this Zoom lecture", or wants a lecture/webinar/meeting they are attending captured and summarized.
---

# lecture-capture — 줌 강의 녹음·녹화·전사·정리

Scripts live in `${CLAUDE_PLUGIN_ROOT}/scripts/` (below: `$S`). Everything for one
lecture goes into one folder (`$D`, default `~/Desktop/lecture_YYYYMMDD_HHMM`):

```
$D/lecture_audio.m4a, transcript_full.txt/.srt, lecture.mp4     the finals (written by stop.sh)
$D/intermediate/audio/part_NNN.wav      16 kHz mono, 5-minute segments (system audio tap)
$D/intermediate/video/v_HHMMSS.mkv      Zoom meeting window only, 10 fps H.264, 5-minute segments
$D/intermediate/transcript/part_NNN.*   Whisper output per segment (txt/srt/vtt/json/tsv)
$D/intermediate/logs/                   process logs
$D/.pids                                process ids + audio start epoch (hidden state files stay in $D)
```

The lecture is live and the user is listening. Keep every step in the background,
report briefly in Korean, and never block the turn.

## 1. Setup (idempotent, ~10 s first time)

Run `$S/doctor.sh` first when unsure the machine is ready: it checks the install, the tap permission
(it plays a short tone for 5 s), Whisper, the Zoom window and disk space, and prints the fix for every ✗.
Use `--quick` for static checks only. It is safe while a lecture is recording.

`$S/setup.sh` downloads the prebuilt AudioTee + `winrec2` for this plugin version into the
plugin's `bin/` (checksum-verified),
installs `mlx-whisper` with uv, and checks ffmpeg. Then confirm permission:
시스템 설정 → 개인정보 보호 및 보안 → **화면 및 시스템 오디오 녹음** → enable the
terminal app (Ghostty/Terminal/iTerm). Open the pane for the user with
`open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"`.
Tell them to answer "나중에" if asked to restart the terminal, because a restart kills this session.

## 2. Start

`$S/start.sh [$D]` starts the tap, the window recorder and the live transcriber with
nohup, then runs a 5 s self-test on a separate tap. **Exit 3 = silence**: either
the permission is missing or nothing is playing. Never report "녹음 중" on exit 3.

The window is matched by owner `Zoom` and title `Zoom 회의` or `Zoom Meeting`.
`winrec2` pipes raw BGRA frames into ffmpeg. The frame size is fixed once from the window's
aspect ratio at 1280 px wide.
Override with `LECTURE_WINDOW_OWNER` / `LECTURE_WINDOW_TITLE="A|B"` for another app,
and `LECTURE_FPS` / `LECTURE_VIDEO_WIDTH` / `LECTURE_ROOT` (output parent dir)
(list the titles with `CGWindowListCopyWindowInfo`).

## 3. Verify with evidence, not file sizes

- **Audio:** `$S/peek.sh $D` transcribes the in-progress segment. Real sentences mean it works.
- **Video:** extract a frame and look at it:
  `ffmpeg -sseof -1 -i <newest video> -frames:v 1 /tmp/f.jpg`. Read it and check that it shows the Zoom content.
  A fresh mkv segment can read as 0 bytes for about the first minute (see Gotchas). Check the
  write offset with `lsof -o -p $(cat $D/.vffmpeg.pid)` or wait, then look at the frame.
- Show the user a 1–2 line excerpt of what was heard.

## 4. Watch every 5 minutes

Arm `Monitor` with `command: "$S/watch.sh $D"` and `timeout_ms: 1800000`. Re-arm it when it
expires. Each finished segment emits one line with character count, mean dB and video size.
`ALERT <proc> 종료됨` means a process died: tell the user and restart it.
Report each line briefly. Mean dB below -50 or a near-empty transcript is a problem, not a pass.

## 5. Stop and merge

When the user says "끝났어", run `$S/stop.sh $D` in the background. It stops the video,
then the tap, waits for the last segment's transcription, then writes:
- `lecture_audio.m4a`
- `transcript_full.txt` (with `## [mm:ss]` headers per segment) and `transcript_full.srt`
- `lecture.mp4`: each mkv segment is muxed with its audio slice, aligned by the wall-clock start time in
  its filename, then the segments are concatenated. Video gaps are skipped rather than drifting.
  Expect ≤1 s of skew.

## 6. Summarize

Follow `${CLAUDE_PLUGIN_ROOT}/prompts/summarize.md`. Hand the transcript plus sampled video
frames (one every ~30 s, deduplicated) to a subagent if the lecture is long. Deliver the
notes the way the user wants (doc, markdown file, or chat).

## 7. Unattended: join, record, leave

When the user can't be at the Mac (e.g. "4시 수업 자동으로 들어가서 녹화해줘"), run on the day:

```
nohup $S/auto_lecture.sh "<zoom link or meeting ID>" [passcode] --at 15:55 --until 16:40 --end 18:00 --dir $D > $D.log 2>&1 &!
```

It waits for `--at` on the wall clock, joins with `zoom_join.sh`, runs `start.sh`, and stops when the meeting
window has been gone for 3 minutes or at `--end`. At `--end` it first leaves the meeting with `zoom_leave.sh`, then runs `stop.sh`.
If it is not in the meeting by `--until`, it records nothing and posts a notification. `LECTURE_MUTE=1` mutes the speakers.
Every notification plays a sound.
- **Join only** ("9시 수업 카메라 끄고 들어가만 줘"): add `--no-record`. It joins, notifies, keeps the Mac awake until the
  meeting ends or `--end`, and never records or leaves. No `--dir` is needed.
- **"Not in yet" alert**: `--warn 09:05` posts one notification if the join hasn't finished by then, and keeps trying
  until `--until`.
- **Another meeting already open at `--at`** (e.g. the morning class is still up) is not the lecture: it notifies once
  and waits for that window to close, then joins. It never records or closes that meeting; if it is still open at
  `--until`, it gives up (exit 4).
- `zoom_join.sh <link|ID> [pwd] [--until HH:MM[:SS]]` turns an `https://…zoom.us/j/ID?pwd=…` link into `zoommtg://`,
  so there is no browser prompt. If the video preview shows, it presses 참가 only after the camera reads off, then the
  "computer audio" button. Then it reads the **회의 menu** and switches off the mic and camera if either is on, and logs
  `상태: mic:off cam:off`. Exit 4 = the meeting never opened by the deadline; exit 5 = joined, but mic/camera could
  not be confirmed off (auto_lecture alerts).
- `zoom_leave.sh` closes the meeting or waiting-room window and confirms 회의 나가기. It never quits Zoom.
- Both scripts drive Zoom's UI through `zoom_ui.applescript`, which needs the terminal app enabled under
  손쉬운 사용 (Accessibility). Read the log (`$D.log`) to see each click.
- Recommend once that the user turn on, in Zoom → 설정 → 회의/웨비나: **내 카메라 끄기 유지**, **마이크 음소거 유지**
  and **컴퓨터 오디오에 자동으로 연결**. They make the join safe even before the scripts check.
- **Phone alerts**: scripts can only post macOS notifications. If the user wants a push on their phone over Remote
  Control, schedule a one-shot check in the Claude session (CronCreate → read the log → PushNotification). It lives
  only in that session, so tell the user to keep it open.
- **Test end to end without a real class**: open zoom.us/test in Chrome; its 참가 button navigates to
  `https://zoom.us/j/<id>?pwd=…` (catch it with the Navigation API and `preventDefault()` instead of letting Chrome
  open Zoom). Run `auto_lecture.sh "<that link>" --no-record --at <now>` and check the log's `상태:` line, then
  `zoom_leave.sh`. The ID **expires within minutes**, so fetch a fresh one right before each run. The test meeting
  shows an extra "비디오를 시작하여 카메라를 테스트하세요" window that real meetings don't. Never test while a lecture
  is being recorded or about to be joined.

## Gotchas (learned the hard way)

- **Headphones are fine.** The Core Audio tap captures what the system plays, whatever the output
  device. Don't ask the user to switch speakers or install BlackHole. A Multi-Output Device with
  Bluetooth drifts.
- **Silence fails silently.** Without the permission, the tap returns digital silence
  (-91 dB / -inf) with no error. One stray click can show a high *max* volume, so judge by
  *mean* volume and a real transcript.
- **Whisper hallucinates on silence.** It produces "감사합니다", "Thank you" or "시청해주셔서 감사합니다".
  Use `--language ko --hallucination-silence-threshold 2 --condition-on-previous-text False`
  (already in `_common.sh`). If auto-detect says English on a Korean lecture, the input is silence.
- **Window-only video.** Full-screen capture recorded the user's private Slack DMs. Use
  `winrec2` (ScreenCaptureKit `desktopIndependentWindow`), which ignores windows that overlap Zoom.
  A *minimized* Zoom window stops new frames; the last frame repeats.
- **Don't write SCK frames with AVAssetWriter.** Appending ScreenCaptureKit sample buffers to
  AVAssetWriter fails intermittently (`-11800` / `-16341`, every 10–80 s). This happens even with a
  single stream and outside iCloud folders. `winrec2` instead pipes raw BGRA frames at a constant fps
  (repeating the latest frame) into ffmpeg/libx264.
- **Never run two capture streams on the same window.** A second SCK stream (e.g. a test run)
  interrupts the live one with `SCStreamError -3805`. Do static checks only while a lecture is recording.
- **A new mkv segment shows 0 bytes for about a minute.** Static slides compress to almost nothing,
  so ffmpeg's write buffer hasn't flushed yet. This is normal. Check with `lsof -o` or wait before calling it broken.
- **Segment wav headers are finalized only on close.** Read in-progress parts as raw s16le
  after the 44-byte header (`tail -c +45`), as `peek.sh` does. Expect ffmpeg to buffer the
  first seconds.
- **Monitor runs commands through eval.** zsh glob qualifiers like `(N)` fail there, so always
  point Monitor at a script file.
- **Stop by pid, never by name.** Scripts use `$D/.pids`, so a test run never kills a live lecture.
  winrec2 gets exactly one SIGINT (from the loop's trap); ffmpeg finalizes the segment on EOF.
- **The zoommtg:// link stops at the video preview.** It waits for a click on 참가, and the camera is *on* there.
  The `kZMUserDefaultMeetingStartWithVideo` default no longer turns it off. `zoom_ui.applescript` turns the
  camera off and checks it before it presses 참가.
- **The preview can be skipped.** Sometimes the meeting window comes up with no preview at all, so the camera-off step
  never runs (seen 2026-11-27: the camera was on). Don't rely on the preview: `zoom_join.sh` checks the 회의 menu after
  joining, and the Zoom settings above keep the camera and mic off from the start.
- **The meeting window shows no toolbar buttons to Accessibility.** Searching it for "오디오 음소거" finds nothing. The
  menu bar's 회의 (Meeting) menu names the action instead: "오디오 음소거 해제" / "Unmute Audio" means the mic is off,
  "비디오 시작" / "Start Video" means the camera is off.
- **Don't click Zoom blind.** Clicking "button 1" of the 설정 window hit 지금 업그레이드 and opened a checkout window.
  Close windows with ⌘W or a button found by its description.
- **Don't edit a script while a run of it is waiting.** zsh reads a script as it goes, so an edit can change or break
  the waiting run. Edit, then stop that run (by its pid) and start it again.
- **A long `sleep` misses the join time.** It stalls while the Mac sleeps, so wait in short steps on the wall clock,
  as `auto_lecture.sh` does. A closed lid still sleeps the Mac.
- **Always give a waiting loop a deadline.** A loop that waited for the meeting window with no deadline kept
  `caffeinate` running for two days, and it would have recorded whatever meeting opened next.
- **Recording consent.** Remind the user once that recording may need the organizer's permission.
