#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read a reference deck and write a tokens.py you can build against.

    python3 scripts/extract_ref.py ref.pptx
    python3 scripts/extract_ref.py ref.pptx -o ref/tokens.py --render ref/render

The tokens are a draft, not an answer. The numbers below are measured and
trustworthy; what they mean is not. Read the rendered slides before you build
anything, because the mistake that ships a deck the user rejects is matching the
fonts and the colours out of the XML and missing the visual grammar: what sits
above the title, whether bullets are boxed, where emphasis is allowed to live,
how much of the slide stays empty.

So the render is not optional. --render writes every reference slide as a PNG
through LibreOffice, and you should look at them.

What is measured here:

  canvas     the slide size, which decides the whole type scale
  font       the family the runs actually use, which is often not the theme's
  margins    the left and right edge most shapes share, and the lowest content
  scale      every distinct size with how many characters are set in it
  colour     every fill and every text colour, by how much of the deck uses it
"""
import argparse
import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EMU = 914400.0
TABLE = 19


def iter_shapes(prs):
    for i, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            yield i + 1, slide, shape


def iter_runs(prs):
    for n, _slide, shape in iter_shapes(prs):
        if not shape.has_text_frame:
            continue
        for p in shape.text_frame.paragraphs:
            for r in p.runs:
                if r.text.strip():
                    yield n, shape, p, r


def measure(prs):
    out = {}
    out["w"] = prs.slide_width / EMU
    out["h"] = prs.slide_height / EMU

    fonts = Counter()
    sizes = Counter()
    inks = Counter()
    wide = Counter()      # characters set in a box wider than half the content
    header = Counter()    # characters sitting in the top band, above the body
    cw_guess = (prs.slide_width / EMU) * 0.55
    for _n, shape, _p, r in iter_runs(prs):
        k = len(r.text)
        if r.font.name:
            fonts[r.font.name] += k
        if r.font.size is not None:
            pt = round(r.font.size.pt, 2)
            sizes[pt] += k
            if (shape.width or 0) / EMU >= cw_guess:
                wide[pt] += k
            if (shape.top or 0) / EMU < 1.20:
                header[pt] += k
        try:
            if r.font.color is not None and r.font.color.type is not None \
                    and r.font.color.rgb is not None:
                inks[str(r.font.color.rgb)] += k
        except (AttributeError, TypeError, ValueError):
            pass
    out["fonts"] = fonts
    out["sizes"] = sizes
    out["inks"] = inks
    out["wide"] = wide
    out["header"] = header

    fills = Counter()
    lines = Counter()
    for _n, _slide, shape in iter_shapes(prs):
        try:
            if shape.fill.type == 1:  # MSO_FILL.SOLID
                fills[str(shape.fill.fore_color.rgb)] += 1
        except (AttributeError, TypeError, ValueError, NotImplementedError):
            pass
        try:
            if shape.line.fill.type == 1:
                lines[str(shape.line.color.rgb)] += 1
        except (AttributeError, TypeError, ValueError, NotImplementedError):
            pass
    out["fills"] = fills
    out["lines"] = lines

    lefts, rights = Counter(), Counter()
    bottoms, tops = [], []
    for _n, _slide, shape in iter_shapes(prs):
        if not shape.width or not shape.height:
            continue
        l = shape.left / EMU
        t = shape.top / EMU
        lefts[round(l, 2)] += 1
        rights[round(l + shape.width / EMU, 2)] += 1
        if shape.height / EMU > 0.25:
            bottoms.append(t + shape.height / EMU)
            tops.append(t)
    out["ml"] = lefts.most_common(1)[0][0] if lefts else 0.5
    out["mr"] = rights.most_common(1)[0][0] if rights else out["w"] - 0.5
    bottoms.sort()
    tops.sort()
    out["content_bottom"] = round(bottoms[int(len(bottoms) * 0.95)], 2) if bottoms else out["h"] - 0.3
    out["page_y"] = round(max(bottoms), 2) if bottoms else out["h"] - 0.2
    out["first_top"] = round(tops[int(len(tops) * 0.02)], 2) if tops else 0.3
    return out


def name_scale(m, min_share=0.01):
    """Give the measured sizes the names a builder will want.

    Character count alone gets this wrong. A reference full of small annotations
    has more characters at the caption size than at the body size, and naming the
    caption "body" poisons every later decision. So two more signals are used.

    Body is the size that carries the most text inside WIDE boxes, because a body
    column spans the content width and a caption or a diagram label does not.
    Title is the size that dominates the header band at the top of the slide.
    Section is simply the largest size in use, which is the divider.
    """
    sizes = m["sizes"]
    if not sizes:
        return {}
    total = sum(sizes.values()) or 1
    real = [s for s, n in sizes.items() if n >= total * min_share]
    if not real:
        real = list(sizes)

    wide = Counter({s: n for s, n in m["wide"].items() if s in real})
    body = (wide.most_common(1)[0][0] if wide
            else Counter({s: sizes[s] for s in real}).most_common(1)[0][0])

    header = Counter({s: n for s, n in m["header"].items() if s in real and s > body})
    largest = max(real)
    title = None
    if header:
        # The divider size also lives at the top, so prefer the header size that
        # is not the largest one in the deck.
        ranked = [s for s, _n in header.most_common()]
        title = next((s for s in ranked if s != largest), ranked[0])
    above = sorted([s for s in real if s > body], reverse=True)
    if title is None and above:
        title = above[-1]

    named = {"S_BODY": body}
    if largest > body:
        named["S_SEC"] = largest
    if title and title != largest:
        named["S_TITLE"] = title
    mid = [s for s in above if s != largest and s != title]
    if mid:
        named["S_LABEL"] = max(mid)
    below = sorted([s for s in real if s < body], reverse=True)
    if below:
        named["S_DESC"] = below[0]
        named["S_SMALL"] = below[-1]
    return named


def write_tokens(m, path):
    fonts = m["fonts"]
    font = fonts.most_common(1)[0][0] if fonts else "Arial"
    named = name_scale(m)
    inks = m["inks"]
    ink = inks.most_common(1)[0][0] if inks else "000000"
    # The supporting colours: every fill and outline that is neither the ink nor
    # the paper. This is where a reference's one grey, or its accent, shows up.
    support = Counter()
    support.update(m["fills"])
    support.update(m["lines"])
    greys = [c for c, _n in support.most_common() if c not in (ink, "FFFFFF")]
    total = sum(m["sizes"].values()) or 1

    lines = []
    a = lines.append
    a("# -*- coding: utf-8 -*-")
    a('"""Tokens measured from %s. A draft: check every name against the render."""'
      % os.path.basename(m["source"]))
    a("from pptx.dml.color import RGBColor")
    a("")
    a("# ---------------------------------------------------------------- canvas")
    a("W, H = %.3f, %.3f" % (m["w"], m["h"]))
    a("ML, MR = %.2f, %.2f        # the left and right edge most shapes share" % (m["ml"], m["mr"]))
    a("CW = MR - ML")
    a("CONTENT_BOTTOM = %.2f      # 95 percent of content ends above this" % m["content_bottom"])
    a("PAGE_Y = %.2f              # the lowest thing on any slide" % m["page_y"])
    a("BODY_TOP = %.2f            # the highest thing on any slide" % m["first_top"])
    a("")
    a("# ---------------------------------------------------------------- colour")
    a('BLACK = RGBColor(0x00, 0x00, 0x00)')
    a('WHITE = RGBColor(0xFF, 0xFF, 0xFF)')
    a("INK = RGBColor(0x%s, 0x%s, 0x%s)     # %d percent of the deck's text"
      % (ink[0:2], ink[2:4], ink[4:6], 100 * inks[ink] // (sum(inks.values()) or 1)))
    if not greys:
        a("# No fill or outline colour other than the ink. This reference draws")
        a("# hierarchy with size and weight alone.")
    for i, c in enumerate(greys[:3]):
        a("SUPPORT_%d = RGBColor(0x%s, 0x%s, 0x%s)   # used %d times"
          % (i + 1, c[0:2], c[2:4], c[4:6], support[c]))
    a('HL = "E6E6E6"   # marker highlight. Not measurable: pick one from the render.')
    a("")
    a("# ---------------------------------------------------------------- type")
    a('FONT = "%s"' % font)
    a("FONT_FILES = {")
    a('    False: "~/Library/Fonts/%s-Regular.otf",' % font.replace(" ", ""))
    a('    True: "~/Library/Fonts/%s-Bold.otf",' % font.replace(" ", ""))
    a("}")
    a("")
    for key in ("S_SEC", "S_LABEL", "S_TITLE", "S_BODY", "S_DESC", "S_SMALL"):
        if key in named:
            v = named[key]
            a("%-8s = %5.2f   # %d percent of the characters" % (key, v, 100 * m["sizes"][v] // total))
    if "S_DESC" in named:
        a("BODY_FLOOR = %.2f   # do not set body text smaller than this" % named["S_DESC"])
    a("")
    a("LINE = 1.12")
    a("AFTER = 4")
    a("ORPHAN_MIN_RATIO = 0.34")
    a("")
    a("# Sizes measured but not named, with their share of the characters:")
    for s, n in sorted(m["sizes"].items(), reverse=True):
        if s not in named.values():
            a("#   %5.2f pt  %2d percent" % (s, 100 * n // total))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ref")
    ap.add_argument("-o", "--out", help="write a tokens.py here")
    ap.add_argument("--render", help="render every reference slide into this directory")
    ap.add_argument("--dpi", type=int, default=120)
    a = ap.parse_args()

    from pptx import Presentation
    prs = Presentation(a.ref)
    m = measure(prs)
    m["source"] = a.ref
    total = sum(m["sizes"].values()) or 1

    print("reference  %s, %d slides" % (os.path.basename(a.ref), len(prs.slides)))
    print("canvas     %.3f x %.3f in" % (m["w"], m["h"]))
    print("margins    %.2f to %.2f, content bottom %.2f, lowest %.2f"
          % (m["ml"], m["mr"], m["content_bottom"], m["page_y"]))
    print("font       %s" % ", ".join("%s (%d percent)" % (f, 100 * n // (sum(m["fonts"].values()) or 1))
                                      for f, n in m["fonts"].most_common(4)))
    print("scale      %s" % ", ".join("%.1f (%d percent)" % (s, 100 * n // total)
                                      for s, n in m["sizes"].most_common(8)))
    print("text ink   %s" % ", ".join("#%s x%d" % (c, n) for c, n in m["inks"].most_common(5)))
    print("fills      %s" % (", ".join("#%s x%d" % (c, n) for c, n in m["fills"].most_common(5)) or "none"))
    print("outlines   %s" % (", ".join("#%s x%d" % (c, n) for c, n in m["lines"].most_common(5)) or "none"))

    named = name_scale(m)
    print("")
    print("named      %s" % ", ".join("%s %.1f" % (k, v) for k, v in sorted(named.items(), key=lambda kv: -kv[1])))

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        write_tokens(m, a.out)
        print("\nwrote %s" % a.out)

    if a.render:
        here = os.path.dirname(os.path.abspath(__file__))
        r = subprocess.run([sys.executable, os.path.join(here, "render_real.py"),
                            os.path.abspath(a.ref), "-o", a.render, "--dpi", str(a.dpi)],
                           capture_output=True, text=True)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)

    print("\nNow look at the slides. The numbers above are measured and the names")
    print("are a guess, and the grammar, what goes above the title, whether bullets")
    print("are boxed, where emphasis is allowed, is not in the XML at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
