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

Exit code 1 means an orphan is left. 2 means something could not be measured: the
--font has no file, or a paragraph asks for a font that has none. A paragraph that
was not measured is listed, never counted as clean.

Text inside a group or a table cell is checked like any other: text_frames()
finds every place text lives and says where it is drawn. A cell's font is shrunk,
never its column, which would change every cell under it.

The measuring helpers are importable. check_layout.py uses them.
"""
import argparse
import os
import re
import sys

from PIL import ImageFont
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.shapes.group import GroupShape
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
_name_table = None


def _font_paths():
    seen = set()
    for d in FONT_DIRS:
        d = os.path.expanduser(d)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                path = os.path.join(root, f)
                # A listed directory can sit inside another one, as Supplemental
                # does inside /System/Library/Fonts.
                if f.lower().endswith((".otf", ".ttf", ".ttc")) and path not in seen:
                    seen.add(path)
                    yield path


def _flat(name):
    return re.sub(r"[\s_-]", "", name or "").lower()


def _by_file_name(family, bold):
    """(rank, path) for the best file whose name gives the family and weight, or
    None. rank is the weight's place in WEIGHT_NAMES, so Bold beats SemiBold."""
    flat = _flat(family)
    wants = [_flat(w) for w in WEIGHT_NAMES[bool(bold)]]
    best = None
    for path in _font_paths():
        stem = _flat(os.path.splitext(os.path.basename(path))[0])
        if not stem.startswith(flat):
            continue
        tail = stem[len(flat):]
        # "Bold" must not match "BoldItalic", and regular must not match "Light"
        # or "Italic".
        if "italic" in tail or "oblique" in tail:
            continue
        if not bold and tail not in ("", "regular", "book", "roman"):
            continue
        for rank, w in enumerate(wants):
            if tail == w or (w and tail.startswith(w)):
                if best is None or rank < best[0]:
                    best = (rank, path)
                break
    return best


def _by_name_table(family, bold):
    """(rank, path) matched on the family and style the font file declares, which
    is what a renderer matches on. Opening every font costs a fraction of a second,
    so the table is read once per process."""
    global _name_table
    if _name_table is None:
        _name_table = []
        for path in _font_paths():
            try:
                fam, style = ImageFont.truetype(path, 10).getname()
            except (OSError, ValueError):
                continue
            fam, style = _flat(fam), _flat(style)
            _name_table.append((path, fam, style))
            # FreeType reports the typographic family, "Inter" and "Medium". A deck
            # saved on Windows names the legacy one, "Inter Medium" and "Regular".
            if style not in ("regular", "bold", "italic", "bolditalic") \
                    and "italic" not in style and "oblique" not in style:
                _name_table.append((path, fam + style, "regular"))
    wants = [_flat(w) for w in WEIGHT_NAMES[bool(bold)]]
    best = None
    for path, fam, style in _name_table:
        if fam == _flat(family) and style in wants:
            rank = wants.index(style)
            if best is None or rank < best[0]:
                best = (rank, path)
    return best


def font_file(family, bold):
    """The file on disk for one family and weight, or None. File names are tried
    first. The name table inside each font is read when they find nothing, or only
    a lesser weight: a file whose name says nothing, like the hashed names the
    Google Fonts CDN serves, is found by the family and style inside it."""
    key = (family, bool(bold))
    if key not in _file_cache:
        best = _by_file_name(family, bold)
        if best is None or best[0] > 0:
            named = _by_name_table(family, bold)
            if named is not None and (best is None or named[0] < best[0]):
                best = named
        _file_cache[key] = best[1] if best else None
    return _file_cache[key]


def resolve(family, bold):
    """(path, synthesised). A bold with no Bold file is measured with the Regular:
    LibreOffice draws that bold by stroking the Regular glyphs, which leaves every
    advance as it was, so the Regular file is exact against its render. Against a
    machine that has the real Bold it is exact only for a fixed-pitch family."""
    path = font_file(family, bold)
    if path is not None or not bold:
        return path, False
    path = font_file(family, False)
    return path, path is not None


# Glyphs whose widths differ in any proportional font.
PITCH_PROBE = "iWMl."
SYNTHESISED = "LibreOffice synthesises it; a real Bold can be up to ~7% wider"


def is_fixed_pitch(family):
    """True when every probe glyph of the Regular has the same advance."""
    f = font(family, False, 12)
    return f is not None and len({f.getlength(c) for c in PITCH_PROBE}) == 1


