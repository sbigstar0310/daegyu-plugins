# -*- coding: utf-8 -*-
"""Tests for the merge step: merge.py, and stop.sh on a lecture whose processes are gone.

    uv run --directory lecture-capture pytest tests/test_merge.py

Every input is synthetic. Audio parts are 16 kHz mono s16le wavs from ffmpeg's
lavfi, a few seconds long instead of five minutes. Video segments are short mkvs
named v_HHMMSS by the wall-clock second they open, the way winrec_loop.sh names
them. The `.pids` file holds only dead pids, so stop.sh kills nothing and goes
straight to merging.

The audio is loud in every part except part_001, which is digital silence. A video
segment that is muxed with the wrong slice of audio therefore comes out silent,
which is how the gap tests tell an aligned mux from a drifting one.
"""
import datetime as dt
import subprocess
import sys

import pytest

from conftest import DEAD_PID, SCRIPTS, duration, ffmpeg, mean_db, probe

# Intermediate files live here; only the finals sit next to .pids (see MIDDIR in _common.sh).
MID = "intermediate"

MERGE = SCRIPTS / "merge.py"
PART = 3  # seconds of audio per synthetic part
SEG = 300  # what stop.sh passes (SEGMENT_SEC); only the transcript headers use it


def noon_today():
    return int(dt.datetime.combine(dt.date.today(), dt.time(12, 0, 0)).timestamp())


def hhmmss(epoch):
    return dt.datetime.fromtimestamp(epoch).strftime("%H%M%S")


def write_pids(d, started):
    (d / ".pids").write_text(
        f"audiotee={DEAD_PID}\nstarted={started}\nffmpeg={DEAD_PID}\n"
        f"winrec_loop={DEAD_PID}\nlive_tx={DEAD_PID}\n")


def make_lecture(d, started, loud=(True, False, True), videos=(), transcripts=True):
    """A stopped lecture folder. loud[i] says whether audio part i is a tone or silence.
    videos is a list of (seconds after started, length in seconds)."""
    for sub in ("audio", "video", "transcript", "logs"):
        (d / MID / sub).mkdir(parents=True, exist_ok=True)
    write_pids(d, started)
    for i, is_loud in enumerate(loud):
        src = (f"sine=frequency={440 + 220 * i}:duration={PART}:sample_rate=16000" if is_loud
               else f"anullsrc=r=16000:cl=mono:d={PART}")
        ffmpeg("-f", "lavfi", "-i", src, "-t", PART, "-ac", "1", "-ar", 16000,
               "-c:a", "pcm_s16le", d / MID / "audio" / f"part_{i:03}.wav")
    for off, length in videos:
        ffmpeg("-f", "lavfi", "-i", f"testsrc=size=320x240:rate=10:duration={length}",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
               d / MID / "video" / f"v_{hhmmss(started + off)}.mkv")
    if transcripts:
        for i in range(len(loud)):
            (d / MID / "transcript" / f"part_{i:03}.txt").write_text(f"  구간 {i} 문장입니다.\n\n")
            (d / MID / "transcript" / f"part_{i:03}.srt").write_text(
                f"1\n00:00:00,000 --> 00:00:01,500\n구간 {i} 첫 문장\n\n"
                f"2\n00:00:01,500 --> 00:00:04,250\n구간 {i} 둘째 문장\n")
    return d


