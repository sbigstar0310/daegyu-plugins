# -*- coding: utf-8 -*-
"""Tests for the helpers in _common.sh, sourced into a fresh zsh.

    uv run --directory lecture-capture pytest tests/test_common.py

HOME and LECTURE_ROOT point into tmp_path, so nothing here sees the user's real
~/Desktop/lecture_* folders.
"""
import os
import re
import subprocess
import time

import pytest

from conftest import DEAD_PID, PLUGIN, SCRIPTS, zsh

COMMON = SCRIPTS / "_common.sh"


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home"
    (h / "Desktop").mkdir(parents=True)
    return h


def run(code, home, **env):
    env = {"HOME": str(home), **env}
    env.setdefault("LECTURE_ROOT", "")
    r = zsh(f"source {COMMON}; {code}", env={k: v for k, v in env.items()})
    return r


def real(p):
    return os.path.realpath(str(p))


def test_sourcing_resolves_the_plugin_root_and_binaries(home):
    r = run('print -r -- "$ROOT|$BIN|$AUDIOTEE|$WINREC|$SEGMENT_SEC"', home)
    assert r.returncode == 0, r.stderr
    root = real(PLUGIN)
    assert r.stdout.strip() == f"{root}|{root}/bin|{root}/bin/audiotee|{root}/bin/winrec2|300"


def test_whisper_model_and_language_can_be_overridden(home):
    r = run('print -r -- "$WHISPER_MODEL|$WHISPER_LANG"', home)
    assert r.stdout.strip() == "mlx-community/whisper-large-v3-turbo|ko"
    r = run('print -r -- "$WHISPER_MODEL|$WHISPER_LANG"', home,
            LECTURE_WHISPER_MODEL="m/tiny", LECTURE_LANG="en")
    assert r.stdout.strip() == "m/tiny|en"


