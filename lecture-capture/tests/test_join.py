# -*- coding: utf-8 -*-
"""Join safety: mic/camera state from Zoom's 회의 menu, the "another meeting is open" gate,
the "not in yet" alert, and auto_lecture.sh driven end to end with every Zoom/tap step stubbed.

    uv run --directory lecture-capture pytest tests/test_join.py

Nothing here touches Zoom, a tap or a window: the auto_lecture tests run a copy of the
scripts whose winrec2, zoom_join.sh, zoom_leave.sh, start.sh, stop.sh, osascript and
caffeinate are stand-ins that only write to files under tmp_path.
"""
import os
import shutil
import subprocess
import time

import pytest

from conftest import SCRIPTS, zsh

COMMON = SCRIPTS / "_common.sh"


def fn(code):
    r = zsh(f"source {COMMON}; {code}")
    return r


# ---- #36: mic/camera state from the 회의 / Meeting menu --------------------------------

@pytest.mark.parametrize("items, want", [
    (["전체 화면", "오디오 음소거 해제", "비디오 시작", "공유 시작"], "mic:off cam:off"),
    (["오디오 음소거", "비디오 중지"], "mic:on cam:on"),
    (["오디오 음소거 해제", "비디오 중지"], "mic:off cam:on"),
    (["Unmute Audio", "Start Video"], "mic:off cam:off"),
    (["Mute Audio", "Stop Video"], "mic:on cam:on"),
    (["Mute audio", "Stop video"], "mic:on cam:on"),
    (["오디오 연결", "비디오 시작"], "mic:none cam:off"),
    (["Join Audio", "Start Video"], "mic:none cam:off"),
    ([], "mic:unknown cam:unknown"),
    (["missing value", "전체 화면"], "mic:unknown cam:unknown"),
])
def test_zoom_av_state_reads_the_meeting_menu(items, want):
    args = " ".join(f"'{i}'" for i in items)
    r = fn(f"zoom_av_state {args}")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == want


def test_zoom_av_state_takes_the_applescript_output_split_on_bars():
    r = fn("zoom_av_state ${(s:|:)$(print -r -- '전체 화면|오디오 음소거|비디오 시작')}")
    assert r.stdout.strip() == "mic:on cam:off"


@pytest.mark.parametrize("state, safe", [
    ("mic:off cam:off", True),
    ("mic:none cam:off", True),
    ("mic:on cam:off", False),
    ("mic:off cam:on", False),
    ("mic:unknown cam:off", False),
    ("mic:off cam:unknown", False),
])
def test_av_is_off_only_when_both_are_confirmed_off(state, safe):
    r = fn(f"av_is_off '{state}'")
    assert (r.returncode == 0) == safe


# ---- #37: a meeting that is already open is not the lecture ------------------------------

@pytest.mark.parametrize("now, until, up, want", [
    (100, 200, 0, "join"),
    (100, 200, 1, "wait"),
    (200, 200, 1, "giveup"),
    (250, 200, 1, "giveup"),
    (250, 200, 0, "join"),
])
def test_join_gate(now, until, up, want):
    r = fn(f"join_gate {now} {until} {up}")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == want


# ---- #38: "not in yet" alert -------------------------------------------------------------

@pytest.mark.parametrize("now, warn, joined, due", [
    (100, 200, 0, False),
    (200, 200, 0, True),
    (300, 200, 0, True),
    (300, 200, 1, False),
    (300, "''", 0, False),
])
def test_warn_due(now, warn, joined, due):
    r = fn(f"warn_due {now} {warn} {joined}")
    assert (r.returncode == 0) == due


def test_epoch_at_takes_seconds_too():
    r = fn('a=$(epoch_at 10:20); b=$(epoch_at 10:20:30); print $(( b - a ))')
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "30"


# ---- auto_lecture.sh end to end, with stand-ins -------------------------------------------

STUB = "#!/bin/zsh\n"


@pytest.fixture
def rig(tmp_path):
    """A copy of the plugin whose Zoom, tap and notification steps only touch files."""
    root = tmp_path / "plugin"
    shutil.copytree(SCRIPTS, root / "scripts")
    (root / "bin").mkdir()
    (root / ".claude-plugin").mkdir()
    state = tmp_path / "state"
    state.mkdir()
    calls = state / "calls"

    def stub(path, body):
        path.write_text(STUB + body)
        path.chmod(0o755)

    # winrec2 --size: "the meeting window is up" while state/window exists.
    stub(root / "bin" / "winrec2", f'[[ -e {state}/window ]] && {{ print 1280 720; exit 0 }}; exit 1\n')
    s = root / "scripts"
    stub(s / "zoom_join.sh", f'print "join $*" >> {calls}; sleep ${{JOIN_DELAY:-0}}; '
                             f'touch {state}/window; print "상태: mic:off cam:off"; exit ${{JOIN_RC:-0}}\n')
    stub(s / "zoom_leave.sh", f'print leave >> {calls}; rm -f {state}/window; exit 0\n')
    stub(s / "start.sh", f'print "start $*" >> {calls}; exit 0\n')
    stub(s / "stop.sh", f'print "stop $*" >> {calls}; exit 0\n')
    fake = tmp_path / "fakebin"
    fake.mkdir()
    stub(fake / "osascript", f'print -r -- "osascript $*" >> {state}/notes\n')
    stub(fake / "caffeinate", "exit 0\n")
    return {"root": root, "state": state, "calls": calls, "path": f"{fake}:{os.environ['PATH']}"}


