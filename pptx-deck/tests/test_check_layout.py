# -*- coding: utf-8 -*-
"""Tests for the height and font arithmetic in check_layout.py and fix_orphans.py.

    uv run --directory pptx-deck pytest

Every expected number can be worked by hand. The test fonts make each character
half an em wide, so at 12 pt a character is 6 pt, "line 10 of ten" is 84 pt, and
the 4 in box with 0.1 in insets holds 273.6 pt per line.
"""
import sys

import pytest
from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

import check_layout as C
import fix_orphans as M

TEN = ["line %d of ten" % (i + 1) for i in range(10)]


def deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(10), Inches(5.625)
    return prs


def text_box(prs, height, lines, family="Inter", bold=False, name="box", wrap=True):
    """The issue's repro frame on a new slide: 4 in wide, 0.1 in insets, 12 pt,
    single spaced, one paragraph per line. A "\v" in a line is a line break."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tb = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(height))
    tb.name = name
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Inches(0.1))
    for i, text in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.0
        p.space_after = Pt(0)
        for k, part in enumerate(text.split("\v")):
            if k:
                p.add_line_break()
            r = p.add_run()
            r.text = part
            r.font.size = Pt(12)
            r.font.name = family
            r.font.bold = bold
    return tb


def paragraph(spacing=None, before=None, after=None):
    prs = deck()
    tf = prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_textbox(
        0, 0, Inches(1), Inches(1)).text_frame
    p = tf.paragraphs[0]
    if spacing is not None:
        p.line_spacing = spacing
    if before is not None:
        p.space_before = Pt(before)
    if after is not None:
        p.space_after = Pt(after)
    return p


def overflow(prs):
    rep = C.Report()
    C.check_overflow(prs, rep, "Inter")
    return rep


# ---------------------------------------------------------------- line height
# LibreOffice draws 12 pt at 1.0 on a 14.40 pt pitch, 7.5 pt at 1.15 on 10.35 and
# 6 pt at 1.08 on 7.78: the single-spaced 1.2 em, times the spacing.
@pytest.mark.parametrize("spacing, size, n_lines, points", [
    pytest.param(1.0, 12, 10, 144.0, id="1.0 at 12 pt"),
    pytest.param(1.15, 7.5, 1, 10.35, id="1.15 at 7.5 pt"),
    pytest.param(1.08, 6, 1, 7.776, id="1.08 at 6 pt"),
    pytest.param(None, 14, 3, 50.4, id="unset is single spaced"),
    pytest.param(Pt(18), 12, 4, 72.0, id="a spacing in points is the pitch"),
])
def test_line_pitch(spacing, size, n_lines, points):
    assert C.para_height(paragraph(spacing), size, n_lines, True, True) == pytest.approx(points)


@pytest.mark.parametrize("first, last, points", [
    pytest.param(True, True, 14.4, id="only paragraph"),
    pytest.param(True, False, 14.4 + 6, id="first"),
    pytest.param(False, False, 14.4 + 12 + 6, id="middle"),
    pytest.param(False, True, 14.4 + 12, id="last"),
])
def test_space_before_the_first_and_after_the_last_is_dropped(first, last, points):
    p = paragraph(1.0, before=12, after=6)
    assert C.para_height(p, 12, 1, first, last) == pytest.approx(points)


# ---------------------------------------------------------------- font files
def test_a_hashed_file_name_is_found_by_its_name_table(fonts):
    path = fonts("Inter-UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuGKYMZg.ttf",
                 "Inter", "Regular")
    assert M.font_file("Inter", False) == path


def test_bold_prefers_bold_to_semibold(fonts):
    fonts("Inter-a1.ttf", "Inter", "SemiBold")
    bold = fonts("Inter-b2.ttf", "Inter", "Bold")
    fonts("Inter-c3.ttf", "Inter", "Bold Italic")
    assert M.font_file("Inter", True) == bold


def test_a_file_named_semibold_does_not_beat_a_hashed_bold(fonts):
    fonts("Inter-SemiBold.ttf", "Inter", "SemiBold")
    bold = fonts("Inter-x9.ttf", "Inter", "Bold")
    assert M.font_file("Inter", True) == bold


def test_file_names_rank_weights_too(fonts, tmp_path, monkeypatch):
    # SemiBold is walked first, and the names inside match nothing, so only
    # ranking the file names can pick Bold.
    for sub in ("a", "b"):
        (tmp_path / "fonts" / sub).mkdir()
    fonts("a/Inter-SemiBold.ttf", "Not The Name Inside", "Regular")
    bold = fonts("b/Inter-Bold.ttf", "Not The Name Inside", "Regular")
    monkeypatch.setattr(M, "FONT_DIRS", [str(tmp_path / "fonts" / "a"),
                                         str(tmp_path / "fonts" / "b")])
    assert M.font_file("Inter", True) == bold


def test_a_legacy_family_name_finds_a_hashed_static_instance(fonts):
    medium = fonts("Inter-x9.ttf", "Inter Medium", "Regular", ("Inter", "Medium"))
    assert M.font_file("Inter Medium", False) == medium
    assert M.font_file("Inter", False) is None


def test_a_directory_inside_another_is_walked_once(fonts, tmp_path, monkeypatch):
    fonts("Inter-x9.ttf", "Inter", "Regular")
    nested = tmp_path / "fonts" / "Supplemental"
    nested.mkdir()
    fonts("Supplemental/Mono-y1.ttf", "Mono", "Regular")
    monkeypatch.setattr(M, "FONT_DIRS", [str(tmp_path / "fonts"), str(nested)])
    paths = list(M._font_paths())
    assert len(paths) == len(set(paths)) == 2


def test_semibold_stands_in_for_bold_but_not_for_regular(fonts):
    semi = fonts("Inter-a1.ttf", "Inter SemiBold", "Regular", ("Inter", "SemiBold"))
    assert M.font_file("Inter", True) == semi
    assert M.font_file("Inter", False) is None


def test_italics_and_other_families_do_not_match(fonts):
    fonts("Inter-a1.ttf", "Inter", "Italic")
    fonts("Inter-b2.ttf", "Inter Display", "Regular")
    fonts("Inter-c3.ttf", "Inter", "Bold Italic")
    assert M.font_file("Inter", False) is None
    assert M.font_file("Inter", True) is None


def test_a_telling_file_name_is_still_enough(fonts):
    path = fonts("Inter-Regular.ttf", "Not The Name Inside", "Regular")
    assert M.font_file("Inter", False) == path


def test_missing_fonts_names_each_family_and_weight(fonts):
    fonts("Inter-a1.ttf", "Inter", "Regular")
    toks = [("lead", True, "Inter"), ("body", False, "Inter"), ("code", False, "Mono")]
    assert M.missing_fonts(toks) == {("Inter", True), ("Mono", False)}


# ---------------------------------------------------------------- overflow
def test_the_issue_repro_overflows_the_1_90_in_box(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 1.90, TEN, name="TenLines_h1.90")
    text_box(prs, 2.30, TEN, name="TenLines_h2.30")
    rep = overflow(prs)
    assert rep.errors() == [
        ("ERROR", "overflow", 1, "TenLines_h1.90 needs 2.20 in of height and has 1.90")]
    assert rep.warnings() == []


def test_wrapped_lines_are_counted(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    two = "x" * 29 + " " + "y" * 30  # 360 pt of text in a 273.6 pt line: two lines
    prs = deck()
    text_box(prs, 0.60, [two], name="two_lines")          # 0.2 in + 2 x 14.4 pt
    text_box(prs, 0.45, [two, "z"], name="three_lines")   # 0.2 in + 3 x 14.4 pt
    assert [r[3] for r in overflow(prs).errors()] == [
        "three_lines needs 0.80 in of height and has 0.45"]


def test_an_unmeasured_frame_is_a_warning_not_a_pass(fonts):
    prs = deck()
    text_box(prs, 1.90, TEN)
    text_box(prs, 1.50, TEN)
    rep = overflow(prs)
    assert rep.errors() == []
    assert rep.warnings() == [
        ("WARN", "overflow", None,
         '2 frames not measured: font "Inter" not found, on slides 1, 2')]


def test_the_missing_weight_is_named(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 3.0, TEN, bold=True)
    assert [r[3] for r in overflow(prs).warnings()] == [
        '1 frame not measured: font "Inter" bold not found, on slide 1']


def test_a_proven_overflow_is_an_error_even_with_a_paragraph_left_out(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    tb = text_box(prs, 1.00, TEN)
    tb.text_frame.paragraphs[-1].runs[0].font.name = "Mono"
    rep = overflow(prs)
    assert len(rep.errors()) == 1
    assert rep.warnings() == []


def test_a_partly_measured_frame_that_fits_is_still_reported(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    tb = text_box(prs, 3.0, TEN)
    tb.text_frame.paragraphs[-1].runs[0].font.name = "Mono"
    rep = overflow(prs)
    assert rep.errors() == []
    assert [r[3] for r in rep.warnings()] == [
        '1 frame not measured: font "Mono" not found, on slide 1']


# ---------------------------------------------------------------- orphans
def test_an_unmeasured_orphan_frame_is_a_warning_and_the_first_slide_is_skipped(fonts):
    prs = deck()
    for _ in range(3):
        text_box(prs, 3.0, TEN)
    rep = C.Report()
    C.check_orphans(prs, rep, "Inter", 0.34, M.AT_RISK_FILL, include_first=False)
    assert rep.warnings() == [
        ("WARN", "orphans", None,
         '2 frames not measured: font "Inter" not found, on slides 2, 3')]


def test_a_wrapped_orphan_is_still_reported(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.60, [ORPHANED])
    assert M.report(prs) == [(2, ORPHANED, "orphan")]


def test_an_unset_word_wrap_wraps(fonts):
    # No wrap attribute in the file means PowerPoint's default, which wraps.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.60, [ORPHANED], wrap=None)
    assert M.report(prs) == [(2, ORPHANED, "orphan")]


# ---------------------------------------------------------------- no-wrap frames
# 44 characters fill 264 pt of the 273.6 pt line, 96 percent. ORPHANED adds " LINK"
# and is 294 pt, 4.08 in: wrapped, "LINK" drops to a 24 pt last line; unwrapped, it
# runs 0.28 in past the inner edge, to 1 + 0.1 + 4.08 = 5.18 in.
FULL = "X" * 44
ORPHANED = FULL + " LINK"


def test_a_nowrap_line_is_never_an_orphan(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.40, [ORPHANED], wrap=False)
    assert M.report(prs) == []


def test_a_nearly_full_nowrap_line_is_not_at_risk(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.40, [FULL], wrap=False)
    assert M.report(prs) == []


def test_fix_leaves_a_nowrap_frame_alone(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    tb = text_box(prs, 0.40, [ORPHANED], wrap=False)
    assert M.fix(prs) == 0
    assert tb.width == Inches(4)
    assert tb.text_frame.paragraphs[0].runs[0].font.size == Pt(12)


def test_a_nowrap_line_wider_than_its_box_overflows(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, [ORPHANED], wrap=False, name="code")
    text_box(prs, 0.40, [FULL], wrap=False, name="fits")
    rep = overflow(prs)
    assert rep.errors() == [
        ("ERROR", "overflow", 1, "code needs 4.08 in of width and has 3.80")]
    assert rep.warnings() == []


def test_a_nowrap_frame_is_one_line_per_paragraph(fonts):
    # 0.2 in of insets and five 0.2 in lines. Wrapped at 0.3 in, each short
    # paragraph would still be one line, so this is not the wrap model's count.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.35, ["PERFORM %d000-STEP" % k for k in range(1, 6)], wrap=False,
             name="tall")
    assert [r[3] for r in overflow(prs).errors()] == [
        "tall needs 1.20 in of height and has 0.35"]


def test_an_unmeasured_nowrap_frame_is_a_warning(fonts):
    prs = deck()
    text_box(prs, 0.40, [ORPHANED], wrap=False)
    rep = overflow(prs)
    assert rep.errors() == []
    assert [r[3] for r in rep.warnings()] == [
        '1 frame not measured: font "Inter" not found, on slide 1']


def test_the_ink_of_a_nowrap_line_is_not_cut_at_the_frame(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    tb = text_box(prs, 0.40, [ORPHANED], wrap=False, name="code")
    nb = prs.slides[0].shapes.add_shape(1, Inches(5.1), Inches(1), Inches(1), Inches(0.4))
    nb.name = "Neighbour"
    nb.fill.solid()
    l, t, r, b = C.ink_box(tb, "Inter")
    assert (l, r) == (pytest.approx(1.1), pytest.approx(1.1 + 294 / 72.0))
    rep = C.Report()
    C.check_overlap(prs, rep, C.EPS, "Inter")
    assert [r[3] for r in rep.errors()] == ["code and Neighbour overlap by 0.08 x 0.20 in"]


# ---------------------------------------------------------------- line breaks
def test_a_line_break_is_kept_as_a_break():
    prs = deck()
    tb = text_box(prs, 0.40, ["AAA\vBBB"])
    toks = M.tokens(tb.text_frame.paragraphs[0], "Inter")
    assert [w for w, _b, _f in toks] == ["AAA", M.BREAK, "BBB"]


def test_a_line_break_starts_a_line_in_a_wrapped_frame(fonts):
    # Glued into one word, "AAABBB" is one 0.2 in line and 0.40 in fits.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.45, ["AAA\vBBB"], name="broken")
    assert [r[3] for r in overflow(prs).errors()] == [
        "broken needs 0.60 in of height and has 0.45"]


def test_a_line_break_starts_a_line_in_a_nowrap_frame(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.45, ["AAA\vBBB"], wrap=False, name="broken")
    assert [r[3] for r in overflow(prs).errors()] == [
        "broken needs 0.60 in of height and has 0.45"]


def test_a_short_line_after_a_break_is_not_an_orphan(fonts):
    # The break put "end" there on purpose. Wrapping did not.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.80, ["X" * 30 + "\vend"])
    assert M.report(prs) == []


def test_an_orphan_before_a_break_is_still_one(fonts):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 0.40, ["title"])
    text_box(prs, 0.80, [ORPHANED + "\vend"])
    assert [r[2] for r in M.report(prs)] == ["orphan"]


# ---------------------------------------------------------------- the command
@pytest.fixture
def run_main(tmp_path, monkeypatch, capsys):
    def run(prs, *flags):
        path = str(tmp_path / "deck.pptx")
        prs.save(path)
        monkeypatch.setattr(sys, "argv", ["check_layout.py", path, "--margins", "0.17,9.83,5.31",
                                          "--only", "overflow"] + list(flags))
        code = C.main()
        return code, capsys.readouterr().out
    return run


def test_a_deck_it_could_not_measure_does_not_print_clean(fonts, run_main):
    prs = deck()
    text_box(prs, 1.50, TEN)
    code, out = run_main(prs)
    assert code == 0
    assert 'WARN  overflow  deck      1 frame not measured: font "Inter" not found' in out
    assert "0 error, 1 warning" in out
    code, _out = run_main(prs, "--strict")
    assert code == 1


@pytest.mark.parametrize("fix", [False, True], ids=["report", "fix"])
def test_fix_orphans_does_not_print_clean_when_it_could_not_measure(fonts, tmp_path,
                                                                   monkeypatch, capsys, fix):
    fonts("Inter-Regular.ttf", "Inter", "Regular")
    prs = deck()
    for _ in range(2):
        text_box(prs, 3.0, TEN, family="Mono")
    path = str(tmp_path / "deck.pptx")
    prs.save(path)
    monkeypatch.setattr(sys, "argv", ["fix_orphans.py", path] + (["--fix"] if fix else []))
    code = M.main()
    out = capsys.readouterr().out
    assert code == 2
    assert "no orphans" not in out
    assert 'not measured: 10 paragraphs, font "Mono" not found, on slide 2' in out
    assert out.rstrip().endswith("0 orphan, 0 at risk, 10 not measured")


def test_fix_orphans_counts_a_paragraph_once_whatever_it_lacks(fonts, tmp_path,
                                                             monkeypatch, capsys):
    fonts("Inter-Regular.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 3.0, ["title"])
    tb = text_box(prs, 3.0, ["body text"], family="Mono")
    lead = tb.text_frame.paragraphs[0].runs[0]
    lead.text, lead.font.bold = "Lead ", True
    rest = tb.text_frame.paragraphs[0].add_run()
    rest.text, rest.font.name, rest.font.size = "and the rest", "Mono", Pt(12)
    path = str(tmp_path / "deck.pptx")
    prs.save(path)
    monkeypatch.setattr(sys, "argv", ["fix_orphans.py", path])
    assert M.main() == 2
    out = capsys.readouterr().out
    assert 'not measured: 1 paragraph, font "Mono" bold not found, on slide 2' in out
    assert 'not measured: 1 paragraph, font "Mono" not found, on slide 2' in out
    assert out.rstrip().endswith("0 orphan, 0 at risk, 1 not measured")


def test_the_issue_repro_fails_the_command(fonts, run_main):
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 1.90, TEN, name="TenLines_h1.90")
    code, out = run_main(prs)
    assert code == 1
    assert "ERROR overflow  slide 1   TenLines_h1.90 needs 2.20 in" in out


# ---------------------------------------------------------------- real LibreOffice
def real_font(family):
    """The machine's own file for a family, looked up with the real font path."""
    M._file_cache.clear()
    M._name_table = None
    return M.font_file(family, False)


