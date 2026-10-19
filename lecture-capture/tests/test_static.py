# -*- coding: utf-8 -*-
"""Static checks: syntax, manifests, and guards on what the scripts may do.

    uv run --directory lecture-capture pytest tests/test_static.py

Nothing here runs a script; it only parses and greps them, so it is safe while a
lecture is being recorded.
"""
import json
import py_compile
import re
import shutil
import subprocess

import pytest

from conftest import PLUGIN, REPO, SCRIPTS

SHELL_SCRIPTS = sorted(SCRIPTS.glob("*.sh"))
ALL_SCRIPTS = SHELL_SCRIPTS + [SCRIPTS / "merge.py", SCRIPTS / "winrec2" / "main.swift"]


def test_the_scripts_the_skill_names_are_all_there():
    names = {p.name for p in SHELL_SCRIPTS}
    assert {"_common.sh", "setup.sh", "doctor.sh", "start.sh", "stop.sh", "peek.sh", "live_tx.sh",
            "watch.sh", "winrec_loop.sh"} <= names
    assert (SCRIPTS / "merge.py").is_file()
    assert (SCRIPTS / "winrec2" / "main.swift").is_file()


@pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh is not installed")
@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_every_shell_script_parses_in_zsh(script):
    r = subprocess.run(["zsh", "-n", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("script", [s for s in SHELL_SCRIPTS if s.name != "_common.sh"],
                         ids=lambda p: p.name)
def test_every_runnable_script_is_executable_zsh(script):
    assert script.read_text().startswith("#!/bin/zsh\n")
    assert script.stat().st_mode & 0o111, f"{script.name} is not executable"


def test_merge_py_compiles(tmp_path):
    py_compile.compile(str(SCRIPTS / "merge.py"), cfile=str(tmp_path / "merge.pyc"), doraise=True)


def test_plugin_json_and_the_marketplace_agree():
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    assert plugin["name"] == "lecture-capture"
    assert re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])
    entries = [p for p in market["plugins"] if p["name"] == plugin["name"]]
    assert len(entries) == 1, "lecture-capture must be listed exactly once in marketplace.json"
    entry = entries[0]
    assert entry["source"] == "./lecture-capture"
    assert (REPO / entry["source"]).resolve() == PLUGIN
    # The marketplace entries carry no version; if one is ever added it must match.
    if "version" in entry:
        assert entry["version"] == plugin["version"]


def test_skill_md_has_frontmatter_with_name_and_description():
    text = (PLUGIN / "skills" / "lecture-capture" / "SKILL.md").read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with a --- frontmatter block"
    fields = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
    assert fields.get("name", "").strip() == "lecture-capture"
    assert len(fields.get("description", "").strip()) > 40


def test_the_summarize_prompt_the_skill_points_at_exists():
    assert (PLUGIN / "prompts" / "summarize.md").is_file()


# Paths that only exist on one machine or in one session.
FORBIDDEN_PATHS = [
    r"/private/tmp", r"(?<![\w$])/tmp/", r"scratchpad", r"/Users/", r"/home/\w", r"/var/folders",
    r"claude-\d+/",
]


@pytest.mark.parametrize("script", ALL_SCRIPTS, ids=lambda p: p.name)
def test_no_script_hardcodes_a_machine_or_session_path(script):
    text = script.read_text()
    hits = [(pat, m.group(0)) for pat in FORBIDDEN_PATHS for m in re.finditer(pat, text)]
    assert not hits, f"{script.name} hardcodes {hits}"


# Killing by name would stop another lecture's capture (or a test run's), so every
# kill must go through a pid this lecture wrote, and pkill/killall must be scoped
# to the lecture dir if they are ever used.
@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_no_script_kills_by_name_outside_its_lecture_dir(script):
    for n, line in enumerate(script.read_text().splitlines(), 1):
        code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        if re.search(r"\b(pkill|killall)\b", code):
            assert re.search(r"\$\{?D\b", code), f"{script.name}:{n} kills by name: {line.strip()}"


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_every_kill_targets_a_recorded_pid(script):
    """kill's operand must be a pid this lecture recorded: pid_of, a $D/.*.pid file,
    or a $! captured into a variable. Never a literal, a job spec or a process group."""
    ok = re.compile(r"\$\(pid_of \$D \w+\)|\$\(cat \$D/\.\w+\.pid\)|\$\w+\b")
    for n, line in enumerate(script.read_text().splitlines(), 1):
        for m in re.finditer(r"\bkill\s+(-\w+\s+)?(?P<arg>\S+)", line):
            if m.group("arg").startswith("-0"):
                continue
            arg = line[m.start("arg"):]
            assert ok.match(arg), f"{script.name}:{n} kills something unrecorded: {line.strip()}"
            assert not re.match(r"-?\d+\b|%", arg), f"{script.name}:{n}: {line.strip()}"


def test_stop_reads_its_pids_from_the_lecture_dir_only():
    text = (SCRIPTS / "stop.sh").read_text()
    assert "pgrep" not in text and "ps " not in text
    assert "existing_dir" in text and "$D/.pids" in text


# The finals sit at the top of a lecture folder; everything intermediate goes under MIDDIR.
def test_merge_py_and_common_agree_on_the_intermediate_folder():
    common = re.search(r"^MIDDIR=(\w+)", (SCRIPTS / "_common.sh").read_text(), re.M).group(1)
    merge = re.search(r'^MID = D / "(\w+)"', (SCRIPTS / "merge.py").read_text(), re.M).group(1)
    assert common == merge


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_no_script_puts_intermediates_next_to_the_finals(script):
    for n, line in enumerate(script.read_text().splitlines(), 1):
        assert not re.search(r"\$D/(audio|video|transcript|logs)\b", line), \
            f"{script.name}:{n} uses $D/... instead of $MID/...: {line.strip()}"


def test_merge_py_reads_intermediates_only_from_the_intermediate_folder():
    text = (SCRIPTS / "merge.py").read_text()
    assert not re.search(r'\bD / "(audio|video|transcript|logs)"', text)
