# -*- coding: utf-8 -*-
"""Tests for how render_real.py treats hidden slides.

    uv run --directory pptx-deck pytest
    uv run --directory pptx-deck pytest -m "not libreoffice"    # skip the real render

Most tests stand in for LibreOffice: the fake writes one PDF page per exported
slide, 200 + 10 x slide number points wide, so the width of a PNG rendered at 72
dpi says which slide is on it. A PNG named s03.png must be 230 px wide.
"""
import os
import re
import subprocess
import sys

import pymupdf
import pytest
from PIL import Image, ImageChops
from pptx import Presentation
from pptx.util import Inches, Pt

import render_real as R

HIDDEN = (2, 5)


def deck(path, hidden=HIDDEN, n=5, show="0"):
    prs = Presentation()
    for i in range(1, n + 1):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
        tb.text_frame.text = "SLIDE %d%s" % (i, " HIDDEN" if i in hidden else "")
        if i in hidden:
            slide._element.set("show", show)
    prs.save(str(path))
    return str(path)


@pytest.fixture
def libreoffice(monkeypatch):
    """A stand-in for soffice. It decides what is hidden the way LibreOffice does,
    not by asking render_real. honours_filter=False plays a LibreOffice older than
    7.4, which leaves hidden slides out regardless; max_pages cuts the PDF short;
    writes=False plays a LibreOffice that fails to write and still exits 0.
    uno="works" or "fails" gives it a python that can import uno."""
    calls = []
    state = {"honours_filter": True, "max_pages": None, "writes": True, "uno": None}

    def export(path, pdf, with_hidden):
        doc = pymupdf.open()
        for i, slide in enumerate(Presentation(path).slides):
            if slide._element.get("show") in ("0", "false") and not with_hidden:
                continue
            if state["max_pages"] is not None and doc.page_count == state["max_pages"]:
                break
            doc.new_page(width=200 + 10 * (i + 1), height=100)
        doc.save(pdf)

    def run(cmd, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        if cmd[0] == "unopython":
            if state["uno"] != "works":
                return subprocess.CompletedProcess(
                    cmd, 1, "", "Traceback\nRuntimeError: LibreOffice did not answer\n")
            export(cmd[3], cmd[4], "--hidden" in cmd)
            return subprocess.CompletedProcess(cmd, 0, "autospace off in 5 paragraphs", "")
        if not state["writes"]:
            return subprocess.CompletedProcess(cmd, 0, "", "Error: source file could not be loaded")
        target, outdir, path = cmd[3], cmd[5], cmd[6]
        export(path, os.path.join(outdir, os.path.splitext(os.path.basename(path))[0] + ".pdf"),
               "ExportHiddenSlides" in target and state["honours_filter"])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(R, "find_soffice", lambda: "soffice")
    monkeypatch.setattr(R, "find_uno_python", lambda soffice: "unopython" if state["uno"] else None)
    monkeypatch.setattr(R.subprocess, "run", run)

    def configure(**kw):
        state.update(kw)
        return calls

    return configure


@pytest.fixture
def render(tmp_path, monkeypatch, capsys):
    out = tmp_path / "render"

    def run(path, *flags):
        monkeypatch.setattr(sys, "argv", ["render_real.py", path, "-o", str(out),
                                          "--dpi", "72"] + list(flags))
        code = R.main()
        io = capsys.readouterr()
        # A run stopped before it starts, as the font gate does, makes no directory.
        names = sorted(os.listdir(str(out))) if out.exists() else []
        pngs = {name: Image.open(str(out / name)).size[0]
                for name in names if name.endswith(".png")}
        return code, io.out, io.err, pngs

    return run


def slide_width(n):
    return 200 + 10 * n


# ---------------------------------------------------------------- the map
@pytest.mark.parametrize("skip_hidden, expected", [
    pytest.param(False, [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], id="rendered"),
    pytest.param(True, [(1, 1), (2, None), (3, 2), (4, 3), (5, None)], id="skipped"),
])
def test_slide_map(tmp_path, skip_hidden, expected):
    prs = Presentation(deck(tmp_path / "d.pptx"))
    assert R.slide_map(prs, skip_hidden) == expected


# ---------------------------------------------------------------- the command
def test_hidden_slides_are_rendered_by_default(tmp_path, libreoffice, render):
    calls = libreoffice()
    code, out, err, pngs = render(deck(tmp_path / "d.pptx"))
    assert code == 0
    assert calls[0][3] == R.PDF_WITH_HIDDEN
    assert pngs == {"s%02d.png" % n: slide_width(n) for n in range(1, 6)}
    assert "hidden  2, 5, rendered like the rest, so page N is slide N." in out
    assert err == ""


def test_skip_hidden_renders_what_the_slideshow_shows(tmp_path, libreoffice, render):
    calls = libreoffice()
    code, out, err, pngs = render(deck(tmp_path / "d.pptx"), "--skip-hidden")
    assert code == 0
    assert calls[0][3] == "pdf"
    assert pngs == {"s%02d.png" % n: slide_width(n) for n in (1, 3, 4)}
    assert "slide to page map" in out
    assert "1>1  2>hidden  3>2  4>3  5>hidden" in out
    assert err == ""


def test_a_libreoffice_that_ignores_the_option_does_not_misname_pages(tmp_path, libreoffice,
                                                                      render):
    libreoffice(honours_filter=False)
    code, out, err, pngs = render(deck(tmp_path / "d.pptx"))
    assert code == 0
    assert "LibreOffice 7.4 or newer" in err
    assert "guess" not in err
    assert pngs == {"s%02d.png" % n: slide_width(n) for n in (1, 3, 4)}
    assert "2>hidden" in out


def test_slides_are_picked_by_slide_number(tmp_path, libreoffice, render):
    libreoffice()
    _code, _out, _err, pngs = render(deck(tmp_path / "d.pptx"), "--slides", "5")
    assert pngs == {"s05.png": slide_width(5)}
    # Skipping hidden slides, slide 4 is on page 3.
    _code, _out, _err, pngs = render(deck(tmp_path / "d.pptx"), "--skip-hidden", "--slides", "4")
    assert pngs == {"s04.png": slide_width(4)}


def test_a_slide_hidden_with_false_is_hidden(tmp_path, libreoffice, render):
    libreoffice()
    code, out, err, pngs = render(deck(tmp_path / "d.pptx", show="false"), "--skip-hidden")
    assert code == 0
    assert pngs == {"s%02d.png" % n: slide_width(n) for n in (1, 3, 4)}
    assert err == ""


def test_an_old_pdf_is_not_rendered_in_place_of_a_failed_export(tmp_path, libreoffice, render):
    libreoffice()
    path = deck(tmp_path / "d.pptx")
    render(path, "--skip-hidden", "--keep-pdf")
    assert (tmp_path / "render" / "d.pdf").exists()
    libreoffice(writes=False)
    code, _out, err, pngs = render(path)
    assert code == 2
    assert "LibreOffice produced no PDF" in err
    assert "7.4" not in err
    assert pngs == {}


def test_a_short_pdf_does_not_crash_the_guess(tmp_path, libreoffice, render):
    libreoffice(max_pages=2)
    code, _out, err, pngs = render(deck(tmp_path / "d.pptx", hidden=()))
    assert code == 0
    assert "2 pages but 5 slides to render" in err
    assert pngs == {"s01.png": slide_width(1), "s02.png": slide_width(2)}


def test_a_deck_without_hidden_slides(tmp_path, libreoffice, render):
    libreoffice()
    code, out, _err, pngs = render(deck(tmp_path / "d.pptx", hidden=()))
    assert code == 0
    assert len(pngs) == 5
    assert "no hidden slides, so page N is slide N" in out


def test_pdf_out_keeps_the_checked_pdf_with_its_hidden_slides(tmp_path, libreoffice, render):
    libreoffice()
    dest = tmp_path / "docs" / "deck.pdf"
    code, out, _err, _pngs = render(deck(tmp_path / "d.pptx"), "--pdf-out", str(dest))
    assert code == 0
    assert [p.rect.width for p in pymupdf.open(str(dest))] == [slide_width(n) for n in range(1, 6)]
    assert not (tmp_path / "render" / "d.pdf").exists()
    assert "pdf     %s" % dest in out


def test_the_contact_sheet_tiles_each_written_slide_at_120_dpi(tmp_path, libreoffice, render):
    libreoffice()
    code, out, _err, pngs = render(deck(tmp_path / "d.pptx"), "--skip-hidden", "--contact-sheet")
    assert code == 0
    assert "contact.png" in pngs
    assert "sheet   contact.png, 3 slides at 120 dpi" in out
    sheet = Image.open(str(tmp_path / "render" / "contact.png")).convert("RGB")
    pad = R.SHEET_PAD
    # Slides 1, 3 and 4 in one row, in cells as wide as the widest: slide 4 at
    # 240 pt x 120 / 72 = 400 px. A tile's right edge says which slide it is.
    for k, n in enumerate((1, 3, 4)):
        x = pad + k * (400 + pad)
        right = x + slide_width(n) * 120 // 72
        assert sheet.getpixel((right - 1, pad)) == (255, 255, 255)
        assert sheet.getpixel((right + 1, pad)) != (255, 255, 255)
        # 100 pt tall is 167 px. Below it, the slide number is drawn in black.
        label = sheet.crop((x, pad + 167, x + 400, pad + 167 + 2 * pad)).convert("L")
        assert label.getextrema()[0] < 64


@pytest.mark.parametrize("flags, hidden_flag", [
    pytest.param((), True, id="rendered"),
    pytest.param(("--skip-hidden",), False, id="skipped"),
])
def test_uno_is_the_route_when_a_python_can_import_it(tmp_path, libreoffice, render,
                                                       flags, hidden_flag):
    calls = libreoffice(uno="works")
    code, out, err, pngs = render(deck(tmp_path / "d.pptx"), *flags)
    assert code == 0
    assert len(calls) == 1 and calls[0][0] == "unopython"
    assert ("--hidden" in calls[0]) == hidden_flag
    assert "export  uno, autospace off" in out
    assert len(pngs) == (5 if hidden_flag else 3)
    assert err == ""


def test_a_failed_uno_export_falls_back_to_the_command_line(tmp_path, libreoffice, render):
    calls = libreoffice(uno="fails")
    code, out, err, pngs = render(deck(tmp_path / "d.pptx"))
    assert code == 0
    assert [c[0] for c in calls] == ["unopython", "soffice"]
    assert calls[1][3] == R.PDF_WITH_HIDDEN
    assert "WARNING: the uno export wrote no PDF (RuntimeError: LibreOffice did not answer)" in err
    assert "export  command line, autospace on" in out
    assert len(pngs) == 5


# ---------------------------------------------------------------- the font gate
def font_deck(path, runs):
    """One slide with one run per (family, bold)."""
    prs = Presentation()
    tf = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(
        Inches(1), Inches(1), Inches(6), Inches(1)).text_frame
    for family, bold in runs:
        r = tf.paragraphs[0].add_run()
        r.text, r.font.name, r.font.bold = "%s %s " % (family, bold), family, bold
    prs.save(str(path))
    return str(path)


def test_families_keeps_the_weight(tmp_path):
    prs = Presentation(font_deck(tmp_path / "d.pptx",
                                 [("Mono", True), ("Mono", False), ("Sans", True)]))
    assert sorted(R.families(prs)) == [("Mono", False), ("Mono", True), ("Sans", True)]


def test_a_missing_bold_warns_and_renders(tmp_path, fonts, libreoffice, render):
    fonts("Mono-hash.ttf", "Mono", "Regular")
    libreoffice()
    code, _out, err, pngs = render(font_deck(tmp_path / "d.pptx", [("Mono", True), ("Mono", False)]))
    assert code == 0
    assert pngs == {"s01.png": slide_width(1)}
    assert 'WARNING: "Mono" has no Bold file' in err
    assert "LibreOffice will synthesise the bold" in err


def test_a_missing_regular_still_stops_the_render(tmp_path, fonts, libreoffice, render):
    fonts("Mono-hash.ttf", "Mono", "Bold")
    libreoffice()
    code, _out, err, pngs = render(font_deck(tmp_path / "d.pptx", [("Mono", False)]))
    assert code == 2
    assert "the deck asks for Mono and no file for it was found" in err
    assert pngs == {}


def test_a_bold_only_family_with_no_file_at_all_stops_the_render(tmp_path, fonts, libreoffice,
                                                                render):
    libreoffice()
    code, _out, err, _pngs = render(font_deck(tmp_path / "d.pptx", [("Mono", True)]))
    assert code == 2
    assert "the deck asks for Mono and no file" in err


# ---------------------------------------------------------------- real LibreOffice
def real_route(monkeypatch, route):
    if route == "command line":
        monkeypatch.setattr(R, "find_uno_python", lambda soffice: None)
    elif R.find_uno_python(R.find_soffice()) is None:
        pytest.skip("no python here can import uno")


@pytest.mark.libreoffice
@pytest.mark.skipif(R.find_soffice() is None, reason="LibreOffice is not installed")
@pytest.mark.parametrize("route", ["uno", "command line"])
@pytest.mark.parametrize("flags, pages", [
    pytest.param((), ["SLIDE 1", "SLIDE 2 HIDDEN", "SLIDE 3", "SLIDE 4", "SLIDE 5 HIDDEN"],
                 id="rendered"),
    pytest.param(("--skip-hidden",), ["SLIDE 1", "SLIDE 3", "SLIDE 4"], id="skipped"),
])
def test_libreoffice_exports_what_the_flag_says(tmp_path, render, monkeypatch, route, flags,
                                                pages):
    real_route(monkeypatch, route)
    if "--skip-hidden" not in flags:
        version = subprocess.run([R.find_soffice(), "--version"],
                                 capture_output=True, text=True).stdout
        m = re.search(r"(\d+)\.(\d+)", version)
        if m and (int(m.group(1)), int(m.group(2))) < (7, 4):
            pytest.skip("LibreOffice %s.%s exports hidden slides from the command line "
                        "only from 7.4" % m.groups())
    code, _out, _err, pngs = render(deck(tmp_path / "d.pptx"), "--keep-pdf", *flags)
    assert code == 0
    doc = pymupdf.open(str(tmp_path / "render" / "d.pdf"))
    assert [page.get_text().strip() for page in doc] == pages
    assert len(pngs) == len(pages)


@pytest.mark.libreoffice
@pytest.mark.skipif(R.find_soffice() is None, reason="LibreOffice is not installed")
def test_uno_closes_the_hangul_latin_gap_and_changes_nothing_else(tmp_path, render, monkeypatch):
    real_route(monkeypatch, "uno")
    prs = Presentation()
    for text in ("Latin only, the same either way", "\ud55c\uad6d\uc5b4Latin\ud55c\uad6d\uc5b4Latin"):
        tb = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(
            Inches(0.5), Inches(1), Inches(9), Inches(1))
        r = tb.text_frame.paragraphs[0].add_run()
        r.text, r.font.size = text, Pt(28)
    path = str(tmp_path / "d.pptx")
    prs.save(path)

    def ink(name):
        im = Image.open(str(tmp_path / "render" / name)).convert("L")
        return im.copy(), im.point(lambda v: 255 if v < 128 else 0).getbbox()

    _code, out, _err, _pngs = render(path)
    assert "export  uno, autospace off" in out
    (latin_uno, _), (_, mixed_uno) = ink("s01.png"), ink("s02.png")
    monkeypatch.setattr(R, "find_uno_python", lambda soffice: None)
    _code, out, _err, _pngs = render(path)
    assert "export  command line, autospace on" in out
    (latin_cli, _), (_, mixed_cli) = ink("s01.png"), ink("s02.png")
    assert ImageChops.difference(latin_uno, latin_cli).getbbox() is None
    # Three Hangul/Latin boundaries, each about 6.7 pt, so 6.7 px at 72 dpi, wider
    # on the command line.
    assert mixed_cli[2] - mixed_uno[2] >= 3 * 6