def hms(offset=0):
    return time.strftime("%H:%M:%S", time.localtime(time.time() + offset))


def auto(rig, *args, timeout=40, **env):
    e = dict(os.environ, PATH=rig["path"], LECTURE_POLL_SEC="1", LECTURE_GONE_SEC="2", **env)
    return subprocess.run(["zsh", str(rig["root"] / "scripts" / "auto_lecture.sh"), *args],
                          capture_output=True, text=True, env=e, timeout=timeout)


def lines(p):
    return p.read_text().splitlines() if p.exists() else []


def test_no_record_joins_and_never_records_or_leaves(rig, tmp_path):
    def close_window_later():
        time.sleep(4)
        (rig["state"] / "window").unlink()
    import threading
    threading.Thread(target=close_window_later, daemon=True).start()
    r = auto(rig, "123456789", "--no-record", "--at", hms(), "--until", hms(60), "--end", hms(120))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = lines(rig["calls"])
    assert calls and calls[0].startswith("join 123456789")
    assert not [c for c in calls if c.startswith(("start", "stop", "leave"))], calls
    notes = rig["state"] / "notes"
    assert "입장" in notes.read_text()
    assert not (tmp_path / "home").exists()


def test_a_meeting_already_open_is_waited_out_then_given_up_on(rig):
    (rig["state"] / "window").touch()
    r = auto(rig, "123456789", "--at", hms(), "--until", hms(3), "--end", hms(60))
    assert r.returncode == 4, r.stdout + r.stderr
    assert lines(rig["calls"]) == [], "it must neither join, record nor leave another meeting"
    assert (rig["state"] / "window").exists()
    notes = lines(rig["state"] / "notes")
    assert len([n for n in notes if "기다려요" in n]) == 1, notes   # told once, not every poll
    assert [n for n in notes if "포기" in n], notes


def test_it_joins_once_the_other_meeting_closes(rig):
    (rig["state"] / "window").touch()
    import threading
    def close_later():
        time.sleep(3)
        (rig["state"] / "window").unlink()
    threading.Thread(target=close_later, daemon=True).start()
    r = auto(rig, "123456789", "--no-record", "--at", hms(), "--until", hms(30), "--end", hms(12))
    assert r.returncode == 0, r.stdout + r.stderr
    assert lines(rig["calls"])[0].startswith("join"), r.stdout


def test_warn_posts_one_alert_with_a_sound_while_still_joining(rig):
    r = auto(rig, "123456789", "--no-record", "--at", hms(), "--warn", hms(), "--until", hms(60),
             "--end", hms(8), JOIN_DELAY="3")
    assert r.returncode == 0, r.stdout + r.stderr
    notes = lines(rig["state"] / "notes")
    warns = [n for n in notes if "아직" in n]
    assert len(warns) == 1, notes
    assert 'sound name "Glass"' in warns[0]


def test_no_warn_once_joined(rig):
    r = auto(rig, "123456789", "--no-record", "--at", hms(), "--warn", hms(3), "--until", hms(60),
             "--end", hms(7))
    assert r.returncode == 0, r.stdout + r.stderr
    assert not [n for n in lines(rig["state"] / "notes") if "아직" in n]


def test_recording_mode_still_records_and_stops(rig, tmp_path):
    d = tmp_path / "lec"
    import threading
    def close_later():
        time.sleep(4)
        (rig["state"] / "window").unlink()
    threading.Thread(target=close_later, daemon=True).start()
    r = auto(rig, "123456789", "--at", hms(), "--until", hms(60), "--end", hms(60), "--dir", str(d))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = lines(rig["calls"])
    assert calls[0].startswith("join") and calls[1] == f"start {d}" and calls[-1] == f"stop {d}", calls


def test_a_join_that_cannot_confirm_mic_and_camera_off_alerts(rig, tmp_path):
    r = auto(rig, "123456789", "--no-record", "--at", hms(), "--until", hms(60), "--end", hms(6),
             JOIN_RC="5")
    assert r.returncode == 0, r.stdout + r.stderr
    notes = (rig["state"] / "notes").read_text()
    assert "카메라" in notes or "마이크" in notes
