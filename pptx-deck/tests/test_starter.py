# -*- coding: utf-8 -*-
"""Tests for the starter deck in assets/starter/, the worked example of one file
per slide: the full build assembles every slide module in order, and --only
builds one slide into a preview deck with the page number it has in the deck.

    uv run --directory pptx-deck pytest tests/test_starter.py

The builder runs as a subprocess, the way the skill tells an agent to run it.
"""
import os
import subprocess
import sys

import pytest
from pptx import Presentation

STARTER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                                       "skills", "pptx-deck", "assets", "starter"))
BUILD = os.path.join(STARTER, "build_deck.py")

# Per slide: the text of every text frame in shape order, then the notes.
EXPECTED = [
    (["The white reference instance",
      "A starter deck that proves the toolchain works",
      "",
      "pptx-deck"],
     "Three slides. If these render and pass the layout check, "
     "the toolchain is working and you can build the real deck."),
    (["Grammar",
      "Every slide carries a picture",
      "Header: a grey label above a bold title, on every slide\n"
      "Body: at most three blocks, and one of them is a picture\n"
      "Takeaway: one closing line, one phrase on the marker",
      "workflow", "shield-check", "gauge",
      "A slide with no picture is a slide the audience reads instead of listens to.",
      "1"],
     "The icons come from assets/icons. They are already ink black at "
     "stroke width 1.6, so they sit at the same weight as the body text."),
    (["Grammar",
      "Weight, size, and one marker",
      "", "No accent", "One ink on white. Hierarchy is size and weight.",
      "", "One grey", "#CFCFCF for rules, hairlines and card outlines.",
      "", "One marker", "#E6E6E6 behind a single bold phrase per slide.",
      "If you reach for a colour, the answer this instance wants is weight.",
      "2"],
     "Cards are outlined in the one grey, never filled with colour and "
     "never rounded. Each one still carries an icon."),
]


def run(*args, cwd):
    r = subprocess.run([sys.executable, BUILD, *args], cwd=str(cwd),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


def text(prs):
    return [([sh.text_frame.text for sh in s.shapes if sh.has_text_frame],
             s.notes_slide.notes_text_frame.text) for s in prs.slides]


def test_the_full_build_assembles_every_slide_in_order(tmp_path):
    run("-o", "deck.pptx", cwd=tmp_path)
    prs = Presentation(str(tmp_path / "deck.pptx"))
    assert len(prs.slides) == 3
    assert text(prs) == EXPECTED
    # Two icons and three card icons, all found in assets/icons.
    assert sum(sh.shape_type == 13 for s in prs.slides for sh in s.shapes) == 6


@pytest.mark.parametrize("name, index", [("s01_title", 0), ("s02_grammar", 1),
                                         ("s03_weight", 2), ("s03", 2)])
def test_a_preview_holds_one_slide_as_it_is_in_the_deck(tmp_path, name, index):
    run("--only", name, "-o", "preview/one.pptx", cwd=tmp_path)
    prs = Presentation(str(tmp_path / "preview" / "one.pptx"))
    assert len(prs.slides) == 1
    assert text(prs) == [EXPECTED[index]]


def test_a_preview_does_not_write_the_deck(tmp_path):
    r = run("--only", "s02_grammar", cwd=tmp_path)
    assert os.listdir(str(tmp_path)) == ["preview"]
    assert os.listdir(str(tmp_path / "preview")) == ["s02_grammar.pptx"]
    assert "1 slides" in r.stdout


@pytest.mark.parametrize("name", ["s09_missing", "s0"])
def test_an_unknown_or_ambiguous_name_fails(tmp_path, name):
    r = subprocess.run([sys.executable, BUILD, "--only", name], cwd=str(tmp_path),
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "--only %s" % name in r.stderr
    assert not os.listdir(str(tmp_path))


def test_a_hidden_slide_is_kept_unnumbered_and_the_numbers_close_up(tmp_path, monkeypatch):
    sys.path.insert(0, STARTER)
    try:
        import build_deck as B
    finally:
        sys.path.remove(STARTER)
    monkeypatch.setattr(B, "HIDDEN", {"s02_grammar"})
    B.main(["-o", str(tmp_path / "deck.pptx")])
    prs = Presentation(str(tmp_path / "deck.pptx"))
    assert [s._element.get("show") for s in prs.slides] == [None, "0", None]
    got = text(prs)
    assert got[1][0] == EXPECTED[1][0][:-1]          # no page number on the hidden slide
    assert got[2][0] == EXPECTED[2][0][:-1] + ["1"]  # the next slide is page 1