@pytest.mark.libreoffice
def test_a_nowrap_frame_renders_as_measured(tmp_path):
    """One unwrapped code line in a 4 in box, and a frame of three paragraphs
    with a line break in the middle one. LibreOffice must draw the code line on
    one line at the measured width, past the frame, and the other frame on the
    four lines the model counts."""
    import subprocess

    import pymupdf
    import render_real as R

    soffice = R.find_soffice()
    if soffice is None:
        pytest.skip("LibreOffice is not installed")
    if real_font("Inter") is None:
        pytest.skip("Inter is not installed, so LibreOffice would draw another font")

    code = "EXEC CICS LINK PROGRAM('LGICUS01') COMMAREA(CA) RESP(WS-RESP)"
    prs = deck()
    one = text_box(prs, 0.40, [code], wrap=False, name="code")
    text_box(prs, 1.00, ["MOVE A TO B", "PERFORM 1000-STEP\vTHRU 1000-EXIT", "GOBACK"],
             wrap=False, name="tall")
    path = tmp_path / "nowrap.pptx"
    prs.save(str(path))
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir",
                    str(tmp_path), str(path)], capture_output=True, check=True)
    doc = pymupdf.open(str(tmp_path / "nowrap.pdf"))

    def drawn(page):
        """[(text, bbox)] for each line of text on a page, top to bottom."""
        return sorted(((("".join(s["text"] for s in ln["spans"])).strip(), ln["bbox"])
                       for blk in page.get_text("dict")["blocks"]
                       for ln in blk.get("lines", [])
                       if "".join(s["text"] for s in ln["spans"]).strip()),
                      key=lambda row: row[1][1])

    # A LibreOffice that substitutes another face would make the widths below
    # compare two different fonts.
    used = [f[3] for f in doc[0].get_fonts()]
    assert any("Inter" in name for name in used), "LibreOffice drew %s" % used

    code_lines = drawn(doc[0])
    assert [t for t, _b in code_lines] == [code]
    p = one.text_frame.paragraphs[0]
    measured = max(M.lines(M.tokens(p, "Inter"), 12, M.para_width(one, p), wrap=False))
    x0, _y0, x1, _y1 = code_lines[0][1]
    assert x1 - x0 == pytest.approx(measured, rel=0.03)
    assert x1 / 72.0 > 5.0                      # past the frame's right edge

    assert [t for t, _b in drawn(doc[1])] == [
        "MOVE A TO B", "PERFORM 1000-STEP", "THRU 1000-EXIT", "GOBACK"]
    # 0.2 in of insets and four 0.2 in lines fill the 1.00 in frame exactly.
    assert [r[3] for r in overflow(prs).errors()] == [
        "code needs %.2f in of width and has 3.80" % (measured / 72.0)]