def missing_fonts(toks):
    """{(family, bold)} a paragraph needs and has no file for. lines() returns None
    for such a paragraph, and a caller that skips it must say so."""
    return {(family, bool(bold)) for w, bold, family in toks
            if w != BREAK and resolve(family, bold)[0] is None}


def synthesised_fonts(toks):
    """{family} whose bold a paragraph measures with the Regular, for a family where
    that is only an approximation: a proportional one. A caller reports these."""
    return {family for w, bold, family in toks
            if w != BREAK and bold and resolve(family, True)[1]
            and not is_fixed_pitch(family)}


def font(family, bold, size_pt):
    key = (family, bool(bold), round(size_pt * SCALE))
    if key not in _font_cache:
        path = resolve(family, bold)[0]
        _font_cache[key] = (ImageFont.truetype(path, int(round(size_pt * SCALE)))
                            if path else None)
    return _font_cache[key]


def run_family(run, default):
    return run.font.name or default


# A line break inside a paragraph (<a:br/>, Shift+Enter). tokens() puts it in the
# word list, and lines() always ends the line there.
BREAK = "\v"


class Frame(object):
    """One place text lives, placed on the slide. left, top, width and height are
    EMU in slide coordinates, as a top-level shape's are; a group's child is
    mapped through each group it sits in. The group scales the box and never the
    type, so a child 8 in wide in a group drawn at half size wraps at 4 in.

    shape is what an edit changes: the shape itself, or the table that holds a
    cell. key tells one frame from another on its slide, and cell is (row, column,
    rows spanned) for a table cell and None otherwise."""

    def __init__(self, shape, text_frame, left, top, width, height, insets, wrap,
                 kind, key, name, cell=None, scale=(1.0, 1.0)):
        self.shape = shape
        self.text_frame = text_frame
        self.left, self.top, self.width, self.height = left, top, width, height
        self.insets = insets            # (left, right, top, bottom), EMU
        self.wrap = wrap
        self.kind = kind                # "shape", "child" or "cell"
        self.key = key
        self.name = name
        self.cell = cell
        self.scale = scale


IDENTITY = (1.0, 0.0, 1.0, 0.0)         # (sx, tx, sy, ty): slide = child * s + t


def _group_transform(group, outer):
    """The transform of a group's children, composed with the one it sits in."""
    xfrm = group._element.find(qn("p:grpSpPr")).find(qn("a:xfrm"))
    if xfrm is None:
        return outer

    def pair(tag, a, b):
        el = xfrm.find(qn(tag))
        return (int(el.get(a)), int(el.get(b))) if el is not None else (0, 0)

    (ox, oy), (cx, cy) = pair("a:off", "x", "y"), pair("a:ext", "cx", "cy")
    (chx, chy), (chcx, chcy) = pair("a:chOff", "x", "y"), pair("a:chExt", "cx", "cy")
    gx = cx / float(chcx) if chcx else 1.0
    gy = cy / float(chcy) if chcy else 1.0
    sx, tx, sy, ty = outer
    return (sx * gx, sx * (ox - chx * gx) + tx, sy * gy, sy * (oy - chy * gy) + ty)


def _cell_frames(gf, xf):
    sx, tx, sy, ty = xf
    tbl = gf.table
    widths = [col.width for col in tbl.columns]
    heights = [row.height for row in tbl.rows]
    for r in range(len(heights)):
        for c in range(len(widths)):
            cell = tbl.cell(r, c)
            # A cell under a merge draws nothing; the merge origin holds the text.
            if cell.is_spanned:
                continue
            left = (gf.left or 0) + sum(widths[:c])
            top = (gf.top or 0) + sum(heights[:r])
            yield Frame(gf, cell.text_frame, left * sx + tx, top * sy + ty,
                        sum(widths[c:c + cell.span_width]) * sx,
                        sum(heights[r:r + cell.span_height]) * sy,
                        (cell.margin_left, cell.margin_right, cell.margin_top,
                         cell.margin_bottom),
                        True, "cell", (gf.shape_id, r, c),
                        "%s row %d col %d" % (gf.name, r + 1, c + 1),
                        cell=(r, c, cell.span_height), scale=(sx, sy))


