# -*- coding: utf-8 -*-
"""End to end on the real machine: build, record what `say` speaks, peek, stop, merge.

    LECTURE_CAPTURE_REAL=1 uv run --directory lecture-capture pytest -m real -s

Opt-in only (see conftest.py). It needs Apple Silicon, macOS 14.2+, swift, ffmpeg,
uv, a Korean `say` voice, and the 화면 및 시스템 오디오 녹음 permission for the
terminal running pytest. The speakers (or headphones) play the sentence aloud.

It never touches another capture. It skips when any audiotee, winrec2, winrec_loop.sh
or live_tx.sh is already running, because a second ScreenCaptureKit stream on the
Zoom window interrupts a live lecture; and it stops only through the tmp lecture
dir's own .pids. If a Zoom meeting window is open, lecture.mp4 is checked too;
otherwise the test checks that the merge skips the video cleanly.
"""
import os
import re
import subprocess
import time

import pytest

from conftest import PLUGIN, SCRIPTS, duration, probe

pytestmark = [pytest.mark.real, pytest.mark.ffmpeg]

SENTENCE = "안녕하세요. 오늘 강의에서는 인공지능과 음성 인식에 대해 이야기하겠습니다."
HANGUL = re.compile(r"[가-힣]")
CAPTURE = r"(^|/)(audiotee|winrec2)( |$)|winrec_loop\.sh|live_tx\.sh"


def sh(*args, timeout=120, check=False):
    r = subprocess.run(["zsh", "-f", *map(str, args)], capture_output=True, text=True,
                       timeout=timeout)
    if check:
        assert r.returncode == 0, f"{args}\n{r.stdout}\n{r.stderr}"
    return r


def running_captures(exclude=None):
    out = subprocess.run(["pgrep", "-lf", CAPTURE], capture_output=True, text=True).stdout
    lines = [l for l in out.splitlines() if l.strip()]
    if exclude:
        lines = [l for l in lines if str(exclude) not in l]
    return lines


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True


def korean_voice():
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if "ko_KR" in line:
            return re.split(r"\s{2,}|\s+\(", line.strip())[0]
    return None


def zoom_window_exists():
    for title in ("Zoom 회의", "Zoom Meeting"):
        r = subprocess.run([str(PLUGIN / "bin" / "winrec2"), "--size", "Zoom", title, "1280"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and len(r.stdout.split()) == 2:
            return True
    return False


@pytest.fixture
def lecture(tmp_path):
    """A lecture dir under tmp_path. Whatever happens, its own processes are stopped
    (through its .pids, never by name) and none may survive."""
    d = tmp_path / "lecture_real"
    yield d
    if (d / ".pids").exists():
        sh(SCRIPTS / "stop.sh", d, "--no-merge", timeout=900)
    for f in (d / ".pids", d / ".winrec.pid", d / ".vffmpeg.pid"):
        if f.exists():
            for line in f.read_text().split():
                pid = line.split("=", 1)[-1]
                if not line.startswith("started=") and alive(pid):
                    os.kill(int(pid), 15)


def test_setup_start_peek_stop_on_the_real_machine(lecture):
    others = running_captures()
    if others:
        pytest.skip("another capture is running, so this would disturb it:\n" + "\n".join(others))
    voice = korean_voice()
    if voice is None:
        pytest.skip("no Korean say voice is installed")

    # 1. Build.
    sh(SCRIPTS / "setup.sh", timeout=1200, check=True)
    for name in ("audiotee", "winrec2"):
        b = PLUGIN / "bin" / name
        assert b.is_file() and os.access(b, os.X_OK), f"setup.sh did not build {b}"
    with_video = zoom_window_exists()

    # 2. Speak, then start (the start self-test listens for 5 s on its own tap).
    speaker = subprocess.Popen(
        ["zsh", "-f", "-c", f'for i in {{1..12}}; do say -v "{voice}" "{SENTENCE}"; done'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1)
        r = sh(SCRIPTS / "start.sh", lecture, timeout=60)
        assert r.returncode != 3, ("start.sh heard silence: grant 화면 및 시스템 오디오 녹음 to "
                                   "this terminal\n" + r.stdout)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "녹음 시작" in r.stdout
        pids = dict(l.split("=", 1) for l in (lecture / ".pids").read_text().split())
        assert set(pids) >= {"audiotee", "started", "ffmpeg", "winrec_loop", "live_tx"}
        assert abs(int(pids["started"]) - time.time()) < 60

        time.sleep(20)

        # 3. Peek at the in-progress segment.
        r = sh(SCRIPTS / "peek.sh", lecture, timeout=300, check=True)
        assert "== part_000.wav (진행 중 구간) ==" in r.stdout
        heard = r.stdout.split("==", 2)[-1]
        assert len(HANGUL.findall(heard)) >= 5, f"peek.sh heard no Korean:\n{r.stdout}"
    finally:
        speaker.terminate()
        speaker.wait()

    # 4. Stop and merge.
    r = sh(SCRIPTS / "stop.sh", lecture, timeout=1500, check=True)
    audio = lecture / "lecture_audio.m4a"
    assert audio.exists(), r.stdout
    assert duration(audio) > 15
    text = (lecture / "transcript_full.txt").read_text()
    assert text.startswith("## [00:00] part_000")
    assert len(HANGUL.findall(text)) >= 5, text
    mp4 = lecture / "lecture.mp4"
    if with_video:
        assert mp4.exists(), r.stdout
        kinds = sorted(s["codec_type"] for s in probe(mp4)["streams"])
        assert kinds == ["audio", "video"]
        assert duration(mp4) == pytest.approx(duration(audio), abs=5)
    else:
        # No Zoom window: no segments, no mp4, and stop.sh still succeeded.
        assert not list((lecture / "video").glob("v_*.mkv"))
        assert not mp4.exists()
        assert "영상:" not in r.stdout

    # 5. Nothing of this lecture is left running.
    for name, pid in pids.items():
        if name != "started":
            assert not alive(pid), f"{name} ({pid}) is still running"
    for f in (".winrec.pid", ".vffmpeg.pid"):
        if (lecture / f).exists():
            assert not alive((lecture / f).read_text().strip()), f
    left = subprocess.run(["pgrep", "-lf", str(lecture)], capture_output=True, text=True).stdout
    assert not left.strip(), f"processes still reference {lecture}:\n{left}"
    assert not (lecture / ".audio.fifo").exists()