def stop(d):
    r = subprocess.run(["zsh", "-f", str(SCRIPTS / "stop.sh"), str(d)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def merge(d, seg=SEG):
    r = subprocess.run([sys.executable, "-I", str(MERGE), str(d), str(seg)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def streams(path):
    return sorted(s["codec_type"] for s in probe(path)["streams"])


# ---- transcripts (no ffmpeg needed) ----

def text_lecture(d, parts, srt=True):
    (d / MID / "transcript").mkdir(parents=True)
    write_pids(d, noon_today())
    for n, body in parts.items():
        (d / MID / "transcript" / f"part_{n:03}.txt").write_text(body)
        if srt:
            (d / MID / "transcript" / f"part_{n:03}.srt").write_text(
                f"1\n00:00:01,500 --> 00:00:03,000\n{body.strip()}\n")
    return d


def test_transcript_parts_are_joined_in_order_under_time_headers(tmp_path):
    # Written out of order on purpose; part 12 starts an hour in.
    d = text_lecture(tmp_path / "lec", {2: "셋째\n", 0: "  첫째  \n\n", 12: "열세째", 1: "둘째"})
    merge(d)
    assert (d / "transcript_full.txt").read_text() == (
        "## [00:00] part_000\n\n첫째\n\n"
        "## [05:00] part_001\n\n둘째\n\n"
        "## [10:00] part_002\n\n셋째\n\n"
        "## [01:00:00] part_012\n\n열세째\n")


def test_srt_cues_are_offset_by_their_part_and_renumbered(tmp_path):
    d = text_lecture(tmp_path / "lec", {0: "a", 1: "b", 12: "c"})
    merge(d)
    assert (d / "transcript_full.srt").read_text() == (
        "1\n00:00:01,500 --> 00:00:03,000\na\n\n"
        "2\n00:05:01,500 --> 00:05:03,000\nb\n\n"
        "3\n01:00:01,500 --> 01:00:03,000\nc\n")


def test_the_segment_length_argument_sets_the_offsets(tmp_path):
    d = text_lecture(tmp_path / "lec", {0: "a", 1: "b"})
    merge(d, seg=60)
    assert "## [01:00] part_001" in (d / "transcript_full.txt").read_text()
    assert "00:01:01,500 --> 00:01:03,000" in (d / "transcript_full.srt").read_text()


def test_malformed_srt_blocks_are_skipped_and_a_missing_srt_is_fine(tmp_path):
    d = text_lecture(tmp_path / "lec", {0: "a", 1: "b"}, srt=False)
    (d / MID / "transcript" / "part_000.srt").write_text(
        "garbage\n\n1\nnot a time\ntext\n\n2\n00:00:02,000 --> 00:00:02,500\nkept\n")
    merge(d)
    assert (d / "transcript_full.srt").read_text() == "1\n00:00:02,000 --> 00:00:02,500\nkept\n"
    assert "## [05:00] part_001\n\nb" in (d / "transcript_full.txt").read_text()


def test_no_transcripts_and_no_video_writes_nothing_and_exits_cleanly(tmp_path):
    d = tmp_path / "lec"
    d.mkdir()
    write_pids(d, noon_today())
    merge(d)
    assert not (d / "transcript_full.txt").exists()
    assert not (d / "transcript_full.srt").exists()
    assert not (d / "lecture.mp4").exists()
    assert sorted(p.name for p in d.iterdir()) == [".pids"], "temp dir left behind"


# ---- audio + video, through stop.sh ----

@pytest.mark.ffmpeg
def test_stop_merges_audio_transcript_and_a_continuous_video(tmp_path):
    started = noon_today()
    d = make_lecture(tmp_path / "lec", started, loud=(True, True, True),
                     videos=[(0, 3 * PART)])
    out = stop(d).stdout
    assert "오디오:" in out and "전사:" in out and "영상:" in out

    audio = d / "lecture_audio.m4a"
    assert streams(audio) == ["audio"]
    assert duration(audio) == pytest.approx(3 * PART, abs=0.2)

    text = (d / "transcript_full.txt").read_text()
    assert text.index("## [00:00] part_000") < text.index("## [05:00] part_001") \
        < text.index("## [10:00] part_002")
    assert "구간 1 문장입니다." in text
    srt = (d / "transcript_full.srt").read_text()
    assert "6\n00:10:01,500 --> 00:10:04,250\n구간 2 둘째 문장" in srt

    mp4 = d / "lecture.mp4"
    assert streams(mp4) == ["audio", "video"]
    assert duration(mp4) == pytest.approx(duration(audio), abs=1.0)
    assert mean_db(mp4) > -40

    assert (d / ".stopped").exists()
    leftovers = {p.name for p in d.iterdir()} - {
        MID, ".pids", ".stopped", ".audio_list.txt",
        "lecture_audio.m4a", "transcript_full.txt", "transcript_full.srt", "lecture.mp4"}
    assert not leftovers, f"left behind: {leftovers}"


@pytest.mark.ffmpeg
def test_a_gap_in_video_is_skipped_and_the_next_segment_keeps_its_own_audio(tmp_path):
    # Video covers part 0 and part 2; the window was lost during part 1 (silence).
    started = noon_today()
    d = make_lecture(tmp_path / "lec", started, videos=[(0, PART), (2 * PART, PART)])
    stop(d)
    mp4 = d / "lecture.mp4"
    assert streams(mp4) == ["audio", "video"]
    # The gap is skipped, not filled: two 3 s segments make a 6 s video.
    assert duration(mp4) == pytest.approx(2 * PART, abs=1.0)
    assert duration(d / "lecture_audio.m4a") == pytest.approx(3 * PART, abs=0.2)
    # Muxed by position instead of by time, the second segment would get part 1's silence.
    assert mean_db(mp4, start=0.3, length=PART - 0.6) > -40
    assert mean_db(mp4, start=PART + 0.3, length=PART - 0.6) > -40


@pytest.mark.ffmpeg
def test_segments_across_midnight_stay_in_time_order(tmp_path):
    # v_235957 (loud part 0) then v_000000 (silent part 1). By name, 000000 sorts first.
    started = int(dt.datetime.combine(dt.date.today(), dt.time(23, 59, 57)).timestamp())
    d = make_lecture(tmp_path / "lec", started, videos=[(0, PART), (PART, PART)])
    assert sorted(p.name for p in (d / MID / "video").iterdir()) == ["v_000000.mkv", "v_235957.mkv"]
    out = stop(d).stdout
    assert "구간 2개" in out and "오디오 00:00부터" in out
    mp4 = d / "lecture.mp4"
    assert duration(mp4) == pytest.approx(2 * PART, abs=1.0)
    assert mean_db(mp4, start=0.3, length=PART - 0.6) > -40      # part 0 first
    assert mean_db(mp4, start=PART + 0.3, length=PART - 0.6) < -80  # then part 1


@pytest.mark.ffmpeg
def test_video_that_starts_late_is_offset_into_the_audio(tmp_path):
    started = noon_today()
    # Window found only during part 2.
    d = make_lecture(tmp_path / "lec", started, loud=(False, False, True),
                     videos=[(2 * PART, PART)])
    out = stop(d).stdout
    assert f"오디오 00:0{2 * PART}부터" in out
    assert mean_db(d / "lecture.mp4") > -40


@pytest.mark.ffmpeg
def test_no_video_still_merges_audio_and_transcript(tmp_path):
    d = make_lecture(tmp_path / "lec", noon_today())
    out = stop(d).stdout
    assert (d / "lecture_audio.m4a").exists()
    assert (d / "transcript_full.txt").exists()
    assert not (d / "lecture.mp4").exists()
    assert "영상:" not in out


@pytest.mark.ffmpeg
def test_stray_and_too_short_video_files_are_ignored(tmp_path):
    started = noon_today()
    d = make_lecture(tmp_path / "lec", started, videos=[(0, PART)])
    # Not v_HHMMSS, and an empty file with a valid name.
    (d / MID / "video" / f"v_{hhmmss(started)}.mkv").rename(d / MID / "video" / "v_keep.mkv")
    ffmpeg("-i", d / MID / "video" / "v_keep.mkv", "-c", "copy", d / MID / "video" / f"v_{hhmmss(started)}.mkv")
    (d / MID / "video" / "v_keep.mkv").rename(d / MID / "video" / "v_120000_old.mkv")
    (d / MID / "video" / f"v_{hhmmss(started + 5)}.mkv").write_bytes(b"")
    out = stop(d).stdout
    assert "구간 1개" in out
    assert duration(d / "lecture.mp4") == pytest.approx(PART, abs=1.0)


@pytest.mark.ffmpeg
def test_stop_no_merge_only_stops(tmp_path):
    d = make_lecture(tmp_path / "lec", noon_today(), videos=[(0, PART)])
    stop_cmd = ["zsh", "-f", str(SCRIPTS / "stop.sh"), str(d), "--no-merge"]
    r = subprocess.run(stop_cmd, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert (d / ".stopped").exists()
    assert not (d / "lecture_audio.m4a").exists()
    assert not (d / "transcript_full.txt").exists()


def test_stop_refuses_a_folder_that_never_started(tmp_path):
    d = tmp_path / "lec"
    d.mkdir()
    r = subprocess.run(["zsh", "-f", str(SCRIPTS / "stop.sh"), str(d)],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert ".pids 없음" in r.stdout
    assert not (d / ".stopped").exists()
