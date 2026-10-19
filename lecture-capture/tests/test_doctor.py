# -*- coding: utf-8 -*-
"""doctor.sh with a stripped-down PATH and an empty HOME, so it sees a machine with nothing installed.

    uv run --directory lecture-capture pytest tests/test_doctor.py

--quick plays no sound and opens no tap, so these are safe while a lecture is recording.
"""
import shutil
import subprocess
import sys

import pytest

from conftest import SCRIPTS

DOCTOR = SCRIPTS / "doctor.sh"
BARE_PATH = "/usr/bin:/bin"

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="doctor.sh checks macOS specifics")


def doctor(tmp_path, *args):
    (tmp_path / "home").mkdir(exist_ok=True)
    env = {"HOME": str(tmp_path / "home"), "PATH": BARE_PATH, "LECTURE_ROOT": str(tmp_path / "out")}
    return subprocess.run(["zsh", str(DOCTOR), *args], capture_output=True, text=True, env=env, timeout=60)


def test_it_fails_and_says_how_to_fix_it_when_ffmpeg_is_missing(tmp_path):
    if shutil.which("ffmpeg", path=BARE_PATH):
        pytest.skip("ffmpeg is on the bare PATH")
    r = doctor(tmp_path, "--quick")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "✗ ffmpeg 없음" in r.stdout
    assert "brew install ffmpeg" in r.stdout
    assert "문제" in r.stdout.splitlines()[-1]


def test_quick_skips_the_sound_test(tmp_path):
    r = doctor(tmp_path, "--quick")
    assert "소리 시험을 건너뜀" in r.stdout
    assert "신호음이 납니다" not in r.stdout


def test_it_reports_the_output_folder_it_will_use(tmp_path):
    r = doctor(tmp_path, "--quick")
    assert str(tmp_path / "out") in r.stdout
    assert (tmp_path / "out").is_dir()


def test_an_unknown_flag_is_rejected(tmp_path):
    r = doctor(tmp_path, "--nope")
    assert r.returncode == 2
    assert "usage" in r.stdout
