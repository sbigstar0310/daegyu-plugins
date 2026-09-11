#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find and fix dangling last lines.

A paragraph whose last line holds one or two words looks broken, and a presenter
notices it before anything else on the slide. python-pptx cannot tell you where
the lines break, so this measures them: it loads the deck's real font file with
PIL and wraps each paragraph the way the renderer will.

    python3 scripts/fix_orphans.py deck.pptx                  # report, change nothing
    python3 scripts/fix_orphans.py deck.pptx --fix            # rewrite deck.pptx
    python3 scripts/fix_orphans.py deck.pptx --fix -o out.pptx

The fix is two passes. First shrink the paragraph's font by up to 12 percent, just
enough that the text needs one line fewer. If that is not enough, narrow the text
box by up to 16 percent so the last line pulls a word up. Both are small enough to
stay invisible next to a neighbouring block.

Everything is measured at the stated width and again at plus and minus 3 percent,
because PowerPoint's metrics differ a little from PIL's. A paragraph that is one
wrap away from breaking is reported too: those are the ones that look fine in
LibreOffice and break on the presenter's machine.

The measuring helpers are importable. check_layout.py uses them.
"""
import argparse
import os
import re
import sys

from PIL import ImageFont
from pptx import Presentation
from pptx.util import Pt

# PIL quantises to integer pixels, so measure at 4x and divide. Without this a
# 10.7 pt line is measured as 11 pt and every width is a percent too wide.
SCALE = 4

FONT_DIRS = [
    "~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "~/.local/share/fonts", "~/.fonts", "/usr/share/fonts", "/usr/local/share/fonts",
    "/Applications/LibreOffice.app/Contents/Resources/fonts/truetype",
]
WEIGHT_NAMES = {False: ["Regular", "Book", "Roman", ""], True: ["Bold", "Semibold", "SemiBold"]}

_font_cache = {}
_file_cache = {}


def font_file(family, bold):
    """The file on disk for one family and weight, or None."""
    key = (family, bool(bold))
    if key in _file_cache:
        return _file_cache[key]
    flat = family.replace(" ", "").lower()
    found = None
    for d in FONT_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if not f.lower().endswith((".otf", ".ttf", ".ttc")):
                    continue
                stem = os.path.splitext(f)[0].replace(" ", "").replace("-", "").lower()
                if not stem.startswith(flat):
                    continue
                tail = stem[len(flat):]
                for want in WEIGHT_NAMES[bool(bold)]:
                    w = want.replace(" ", "").lower()
                    if tail == w or (w and tail.startswith(w)):
                        # "Bold" must not match "BoldItalic", and regular must not
                        # match "Light" or "Italic".
                        if "italic" in tail or "oblique" in tail:
                            continue
                        if not bold and tail not in ("", "regular", "book", "roman"):
                            continue
                        found = os.path.join(root, f)
                        break
                if found:
                    break
            if found:
                break
        if found:
            break
    _file_cache[key] = found
    return found


def font(family, bold, size_pt):
    key = (family, bool(bold), round(size_pt * SCALE))
    if key not in _font_cache:
        path = font_file(family, bold)
        _font_cache[key] = (ImageFont.truetype(path, int(round(size_pt * SCALE)))
                            if path else None)
    return _font_cache[key]


def run_family(run, default):
    return run.font.name or default


def tokens(p, default_family):
    """[(word, bold, family)] for one paragraph. A word takes the weight and family
    of the run it starts in, which is right for the bold lead-in pattern."""
    full = ""
    spans = []
    for r in p.runs:
        spans.append((len(full), len(full) + len(r.text), bool(r.font.bold),
                      run_family(r, default_family)))
        full += r.text
    out = []
    for m in re.finditer(r"\S+", full):
        hit = next((s for s in spans if s[0] <= m.start() < s[1]), None)
        out.append((m.group(), hit[2] if hit else False,
                    hit[3] if hit else default_family))
    return out


def lines(toks, size_pt, width_pt):
    """Greedy word wrap. Returns the width in points of each resulting line, or
    None if the font file is missing, in which case nothing can be measured."""
    out = []
    cur = 0.0
    n = 0
    for word, bold, family in toks:
        f = font(family, bold, size_pt)
        if f is None:
            return None
        ww = f.getlength(word) / SCALE
        sp = f.getlength(" ") / SCALE
        cand = cur + (sp if n else 0.0) + ww
        if cand <= width_pt or n == 0:
            cur = cand
            n += 1
        else:
            out.append(cur)
            cur = ww
            n = 1
    if n:
        out.append(cur)
    return out


def para_width(shape, p):
    """Usable width of one paragraph in points: the box minus its insets and minus
    the paragraph's own left margin, which a bulleted paragraph always has."""
    tf = shape.text_frame
    inset = ((tf.margin_left or 0) + (tf.margin_right or 0)) / 12700.0
    pPr = p._p.pPr
    marl = int(pPr.get("marL", 0)) / 12700.0 if pPr is not None else 0.0
    return shape.width / 12700.0 - inset - marl


def orphan(toks, size_pt, width_pt, min_ratio):
    """(is_orphan, line_count_at_nominal_width). Checked at the nominal width and
    at plus and minus 3 percent, so a paragraph that only breaks in PowerPoint is
    still caught."""
    bad = False
    n_at = 0
    for k in (1.0, 0.97, 1.03):
        ls = lines(toks, size_pt, width_pt * k)
        if ls is None:
            return False, 0
        if k == 1.0:
            n_at = len(ls)
        if len(ls) >= 2 and ls[-1] < min_ratio * width_pt:
            bad = True
    return bad, n_at


