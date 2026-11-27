# -*- coding: utf-8 -*-
"""winrec_loop.sh with a stand-in winrec2 (issue #42).

    uv run --directory lecture-capture pytest tests/test_winrec_loop.py

The first winrec2 run stays alive and writes nothing, as the real one did after a rejoin
when it attached to a window that was closing. The loop must notice that ffmpeg has
received no frames, stop that capture and start a new one. The second run writes black
frames, and the loop must leave it alone. ffmpeg is real; nothing touches a window or a tap.
"""
import os
import shutil
import signal
import subprocess
import time

import pytest

from conftest import SCRIPTS

W, H = 64, 48


def wait_for(cond, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.25)
    return False


@pytest.mark.ffmpeg
def test_a_capture_that_delivers_no_frames_is_restarted(tmp_path):
    root = tmp_path / "plugin"
    shutil.copytree(SCRIPTS, root / "scripts")
    (root / "bin").mkdir()
    (root / ".claude-plugin").mkdir()
    state = tmp_path / "state"
    state.mkdir()
    stub = root / "bin" / "winrec2"
    stub.write_text(f"""#!/bin/zsh
[[ $1 == --size ]] && {{ print {W} {H}; exit 0 }}
n=$(( $(cat {state}/n 2>/dev/null || print 0) + 1 )); print $n > {state}/n
print $$ >> {state}/pids
(( n == 1 )) && exec sleep 600          # alive, no frames
while :; do head -c {W * H * 4} /dev/zero || exit 0; sleep 0.1; done
""")
    stub.chmod(0o755)

    d = tmp_path / "lec"
    for sub in ("video", "logs"):
        (d / "intermediate" / sub).mkdir(parents=True)
    tap = subprocess.Popen(["sleep", "600"])          # stands in for audiotee
    (d / ".pids").write_text(f"audiotee={tap.pid}\nstarted={int(time.time())}\n")
    env = dict(os.environ, LECTURE_STALL_SEC="3", LECTURE_STALL_CHECK_SEC="1", LECTURE_STALL_KILL_SEC="2")
    loop = subprocess.Popen(["zsh", str(root / "scripts" / "winrec_loop.sh"), str(d)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    try:
        n = lambda: int((state / "n").read_text()) if (state / "n").exists() else 0
        assert wait_for(lambda: n() >= 2, 25), "the silent capture was never restarted"
        time.sleep(7)                                   # frames now flow: no further restarts
        assert n() == 2
        # mkv bytes lag by up to a minute (SKILL.md, Gotchas); ffmpeg's own frame count does not.
        prog = (d / "intermediate" / "logs" / "ffmpeg_video.progress").read_text()
        frames = [int(l.split("=")[1]) for l in prog.splitlines() if l.startswith("frame=")]
        assert frames and frames[-1] > 20, prog
    finally:
        tap.kill()
        for p in (state / "pids").read_text().split() if (state / "pids").exists() else []:
            try:
                os.kill(int(p), signal.SIGKILL)
            except ProcessLookupError:
                pass
        loop.terminate()
        try:
            out, _ = loop.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            loop.kill()
            out, _ = loop.communicate()
        subprocess.run(["pkill", "-f", str(d)], check=False)
    assert "멈춤" in out, out
