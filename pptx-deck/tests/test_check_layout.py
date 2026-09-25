# -*- coding: utf-8 -*-
"""Tests for the height and font arithmetic in check_layout.py and fix_orphans.py.

    uv run --directory pptx-deck pytest

Every expected number can be worked by hand. The test fonts make each character
half an em wide, so at 12 pt a character is 6 pt, "line 10 of ten" is 84 pt, and
the 4 in box with 0.1 in insets holds 273.6 pt per line.
"""
import sys

import pytest
from lxml import etree
from pptx import Presentation
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn
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
    # A bold with a Regular to stand in for it is measured, so it is not missing.
    fonts("Inter-a1.ttf", "Inter", "Regular")
    toks = [("lead", True, "Inter"), ("body", False, "Inter"), ("code", False, "Mono"),
            ("bold", True, "Mono")]
    assert M.missing_fonts(toks) == {("Mono", False), ("Mono", True)}


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
    # With no Regular to stand in, a bold frame cannot be measured at all.
    fonts("Mono-hash.ttf", "Mono", "Regular")
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


# ---------------------------------------------------------------- bold with no Bold file
# LibreOffice draws a bold it has no file for by stroking the Regular glyphs, which
# leaves every advance as it was. So the Regular file measures that bold exactly,
# and for a fixed-pitch family it matches a real Bold too. The test font "Sans"
# is proportional: i and W differ from the half-em rest.
PROPORTIONAL = {"i": 250, "W": 900, "M": 800, ".": 250}
SYNTH = ('%d frame%s measured with "Sans" Regular for bold, on slide%s %s '
         '(LibreOffice synthesises it; a real Bold can be up to ~7%% wider)')


def test_bold_without_a_bold_file_is_measured_with_regular(fonts):
    regular = fonts("Mono-hash.ttf", "Mono", "Regular")
    assert M.font_file("Mono", True) is None
    assert M.resolve("Mono", True) == (regular, True)
    assert M.resolve("Mono", False) == (regular, False)
    prs = deck()
    text_box(prs, 1.90, TEN, family="Mono", bold=True, name="bold_mono")
    rep = overflow(prs)
    assert [r[3] for r in rep.errors()] == ["bold_mono needs 2.20 in of height and has 1.90"]
    assert rep.warnings() == []


def test_a_bold_lead_in_no_longer_drops_the_frame(fonts):
    fonts("Mono-hash.ttf", "Mono", "Regular")
    prs = deck()
    tb = text_box(prs, 1.90, TEN, family="Mono", name="lead_in")
    lead = tb.text_frame.paragraphs[0].runs[0]
    lead.font.bold = True
    rest = tb.text_frame.paragraphs[0].add_run()
    rest.text, rest.font.name, rest.font.size = " and the rest", "Mono", Pt(12)
    rep = overflow(prs)
    assert [r[3] for r in rep.errors()] == ["lead_in needs 2.20 in of height and has 1.90"]
    assert rep.warnings() == []


def test_a_real_bold_file_is_still_preferred(fonts):
    fonts("Mono-a1.ttf", "Mono", "Regular")
    bold = fonts("Mono-b2.ttf", "Mono", "Bold", widths={"x": 625})
    assert M.resolve("Mono", True) == (bold, False)
    # 12 pt at 0.625 em is 7.5 pt a glyph: two of them are 15 pt.
    assert M.lines([("xx", True, "Mono")], 12, 1000) == [15.0]
    assert M.lines([("xx", False, "Mono")], 12, 1000) == [12.0]
    assert M.synthesised_fonts([("xx", True, "Mono")]) == set()


def test_is_fixed_pitch(fonts):
    fonts("Mono-hash.ttf", "Mono", "Regular")
    fonts("Sans-hash.ttf", "Sans", "Regular", widths=PROPORTIONAL)
    assert M.is_fixed_pitch("Mono") is True
    assert M.is_fixed_pitch("Sans") is False