def text_frames(shapes, _xf=IDENTITY):
    """A Frame for every place text lives among these shapes: each shape with a
    text frame, the shapes inside each group at any depth, and each table cell. A
    cell always wraps, and its width is its columns less its own margins."""
    sx, tx, sy, ty = _xf
    for shape in shapes:
        if isinstance(shape, GroupShape):
            for f in text_frames(shape.shapes, _group_transform(shape, _xf)):
                yield f
        elif getattr(shape, "has_table", False):
            for f in _cell_frames(shape, _xf):
                yield f
        elif shape.has_text_frame:
            tf = shape.text_frame
            yield Frame(shape, tf, (shape.left or 0) * sx + tx, (shape.top or 0) * sy + ty,
                        (shape.width or 0) * sx, (shape.height or 0) * sy,
                        (tf.margin_left or 0, tf.margin_right or 0,
                         tf.margin_top or 0, tf.margin_bottom or 0),
                        tf.word_wrap is not False,
                        "shape" if _xf == IDENTITY else "child", (shape.shape_id,),
                        shape.name, scale=(sx, sy))


def as_frame(shape):
    """A shape, or a Frame already."""
    return shape if isinstance(shape, Frame) else next(text_frames([shape]))


def wraps(shape):
    """False only for a frame that says wrap="none". A frame that says nothing
    takes PowerPoint's default, which wraps. Takes a shape or a Frame."""
    return as_frame(shape).wrap


def tokens(p, default_family):
    """[(word, bold, family)] for one paragraph, with (BREAK, bold, family) where
    it has a line break. A word takes the weight and family of the run it starts
    in, which is right for the bold lead-in pattern."""
    full = ""
    spans = []
    runs = iter(p.runs)
    last = (False, default_family)
    for child in p._p:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "r":
            r = next(runs)
            last = (bool(r.font.bold), run_family(r, default_family))
            text = r.text
        elif tag == "br":
            text = BREAK
        else:
            continue
        spans.append((len(full), len(full) + len(text)) + last)
        full += text
    out = []
    # BREAK is whitespace to \S, so it is matched on its own.
    for m in re.finditer(r"\v|\S+", full):
        hit = next((s for s in spans if s[0] <= m.start() < s[1]), None)
        out.append((m.group(), hit[2] if hit else False,
                    hit[3] if hit else default_family))
    return out


def text_of(toks):
    return " ".join(w for w, _b, _f in toks if w != BREAK)


def segment_lines(toks, size_pt, width_pt, wrap=True):
    """[[line widths in points]] for each stretch between line breaks: a greedy
    word wrap, or with wrap=False one line per stretch whatever its width. None if
    a font file is missing, in which case nothing can be measured."""
    out = []
    cur = 0.0
    n = 0
    seg = []
    for word, bold, family in toks:
        if word == BREAK:
            seg.append(cur)
            out.append(seg)
            cur, n, seg = 0.0, 0, []
            continue
        f = font(family, bold, size_pt)
        if f is None:
            return None
        ww = f.getlength(word) / SCALE
        sp = f.getlength(" ") / SCALE
        cand = cur + (sp if n else 0.0) + ww
        if not wrap or cand <= width_pt or n == 0:
            cur = cand
            n += 1
        else:
            seg.append(cur)
            cur = ww
            n = 1
    seg.append(cur)
    out.append(seg)
    return out


def lines(toks, size_pt, width_pt, wrap=True):
    """The width in points of each line the paragraph is drawn on, or None if a
    font file is missing. A line break always starts a line; wrap=False is a frame
    that never wraps, so only a break does."""
    segs = segment_lines(toks, size_pt, width_pt, wrap)
    return None if segs is None else [w for seg in segs for w in seg]


def para_width(shape, p):
    """Usable width of one paragraph in points: the box as drawn minus its insets
    and minus the paragraph's own left margin, which a bulleted paragraph always
    has. Takes a shape or a Frame."""
    f = as_frame(shape)
    inset = (f.insets[0] + f.insets[1]) / 12700.0
    pPr = p._p.pPr
    marl = int(pPr.get("marL", 0)) / 12700.0 if pPr is not None else 0.0
    return f.width / 12700.0 - inset - marl


