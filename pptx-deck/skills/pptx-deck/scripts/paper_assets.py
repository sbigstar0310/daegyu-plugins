#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Get figures, tables, formulas and markers out of a paper and onto a slide.

Lift the paper's own figures rather than redrawing them. A redrawn table invites
"is that really what the paper says", and presenters ask for the original by name.

    python3 scripts/paper_assets.py pages  paper.pdf ref/pages     # look first
    python3 scripts/paper_assets.py find   paper.pdf "Figure 1" "Table 8:"
    python3 scripts/paper_assets.py crop   paper.pdf 3 95 112 520 366 ref/crops/fig1.png
    python3 scripts/paper_assets.py trim   ref/crops/fig1.png
    python3 scripts/paper_assets.py probe  ref/crops/fig1.png 0.295 0.365
    python3 scripts/paper_assets.py empty  ref/crops/fig1.png 0.11 0.15 0.085 0.125
    python3 scripts/paper_assets.py badges build/badges 6
    python3 scripts/paper_assets.py eq     '\\mathsf{Complete}' build/eq/complete.png
    python3 scripts/paper_assets.py sym    'q' build/eq/sym_q.png

Two rules that are easy to get wrong.

Crop the figure body, not the paper's caption: the caption's font will not match
your deck, so write your own caption line under the image instead.