def test_proportional_bold_is_measured_and_flagged(fonts):
    fonts("Sans-hash.ttf", "Sans", "Regular", widths=PROPORTIONAL)
    prs = deck()
    text_box(prs, 1.90, TEN, family="Sans", bold=True, name="bold_sans")
    text_box(prs, 3.00, TEN, family="Sans", bold=True, name="fits")
    text_box(prs, 3.00, TEN, family="Sans", name="regular_only")
    rep = overflow(prs)
    assert [r[3] for r in rep.errors()] == ["bold_sans needs 2.20 in of height and has 1.90"]
    assert rep.warnings() == [("WARN", "overflow", None, SYNTH % (2, "s", "s", "1, 2"))]
    assert M.synthesised_fonts([("x", True, "Sans"), ("\v", True, "Sans")]) == {"Sans"}


def test_a_proportional_bold_in_the_orphan_check_is_flagged_too(fonts):
    fonts("Sans-hash.ttf", "Sans", "Regular", widths=PROPORTIONAL)
    prs = deck()
    for _ in range(2):
        text_box(prs, 3.0, TEN, family="Sans", bold=True)
    rep = C.Report()
    C.check_orphans(prs, rep, "Sans", 0.34, M.AT_RISK_FILL, include_first=False)
    assert rep.warnings() == [("WARN", "orphans", None, SYNTH % (1, "", "", "2"))]


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


@pytest.mark.parametrize("family, widths, note", [
    ("Mono", None, False), ("Sans", PROPORTIONAL, True)], ids=["fixed-pitch", "proportional"])
def test_fix_orphans_measures_a_bold_it_has_no_file_for(fonts, tmp_path, monkeypatch, capsys,
                                                       family, widths, note):
    fonts("Face-hash.ttf", family, "Regular", widths=widths)
    prs = deck()
    for _ in range(2):
        text_box(prs, 3.0, ["short bold line"], family=family, bold=True)
    path = str(tmp_path / "deck.pptx")
    prs.save(path)
    monkeypatch.setattr(sys, "argv", ["fix_orphans.py", path, "--font", family])
    assert M.main() == 0
    out = capsys.readouterr().out
    assert "not measured" not in out
    assert ('measured with "%s" Regular for bold' % family in out) is note
    assert "no orphans, no paragraphs at risk" in out


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


