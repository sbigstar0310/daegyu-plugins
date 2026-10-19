"""Merge per-segment transcripts and mux video with audio.

Alignment assumption: audio starts at `started` (epoch in .pids) and is continuous.
Video segments are intermediate/video/v_HHMMSS.mkv, named by ffmpeg (-strftime) with the local
wall-clock time the segment opened; winrec2 emits frames at a constant real-time
rate, so a segment's offset into the audio is (its start - started). Each segment
is muxed with its audio slice, then the parts are concatenated into lecture.mp4,
so a gap in video (window lost, restart) skips that stretch instead of drifting.
Expect up to ~1 s of A/V skew.
"""
import json, re, subprocess, sys
from pathlib import Path

D, SEG = Path(sys.argv[1]), int(sys.argv[2])
MID = D / "intermediate"  # keep in sync with MIDDIR in _common.sh; the finals stay in D itself


def ts(sec, srt=False):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if srt:
        return f"{int(h):02}:{int(m):02}:{s:06.3f}".replace(".", ",")
    return f"{int(h):02}:{int(m):02}:{int(s):02}" if h else f"{int(m):02}:{int(s):02}"


def srt_sec(t):
    h, m, s = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


# transcript_full.txt / .srt
txt, srt, idx = [], [], 1
for p in sorted((MID / "transcript").glob("part_*.txt")):
    n = int(p.stem.split("_")[1])
    off = n * SEG
    txt.append(f"\n## [{ts(off)}] {p.stem}\n")
    txt.append(p.read_text().strip())
    s = p.with_suffix(".srt")
    if s.exists():
        for block in s.read_text().strip().split("\n\n"):
            lines = block.splitlines()
            if len(lines) < 3 or "-->" not in lines[1]:
                continue
            a, b = (srt_sec(x.strip()) + off for x in lines[1].split("-->"))
            srt.append(f"{idx}\n{ts(a, True)} --> {ts(b, True)}\n" + "\n".join(lines[2:]))
            idx += 1
if txt:
    (D / "transcript_full.txt").write_text("\n".join(txt).lstrip() + "\n")
    print(f"전사: {D / 'transcript_full.txt'}")
if srt:
    (D / "transcript_full.srt").write_text("\n\n".join(srt) + "\n")

# lecture.mp4
import datetime as dt, tempfile

pids = dict(l.split("=", 1) for l in (D / ".pids").read_text().split() if "=" in l)
started = int(pids.get("started", 0))
audio = D / "lecture_audio.m4a"
segs = sorted(v for v in (MID / "video").glob("v_*.mkv") if re.fullmatch(r"v_\d{6}", v.stem))
if not (audio.exists() and segs and started):
    sys.exit(0)


def duration(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(p)], capture_output=True, text=True).stdout
    return float(json.loads(out or "{}").get("format", {}).get("duration", 0) or 0)


def seg_epoch(stem):
    base = dt.datetime.fromtimestamp(started)
    t = dt.datetime.strptime(stem[2:], "%H%M%S").time()
    e = dt.datetime.combine(base.date(), t).timestamp()
    return e + 86400 if e < started - 60 else e  # crossed midnight


segs.sort(key=lambda v: seg_epoch(v.stem))  # by time, not name: v_000100 follows v_235900
tmp =Path(tempfile.mkdtemp(dir=MID))
parts = []
for i, v in enumerate(segs):
    dur = duration(v)
    if dur < 1:
        continue
    off = max(0.0, seg_epoch(v.stem) - started)
    part = tmp / f"p{i:03}.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(v), "-ss", f"{off:.2f}", "-t", f"{dur:.2f}", "-i", str(audio),
                    "-map", "0:v", "-map", "1:a?", "-c", "copy", str(part)], check=False)
    if part.exists():
        parts.append(part)
if parts:
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    out = D / "lecture.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)], check=False)
    print(f"영상: {out} (구간 {len(parts)}개, 첫 구간은 오디오 {ts(seg_epoch(segs[0].stem) - started)}부터)")
for f in tmp.iterdir():
    f.unlink()
tmp.rmdir()