def orphan(toks, size_pt, width_pt, min_ratio):
    """(is_orphan, line_count_at_nominal_width). Checked at the nominal width and
    at plus and minus 3 percent, so a paragraph that only breaks in PowerPoint is
    still caught. A short line that a line break ends was put there on purpose, so
    only the last line of each stretch that wraps counts, and the count leaves out
    the lines the breaks add."""
    bad = False
    n_at = 0
    for k in (1.0, 0.97, 1.03):
        segs = segment_lines(toks, size_pt, width_pt * k)
        if segs is None:
            return False, 0
        if k == 1.0:
            n_at = sum(len(seg) for seg in segs) - (len(segs) - 1)
        if any(len(seg) >= 2 and seg[-1] < min_ratio * width_pt for seg in segs):
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


def paragraphs(prs, default_family, skip_first):
    """(slide_number, frame, paragraph, tokens) for every paragraph that can be
    measured, in groups and table cells too."""
    for si, slide in enumerate(prs.slides):
        if skip_first and si == 0:
            continue
        for frame in text_frames(slide.shapes):
            # A frame that never wraps cannot leave a short last line.
            if not frame.wrap:
                continue
            for p in frame.text_frame.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if toks:
                    yield si + 1, frame, p, toks


def report(prs, default_family="Inter", min_ratio=0.34, skip_first=True,
           at_risk_fill=AT_RISK_FILL):
    """[(slide_number, text, kind)] for every paragraph that needs attention.
    kind is "orphan" for a short last line that is already there, and "at risk"
    for one that appears as soon as the metrics shift slightly."""
    out = []
    for n, frame, p, toks in paragraphs(prs, default_family, skip_first):
        size = p.runs[0].font.size.pt
        pw = para_width(frame, p)
        bad, count = orphan(toks, size, pw, min_ratio)
        text = text_of(toks)
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
        for frame in text_frames(slide.shapes):
            # Narrowing a frame that never wraps only pushes more of it outside.
            if not frame.wrap:
                continue
            tf = frame.text_frame

            # Pass 1: shrink the font of the offending paragraph until the short
            # last line disappears, or until the text needs one line fewer.
            for p in tf.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if not toks:
                    continue
                size = p.runs[0].font.size.pt
                pw = para_width(frame, p)
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
            # narrower box pulls a word down onto the last line. A cell has no box
            # of its own: its column is every cell above and below it too.
            if frame.kind == "cell":
                continue
            paras = []
            for p in tf.paragraphs:
                if not p.runs or p.runs[0].font.size is None:
                    continue
                toks = tokens(p, default_family)
                if toks:
                    paras.append((toks, p.runs[0].font.size.pt, para_width(frame, p)))
            if not paras:
                continue

            def count_orphans(scale):
                bad = total = 0
                for toks, size, pw in paras:
                    narrower = pw - (1 - scale) * frame.width / 12700.0
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
                    # In the shape's own coordinates, which a group scales.
                    frame.shape.width = int(frame.shape.width * scale)
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
    # A paragraph in a font with no file was never measured, so it did not pass.
    missed = {}
    synthesised = {}
    unmeasured = 0
    for n, _shape, _p, toks in paragraphs(prs, a.font, skip_first):
        keys = missing_fonts(toks)
        unmeasured += bool(keys)
        for key in keys:
            missed.setdefault(key, []).append(n)
        for family in synthesised_fonts(toks):
            synthesised.setdefault(family, []).append(n)
    for family, found_on in sorted(synthesised.items()):
        slides = sorted(set(found_on))
        print('  note: %d paragraph%s measured with "%s" Regular for bold, on slide%s %s (%s)'
              % (len(found_on), "" if len(found_on) == 1 else "s", family,
                 "" if len(slides) == 1 else "s", ", ".join(str(s) for s in slides),
                 SYNTHESISED))
    if not rows and not missed:
        print("no orphans, no paragraphs at risk")
        return 0
    for n, text, kind in rows:
        print("  slide %-3d %-8s %s" % (n, kind, text[:70]))
    for (family, bold), found_on in sorted(missed.items()):
        slides = sorted(set(found_on))
        print('  not measured: %d paragraph%s, font "%s"%s not found, on slide%s %s'
              % (len(found_on), "" if len(found_on) == 1 else "s", family,
                 " bold" if bold else "", "" if len(slides) == 1 else "s",
                 ", ".join(str(s) for s in slides)))
    n_orphan = sum(1 for r in rows if r[2] == "orphan")
    print("%d orphan, %d at risk%s" % (n_orphan, len(rows) - n_orphan,
                                       ", %d not measured" % unmeasured if missed else ""))
    if n_orphan:
        return 1
    return 2 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