# ---------------------------------------------------------------- scale
def sized_slide(prs, *boxes):
    """A slide with a 0.6 in text box at each (top, sizes), one paragraph per size."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    for top, sizes in boxes:
        tf = slide.shapes.add_textbox(Inches(1), Inches(top), Inches(4), Inches(0.6)).text_frame
        for k, pt in enumerate(sizes):
            r = (tf.paragraphs[0] if k == 0 else tf.add_paragraph()).add_run()
            r.text, r.font.size = "at %s" % pt, Pt(pt)
    return slide


FOUR = [14, 12, 10, 9]


def test_a_size_off_the_scale_is_warned_and_a_quarter_point_is_not():
    prs = deck()
    sized_slide(prs, (1.0, [22, 12, 12.25, 11.5, 11.5]))
    scale = {"title": (22, "semibold", "FFFFFF"), "body": 12, "secondary": 10, "caption": 9}
    rep = C.Report()
    assert C.check_scale(prs, rep, scale) == {1: {22.0, 12.0, 12.25, 11.5}}
    assert rep.warnings() == [
        ("WARN", "scale", 1, "2 runs at 11.5 pt, not a step of the type scale, such as 'at 11.5'")]


def test_the_title_band_and_section_slides_count_unless_the_tokens_mark_them():
    prs = deck()
    sized_slide(prs, (2.0, [36]))
    sized_slide(prs, (0.2, [22]), (1.4, [12]))
    rep = C.Report()
    C.check_scale(prs, rep, FOUR)
    assert [(r[2], r[3][:13]) for r in rep.warnings()] == [(1, "1 run at 36.0"), (2, "1 run at 22.0")]
    rep = C.Report()
    assert C.check_scale(prs, rep, FOUR, skip_slides=(1,), skip_above=0.9) == {2: {12.0}}
    assert rep.warnings() == []


@pytest.mark.parametrize("scale, warned", [
    pytest.param({"title": (22, "bold", "FFFFFF"), "body": 12, "caption": 9}, True, id="three roles"),
    pytest.param([12, 12, 10, 9], True, id="a repeated size is one level"),
    pytest.param(FOUR, False, id="four is enough"),
])
def test_a_declared_scale_of_fewer_than_four_levels_is_warned(scale, warned):
    prs = deck()
    sized_slide(prs, (1.0, [12]))
    rep = C.Report()
    C.check_scale(prs, rep, scale)
    assert rep.warnings() == ([] if not warned else [
        ("WARN", "scale", None,
         "TYPE_SCALE declares 3 levels, and a scale the audience can tell apart needs 4")])


def test_the_command_reads_type_scale_even_with_margins_given(run_main, tmp_path):
    prs = deck()
    sized_slide(prs, (0.2, [22]), (1.4, [12, 11.5]))
    scaled = tmp_path / "tokens_scaled.py"
    scaled.write_text("TYPE_SCALE = [22, 14, 12, 9]\n")
    code, out = run_main(prs, "--tokens", str(scaled), "--only", "scale")
    assert code == 0
    assert "scale    22.0, 14.0, 12.0, 9.0  (TYPE_SCALE)\n         slide 1   22.0, 12.0, 11.5\n" in out
    assert "WARN  scale     slide 1   1 run at 11.5 pt" in out
    bare = tmp_path / "tokens_bare.py"
    bare.write_text("ML = 0.5\n")
    code, out = run_main(prs, "--tokens", str(bare), "--only", "scale")
    assert "scale    not checked: tokens_bare.py has no TYPE_SCALE" in out
    assert "0 error, 0 warning" in out


# ---------------------------------------------------------------- portable
HAN = u"\ud55c\uad6d\uc5b4"


def portable(prs, target=None):
    rep = C.Report()
    C.check_portable(prs, rep, "Inter", target)
    return [r[3] for r in rep.warnings()]


def set_ea(run, typeface):
    etree.SubElement(run._r.get_or_add_rPr(), qn("a:ea"), typeface=typeface)


def mark(run):
    h = etree.Element(qn("a:highlight"))
    etree.SubElement(h, qn("a:srgbClr"), val="E6E6E6")
    run._r.get_or_add_rPr().insert(0, h)


def two_runs(tb, second_family, both_marked=True):
    p = tb.text_frame.paragraphs[0]
    extra = p.add_run()
    extra.text, extra.font.size, extra.font.name = " more", Pt(12), second_family
    mark(p.runs[0])
    if both_marked:
        mark(extra)


def hangul(latin, ea=None):
    def edit(tb):
        r = tb.text_frame.paragraphs[0].runs[0]
        r.text, r.font.name = HAN, latin
        if ea:
            set_ea(r, ea)
    return edit


def test_the_test_frame_is_portable():
    prs = deck()
    text_box(prs, 3.0, TEN)
    assert portable(prs) == []


@pytest.mark.parametrize("edit, expected", [
    pytest.param(lambda tb: setattr(tb.text_frame, "auto_size", MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT),
                 "box: spAutoFit, and each app fits text its own way. Use noAutofit", id="spAutoFit"),
    pytest.param(lambda tb: setattr(tb.text_frame, "auto_size", MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE),
                 "box: normAutofit, and each app fits text its own way. Use noAutofit",
                 id="normAutofit"),
    pytest.param(lambda tb: setattr(tb.text_frame.paragraphs[0], "line_spacing", Pt(18)),
                 "box: line spacing in points, which Google Slides cannot store", id="spcPts"),
    pytest.param(hangul("Inter"), "box: Hangul in Inter, not a font known to carry it",
                 id="hangul in a latin font"),
    pytest.param(hangul("Noto Sans KR", "Malgun Gothic"),
                 "box: Hangul in a run whose latin Noto Sans KR and ea Malgun Gothic differ",
                 id="hangul with two fonts"),
    pytest.param(hangul("Noto Sans KR", "Noto Sans KR"), None, id="hangul in one CJK font"),
    pytest.param(lambda tb: two_runs(tb, "Mono"),
                 "box: one highlight spans runs in different fonts", id="highlight across fonts"),
    pytest.param(lambda tb: two_runs(tb, "Inter"), None, id="highlight in one font"),
    pytest.param(lambda tb: two_runs(tb, "Mono", both_marked=False), None,
                 id="highlight ends where the font changes"),
])
def test_each_portable_flag(edit, expected):
    prs = deck()
    edit(text_box(prs, 3.0, TEN))
    assert portable(prs) == ([] if expected is None else [expected])


@pytest.mark.parametrize("top, height, name, flagged", [
    pytest.param(1.30, 0.20, "band", True, id="behind the middle line"),
    pytest.param(1.00, 1.00, "band", False, id="behind every line"),
    pytest.param(1.30, 0.20, "allow: a marker on line two", False, id="allowed"),
])
def test_a_filled_shape_over_some_lines_is_flagged(fonts, top, height, name, flagged):
    # Three lines at 14.4 pt from y 1.1: the text runs from 1.10 to 1.70 in.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 1.0, TEN[:3])
    band = prs.slides[0].shapes.add_shape(1, Inches(1), Inches(top), Inches(4), Inches(height))
    band.name = name
    assert portable(prs) == (["band: covers only some lines of box, by a line pitch other apps "
                              "do not keep"] if flagged else [])


@pytest.mark.parametrize("family, flagged", [
    pytest.param("Inter", False, id="a Google font"),
    pytest.param("Arial", False, id="a web font Slides has"),
    pytest.param("Calibri", True, id="drawn in Arial"),
])
def test_google_slides_wants_google_fonts(family, flagged):
    prs = deck()
    text_box(prs, 3.0, TEN, family=family)
    assert portable(prs) == []
    assert portable(prs, "google-slides") == (
        ["box: %s is not a Google Fonts family, so Slides draws it in Arial" % family]
        if flagged else [])


@pytest.mark.parametrize("text, wrap, percent", [
    pytest.param("x" * 40, True, None, id="88 percent"),
    pytest.param("x" * 45, True, 99, id="99 percent"),
    pytest.param("x" * 30 + " " + "x" * 20, True, None, id="wraps to 66 percent"),
    pytest.param("x" * 30 + " " + "x" * 20, False, 112, id="never wraps, so 112 percent"),
])
def test_a_line_over_95_percent_of_its_frame_is_flagged(fonts, text, wrap, percent):
    # 273.6 pt inside the frame, 6 pt a character.
    fonts("Inter-hash.ttf", "Inter", "Regular")
    prs = deck()
    text_box(prs, 3.0, [text]).text_frame.word_wrap = wrap
    assert portable(prs) == (["box: a line fills %d percent of its frame, and another app may "
                              "wrap it" % percent] if percent else [])


@pytest.mark.parametrize("target, runs", [
    pytest.param("google-slides", True, id="on for google slides"),
    pytest.param("powerpoint", True, id="on for powerpoint"),
    pytest.param("pdf", False, id="off for a pdf talk"),
])
def test_a_target_in_the_tokens_turns_portable_on(run_main, tmp_path, target, runs):
    prs = deck()
    tb = text_box(prs, 3.0, TEN)
    tb.text_frame.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
    tokens = tmp_path / ("tokens_%s.py" % target.replace("-", "_"))
    tokens.write_text('TARGET = "%s"\n' % target)
    _code, out = run_main(prs, "--tokens", str(tokens), "--only", "portable")
    assert ("portable checked for %s" % target in out) == runs
    assert ("WARN  portable  slide 1   box: spAutoFit" in out) == runs
    _code, out = run_main(prs, "--portable", "--only", "portable")
    assert "portable checked for any app" in out