AT_RISK_FILL = 0.95  # a single line this full is one glyph from wrapping


def fill_ratio(toks, size_pt, width_pt):
    """How full the widest line is. Near 1.0 the paragraph is one glyph from
    wrapping on a machine whose metrics round the other way."""
    ls = lines(toks, size_pt, width_pt)
    if not ls:
        return 0.0
    return max(ls) / width_pt if width_pt else 0.0


def _paragraphs(prs, default_family, skip_first):
    for si, slide in enumerate(prs.slides):
        if skip_first and si == 0:
            continue
        for shape in slide.shapes:
            if not shape.has_text_frame or shape.shape_type == 19:  # 19 = table
                continue
            for p in shape.text_frame.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if toks:
                    yield si + 1, shape, p, toks


def report(prs, default_family="Inter", min_ratio=0.34, skip_first=True,
           at_risk_fill=AT_RISK_FILL):
    """[(slide_number, text, kind)] for every paragraph that needs attention.
    kind is "orphan" for a short last line that is already there, and "at risk"
    for one that appears as soon as the metrics shift slightly."""
    out = []
    for n, shape, p, toks in _paragraphs(prs, default_family, skip_first):
        size = p.runs[0].font.size.pt
        pw = para_width(shape, p)
        bad, count = orphan(toks, size, pw, min_ratio)
        text = " ".join(w for w, _b, _f in toks)
        if bad:
            out.append((n, text, "orphan" if count >= 2 else "at risk"))
        elif count == 1 and fill_ratio(toks, size, pw) > at_risk_fill:
            out.append((n, text, "at risk"))
    return out


def fix(prs, default_family="Inter", min_ratio=0.34, min_scale=0.84,
        min_font_scale=0.88, skip_first=True):
    """Returns how many paragraphs or boxes were changed."""
    fixed = 0
    for si, slide in enumerate(prs.slides):
        if skip_first and si == 0:
            continue
        for shape in slide.shapes:
            if not shape.has_text_frame or shape.shape_type == 19:
                continue
            tf = shape.text_frame

            # Pass 1: shrink the font of the offending paragraph until the short
            # last line disappears, or until the text needs one line fewer.
            for p in tf.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if not toks:
                    continue
                size = p.runs[0].font.size.pt
                pw = para_width(shape, p)
                bad, n0 = orphan(toks, size, pw, min_ratio)
                if not bad:
                    continue
                sz = size
                while sz > size * min_font_scale:
                    sz -= 0.5
                    bad2, n2 = orphan(toks, sz, pw, min_ratio)
                    if not bad2 or n2 < n0:
                        for r in p.runs:
                            r.font.size = Pt(sz)
                        fixed += 1
                        break

            # Pass 2: if a paragraph is still orphaned, narrow the whole box. A
            # narrower box pulls a word down onto the last line.
            paras = []
            for p in tf.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if toks:
                    paras.append((toks, p.runs[0].font.size.pt, para_width(shape, p)))
            if not paras:
                continue

            def count_orphans(scale):
                bad = total = 0
                for toks, size, pw in paras:
                    narrower = pw - (1 - scale) * shape.width / 12700.0
                    b, n = orphan(toks, size, narrower, min_ratio)
                    bad += int(b)
                    total += n
                return bad, total

            bad0, tot0 = count_orphans(1.0)
            if bad0 == 0:
                continue
            scale = 1.0
            while scale > min_scale:
                scale -= 0.02
                bad, tot = count_orphans(scale)
                if bad == 0 and tot <= tot0 + 1:
                    shape.width = int(shape.width * scale)
                    fixed += 1
                    break
    return fixed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--fix", action="store_true", help="rewrite the deck instead of only reporting")
    ap.add_argument("-o", "--out", help="write the fixed deck here instead of in place")
    ap.add_argument("--font", default="Inter", help="family to measure with when a run does not name one")
    ap.add_argument("--min-ratio", type=float, default=0.34,
                    help="a last line narrower than this share of the box is an orphan")
    ap.add_argument("--min-scale", type=float, default=0.84, help="narrow a box no further than this")
    ap.add_argument("--min-font-scale", type=float, default=0.88, help="shrink a font no further than this")
    ap.add_argument("--fill-risk", type=float, default=AT_RISK_FILL,
                    help="a single line filling more than this share of its box is at risk")
    ap.add_argument("--include-first", action="store_true",
                    help="check the title slide too, which is usually set by hand")
    a = ap.parse_args()

    if font_file(a.font, False) is None:
        sys.stderr.write(
            "cannot find a file for font %r, so nothing can be measured.\n"
            "Install it, or pass --font with the family the deck actually uses.\n" % a.font)
        return 2

    prs = Presentation(a.deck)
    skip_first = not a.include_first

    if a.fix:
        n = fix(prs, a.font, a.min_ratio, a.min_scale, a.min_font_scale, skip_first)
        out = a.out or a.deck
        prs.save(out)
        print("fixed %d paragraphs, wrote %s" % (n, out))
        prs = Presentation(out)

    rows = report(prs, a.font, a.min_ratio, skip_first, a.fill_risk)
    if not rows:
        print("no orphans, no paragraphs at risk")
        return 0
    for n, text, kind in rows:
        print("  slide %-3d %-8s %s" % (n, kind, text[:70]))
    n_orphan = sum(1 for r in rows if r[2] == "orphan")
    print("%d orphan, %d at risk" % (n_orphan, len(rows) - n_orphan))
    return 1 if n_orphan else 0


if __name__ == "__main__":
    sys.exit(main())