Never desaturate a paper figure. If colour carries meaning in it, a green success
path or a red failure edge, greyscaling deletes exactly what the talk points at.
Embed the crop as it is, even in a monochrome deck.
"""
import argparse
import os
import re
import subprocess
import sys

PDFLATEX = ["pdflatex", "/Library/TeX/texbin/pdflatex"]

# BasicTeX ships no standalone.cls, so this is the article class with a wide
# text width and no page furniture, trimmed afterwards on the alpha channel.
TEX = r"""\documentclass[12pt]{article}
\usepackage[paperwidth=%(pw)sin,paperheight=%(ph)sin,margin=0.2in]{geometry}
\usepackage{amsmath,amssymb,amsfonts}
\pagestyle{empty}
\begin{document}
\noindent$\displaystyle %(body)s$
\end{document}
"""


def pdflatex():
    for p in PDFLATEX:
        if os.path.isabs(p):
            if os.path.exists(p):
                return p
        else:
            import shutil
            f = shutil.which(p)
            if f:
                return f
    return None


# ---------------------------------------------------------------- the pdf
def cmd_pages(a):
    """Every page as a PNG, so you can see where a figure sits before cropping."""
    import pymupdf
    os.makedirs(a.out, exist_ok=True)
    doc = pymupdf.open(a.pdf)
    for i, page in enumerate(doc):
        page.get_pixmap(dpi=a.dpi).save(os.path.join(a.out, "p%02d.png" % (i + 1)))
    print("wrote %d pages at %d dpi into %s" % (doc.page_count, a.dpi, a.out))
    print("Page size in points is %.0f x %.0f, and crop takes points, not pixels."
          % (doc[0].rect.width, doc[0].rect.height))
    return 0


def cmd_find(a):
    """Where each phrase appears, in page coordinates, so a crop can be aimed."""
    import pymupdf
    doc = pymupdf.open(a.pdf)
    for phrase in a.phrases:
        found = False
        for i, page in enumerate(doc):
            for r in page.search_for(phrase):
                print("  %-18s page %-3d x %.0f to %.0f, y %.0f to %.0f"
                      % (phrase, i + 1, r.x0, r.x1, r.y0, r.y1))
                found = True
        if not found:
            print("  %-18s not found" % phrase)
    print("\nA figure body usually sits above its caption, so crop from the top of")
    print("the block down to a few points above the caption's y.")
    return 0


def cmd_crop(a):
    """One crop, in page points, rendered at print resolution."""
    import pymupdf
    doc = pymupdf.open(a.pdf)
    page = doc[a.page - 1]
    rect = pymupdf.Rect(a.x0, a.y0, a.x1, a.y1)
    pix = page.get_pixmap(dpi=a.dpi, clip=rect)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    pix.save(a.out)
    print("wrote %s, %d x %d px from page %d at %d dpi"
          % (a.out, pix.width, pix.height, a.page, a.dpi))
    return 0


# ---------------------------------------------------------------- images
def cmd_trim(a):
    """Trim the white or transparent border.

    Trimming changes the aspect ratio, so anything you placed by height has to be
    recomputed afterwards or its caption lands on the block below. Keep the
    untrimmed file: this writes beside the original by default, so running it
    twice does not eat into the figure.
    """
    from PIL import Image, ImageChops
    im = Image.open(a.image)
    out = a.out or a.image
    if im.mode in ("RGBA", "LA"):
        bbox = im.getchannel("A").getbbox()
    else:
        rgb = im.convert("RGB")
        bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
        bbox = ImageChops.difference(rgb, bg).getbbox()
    if not bbox:
        print("nothing to trim")
        return 0
    pad = a.pad
    bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
            min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))
    cropped = im.crop(bbox)
    cropped.save(out)
    print("%s  %d x %d -> %d x %d, aspect %.4f -> %.4f"
          % (out, im.width, im.height, cropped.width, cropped.height,
             im.width / im.height, cropped.width / cropped.height))
    print("Recompute anything you placed by height against the new aspect.")
    return 0


def ink(im, x0, y0, x1, y1):
    """Share of non-white, non-transparent pixels in a fractional rectangle."""
    w, h = im.size
    box = (int(x0 * w), int(y0 * h), max(int(x1 * w), int(x0 * w) + 1),
           max(int(y1 * h), int(y0 * h) + 1))
    patch = im.crop(box).convert("RGBA")
    px = patch.load()
    on = 0
    total = patch.width * patch.height
    for x in range(patch.width):
        for y in range(patch.height):
            r, g, b, alpha = px[x, y]
            if alpha > 40 and (r < 230 or g < 230 or b < 230):
                on += 1
    return on / float(total or 1)


def cmd_probe(a):
    """How much ink sits at each given height, across the full width.

    Use it to find where an arrow runs, so a numbered badge lands on the arrow and
    not on the figure's own label. Guessing from a thumbnail took four rounds and
    still covered a label. Measuring took one.
    """
    from PIL import Image
    im = Image.open(a.image)
    print("%s  %d x %d" % (a.image, im.width, im.height))
    for y in a.ys:
        band = ink(im, 0.0, max(0.0, y - 0.01), 1.0, min(1.0, y + 0.01))
        cells = []
        for k in range(20):
            cells.append(ink(im, k / 20.0, max(0.0, y - 0.01), (k + 1) / 20.0,
                             min(1.0, y + 0.01)))
        bar = "".join("#" if c > 0.10 else ("+" if c > 0.02 else ".") for c in cells)
        print("  y %.3f  ink %.3f  %s" % (y, band, bar))
    print("\n. is empty, + is faint, # is solid. Put a badge on a + or a . next to a #.")
    return 0


def cmd_empty(a):
    """Confirm one rectangle is empty before putting anything in it."""
    from PIL import Image
    im = Image.open(a.image)
    v = ink(im, a.x0, a.y0, a.x1, a.y1)
    verdict = "empty" if v < 0.005 else ("nearly empty" if v < 0.03 else "OCCUPIED")
    print("%s  x %.3f to %.3f, y %.3f to %.3f  ink %.4f  %s"
          % (os.path.basename(a.image), a.x0, a.x1, a.y0, a.y1, v, verdict))
    return 0 if v < 0.03 else 1


def cmd_badges(a):
    """Numbered markers as images: white ring, black disc, white digit.

    Never draw these as a digit inside an oval autoshape. A run centred vertically
    in a shape does not land in the same place in LibreOffice and in PowerPoint,
    so the render lies to you about where the number sits.
    """
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(a.out, exist_ok=True)
    fp = os.path.expanduser(a.font)
    px = a.px
    for n in range(1, a.count + 1):
        path = os.path.join(a.out, "%d.png" % n)
        im = Image.new("RGBA", (px, px), (255, 255, 255, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((0, 0, px - 1, px - 1), fill=(255, 255, 255, 255))
        pad = int(px * 0.075)
        d.ellipse((pad, pad, px - 1 - pad, px - 1 - pad), fill=(0, 0, 0, 255))
        try:
            f = ImageFont.truetype(fp, int(px * 0.56))
        except (OSError, IOError):
            f = ImageFont.load_default()
        # Centre on the glyph's own ink box, not on the font's metrics, or a 1
        # sits visibly left of a 2.
        l, t, r, b = d.textbbox((0, 0), str(n), font=f)
        d.text(((px - (r - l)) / 2 - l, (px - (b - t)) / 2 - t), str(n), font=f,
               fill=(255, 255, 255, 255))
        im.save(path)
    print("wrote %d badges at %d px into %s" % (a.count, px, a.out))
    return 0


# ---------------------------------------------------------------- latex
def render_tex(body, out, pw=6.0, ph=2.0, pad=4):
    exe = pdflatex()
    if not exe:
        sys.stderr.write(
            "pdflatex is not installed, and mathematical symbols set in a body font\n"
            "look wrong beside a figure cropped from the same paper. Install it:\n"
            "    brew install --cask basictex                  # macOS\n"
            "    sudo apt-get install -y texlive-latex-base\n"
            "On macOS it does not land on PATH: it lives at /Library/TeX/texbin/pdflatex.\n")
        return 2
    import tempfile
    import pymupdf
    from PIL import Image
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tex = os.path.join(tmp, "eq.tex")
        with open(tex, "w") as f:
            f.write(TEX % dict(pw=pw, ph=ph, body=body))
        r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error",
                            "-output-directory", tmp, tex],
                           capture_output=True, text=True)
        pdf = os.path.join(tmp, "eq.pdf")
        if not os.path.exists(pdf):
            tail = "\n".join(r.stdout.strip().splitlines()[-12:])
            sys.stderr.write("pdflatex failed:\n%s\n" % tail)
            return 2
        page = pymupdf.open(pdf)[0]
        page.get_pixmap(dpi=600, alpha=True).save(out)
    im = Image.open(out)
    bbox = im.getchannel("A").getbbox()
    if bbox:
        bbox = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))
        im.crop(bbox).save(out)
        im = Image.open(out)
    print("wrote %s, %d x %d px, aspect %.4f" % (out, im.width, im.height, im.width / im.height))
    return 0


def cmd_eq(a):
    return render_tex(a.body, a.out, a.width, a.height)


def cmd_sym(a):
    """One symbol for a legend row. \\vphantom gives every row the same height, so
    a legend of symbols lines up instead of drifting."""
    return render_tex(r"\vphantom{\mathcal{Z}^{*}}" + a.body, a.out, 1.2, 1.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pages", help="every PDF page as a PNG")
    s.add_argument("pdf")
    s.add_argument("out", nargs="?", default="ref/pages")
    s.add_argument("--dpi", type=int, default=110)

    s = sub.add_parser("find", help="where a phrase sits, in page points")
    s.add_argument("pdf")
    s.add_argument("phrases", nargs="+")

    s = sub.add_parser("crop", help="one crop in page points")
    s.add_argument("pdf")
    s.add_argument("page", type=int)
    for k in ("x0", "y0", "x1", "y1"):
        s.add_argument(k, type=float)
    s.add_argument("out")
    s.add_argument("--dpi", type=int, default=300)

    s = sub.add_parser("trim", help="trim the border, and report the new aspect")
    s.add_argument("image")
    s.add_argument("-o", "--out")
    s.add_argument("--pad", type=int, default=2)

    s = sub.add_parser("probe", help="where the ink is, at given heights")
    s.add_argument("image")
    s.add_argument("ys", nargs="+", type=float)

    s = sub.add_parser("empty", help="is this rectangle free")
    s.add_argument("image")
    for k in ("x0", "x1", "y0", "y1"):
        s.add_argument(k, type=float)

    s = sub.add_parser("badges", help="numbered markers as images")
    s.add_argument("out")
    s.add_argument("count", type=int)
    s.add_argument("font", nargs="?", default="~/Library/Fonts/Inter-Bold.otf")
    s.add_argument("--px", type=int, default=600)

    s = sub.add_parser("eq", help="typeset a formula")
    s.add_argument("body")
    s.add_argument("out")
    s.add_argument("--width", type=float, default=6.0)
    s.add_argument("--height", type=float, default=2.0)

    s = sub.add_parser("sym", help="typeset one symbol for a legend")
    s.add_argument("body")
    s.add_argument("out")

    a = ap.parse_args()
    return globals()["cmd_" + a.cmd.replace("-", "_")](a)


if __name__ == "__main__":
    sys.exit(main())
