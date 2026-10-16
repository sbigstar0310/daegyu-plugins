# -*- coding: utf-8 -*-
"""Shared paths and helpers.

    uv run --directory lecture-capture pytest                      # static + unit
    uv run --directory lecture-capture pytest -m "not ffmpeg"      # static only
    LECTURE_CAPTURE_REAL=1 uv run --directory lecture-capture pytest -m real

Tests marked `real` record the machine's real system audio and may open a
ScreenCaptureKit stream, so they run only when LECTURE_CAPTURE_REAL=1. A second
capture stream on the Zoom window interrupts a live lecture (SKILL.md, Gotchas),
so never set it while a lecture is being recorded.

Tests marked `ffmpeg` skip when ffmpeg/ffprobe are missing; they never touch a
microphone, a tap or a window.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN / "scripts"
REPO = PLUGIN.parent

HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
REAL = os.environ.get("LECTURE_CAPTURE_REAL") == "1"

# A pid no process can have (macOS caps pids at 99998), for a .pids file whose
# processes are all gone.
DEAD_PID = 99999999


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "real" in item.keywords and not REAL:
            item.add_marker(pytest.mark.skip(reason="set LECTURE_CAPTURE_REAL=1 to record for real"))
        if "ffmpeg" in item.keywords and not HAVE_FFMPEG:
            item.add_marker(pytest.mark.skip(reason="ffmpeg/ffprobe are not installed"))


def zsh(code, env=None, cwd=None, timeout=60):
    """Run code in a fresh `zsh -f` (no user rc files) and return the CompletedProcess."""
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run(["zsh", "-f", "-c", code], capture_output=True, text=True,
                          env=full, cwd=cwd, timeout=timeout)


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
                   check=True)


def probe(path):
    """ffprobe's format + streams as a dict."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def duration(path):
    return float(probe(path)["format"]["duration"])


def mean_db(path, start=None, length=None):
    """Mean volume of path's audio (optionally of [start, start+length)), in dB."""
    cmd = ["ffmpeg", "-hide_banner"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if length is not None:
        cmd += ["-t", str(length)]
    cmd += ["-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    for line in err.splitlines():
        if "mean_volume:" in line:
            v = line.split("mean_volume:")[1].split("dB")[0].strip()
            return float("-inf") if v == "-inf" else float(v)
    raise AssertionError("no volumedetect output:\n" + err)
