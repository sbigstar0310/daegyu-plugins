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
- **Recording consent.** Remind the user once that recording may need the organizer's permission.