def test_lecture_dir_defaults_to_a_timestamped_folder_on_the_desktop(home):
    r = zsh(f"unset LECTURE_ROOT; source {COMMON}; lecture_dir", env={"HOME": str(home)})
    assert r.returncode == 0, r.stderr
    out = r.stdout.strip()
    assert os.path.dirname(real(out)) == real(home / "Desktop")
    m = re.fullmatch(r"lecture_(\d{8})_(\d{4})", os.path.basename(out))
    assert m, out
    # Within a minute of now (the test may straddle a minute boundary).
    stamp = time.mktime(time.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M"))
    assert abs(stamp - time.time()) < 120


def test_lecture_dir_honours_lecture_root(home, tmp_path):
    root = tmp_path / "lectures"
    r = run("lecture_dir", home, LECTURE_ROOT=str(root))
    assert os.path.dirname(real(r.stdout.strip())) == real(root)
    assert os.path.basename(r.stdout.strip()).startswith("lecture_")


def test_lecture_dir_takes_an_explicit_dir_and_makes_it_absolute(home, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    r = zsh(f"source {COMMON}; cd {work}; lecture_dir sub/x",
            env={"HOME": str(home), "LECTURE_ROOT": str(tmp_path / "ignored")})
    assert r.stdout.strip().startswith("/")
    assert real(r.stdout.strip()) == real(work / "sub" / "x")
    r = run(f"lecture_dir {tmp_path}/a/../b", home)
    assert real(r.stdout.strip()) == real(tmp_path / "b")


def test_existing_dir_prefers_the_argument(home, tmp_path):
    r = run(f"existing_dir {tmp_path}/given", home)
    assert r.returncode == 0
    assert real(r.stdout.strip()) == real(tmp_path / "given")


def test_existing_dir_finds_the_newest_lecture_with_pids(home, tmp_path):
    root = tmp_path / "root"
    for name, age in (("lecture_old", 300), ("lecture_new", 10)):
        (root / name).mkdir(parents=True)
        pids = root / name / ".pids"
        pids.write_text("started=1\n")
        t = time.time() - age
        os.utime(pids, (t, t))
    (root / "lecture_nopids").mkdir()  # newer, but never started
    r = run("existing_dir", home, LECTURE_ROOT=str(root))
    assert r.returncode == 0, r.stderr
    assert real(r.stdout.strip()) == real(root / "lecture_new")


def test_existing_dir_fails_when_there_is_no_lecture(home, tmp_path):
    r = run("existing_dir", home, LECTURE_ROOT=str(tmp_path / "empty"))
    assert r.returncode == 1
    assert r.stdout == ""
    assert "녹음 폴더를 찾을 수 없음" in r.stderr


def test_pid_of_reads_the_last_entry_for_a_name(home, tmp_path):
    (tmp_path / ".pids").write_text("audiotee=11\nstarted=1700000000\nffmpeg=22\naudiotee=33\n")
    r = run(f"print -r -- \"$(pid_of {tmp_path} audiotee)|$(pid_of {tmp_path} ffmpeg)|"
            f"$(pid_of {tmp_path} live_tx)|$(pid_of {tmp_path}/none audiotee)\"", home)
    assert r.stdout.strip() == "33|22||"


def test_alive_is_true_only_for_a_running_pid(home):
    p = subprocess.Popen(["sleep", "30"])
    try:
        r = run(f"alive {p.pid} && echo yes; alive {DEAD_PID} || echo dead; "
                f"alive '' || echo empty", home)
        assert r.stdout.split() == ["yes", "dead", "empty"]
    finally:
        p.kill()
        p.wait()


@pytest.mark.ffmpeg
def test_mean_db_reads_wav_and_raw_s16le(home, tmp_path):
    from conftest import ffmpeg
    loud, quiet = tmp_path / "loud.wav", tmp_path / "quiet.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=1:sample_rate=16000",
           "-ac", "1", "-c:a", "pcm_s16le", loud)
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono", "-t", "1", "-c:a", "pcm_s16le", quiet)
    raw = tmp_path / "loud.raw"
    raw.write_bytes(loud.read_bytes()[44:])
    r = run(f"mean_db {loud}; mean_db {raw} -raw; mean_db {quiet}", home)
    loud_db, raw_db, quiet_db = r.stdout.split()
    assert -30 < float(loud_db) < 0
    assert abs(float(raw_db) - float(loud_db)) < 1
    assert quiet_db == "-inf" or float(quiet_db) < -90


def fake_bin(tmp_path, **scripts):
    """A PATH dir holding stub commands that print their own name and arguments."""
    d = tmp_path / "fakebin"
    d.mkdir(exist_ok=True)
    for name, body in scripts.items():
        f = d / name
        f.write_text(f"#!/bin/zsh\n{body}\n")
        f.chmod(0o755)
    return d


def test_run_python_uses_python3_when_it_is_usable(home, tmp_path):
    fb = fake_bin(tmp_path, python3='print "python3 $@"', uv='print "uv $@"')
    r = run("run_python merge.py a b", home, PATH=f"{fb}:/usr/bin:/bin")
    assert r.stdout.strip() == "python3 -I merge.py a b"


def test_run_python_falls_back_to_a_uv_managed_python_when_python3_is_unusable(home, tmp_path):
    fb = fake_bin(tmp_path, python3='print "python3 $@"', uv='print "uv $@"')
    r = run("python_is_usable() { return 1 }; run_python merge.py a b", home, PATH=f"{fb}:/usr/bin:/bin")
    assert r.stdout.strip() == "uv run --no-project --managed-python python -I merge.py a b"


def test_python3_counts_as_unusable_when_it_is_the_macos_stub_without_clt(home, tmp_path):
    # Fake both halves: command -v resolves to the stub path, xcode-select says there is no CLT.
    fb = fake_bin(tmp_path, **{"xcode-select": "exit 2"})
    r = run('command() { [[ $2 == python3 ]] && print /usr/bin/python3 || builtin command "$@" }; '
            "python_is_usable && print usable || print unusable", home, PATH=f"{fb}:/usr/bin:/bin")
    assert r.stdout.strip() == "unusable"


def test_python3_counts_as_usable_when_the_macos_stub_has_clt_behind_it(home, tmp_path):
    fb = fake_bin(tmp_path, **{"xcode-select": "print /Library/Developer/CommandLineTools"})
    r = run('command() { [[ $2 == python3 ]] && print /usr/bin/python3 || builtin command "$@" }; '
            "python_is_usable && print usable || print unusable", home, PATH=f"{fb}:/usr/bin:/bin")
    assert r.stdout.strip() == "usable"
