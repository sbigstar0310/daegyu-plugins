#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a deck the way a projector will: LibreOffice to PDF, then PDF to PNG.

    python3 scripts/render_real.py deck.pptx                 # -> render/s01.png ...
    python3 scripts/render_real.py deck.pptx --dpi 200 -o build/render
    python3 scripts/render_real.py deck.pptx --slides 8,13   # re-render two pages

This is the only render you are allowed to judge line breaks from. The matplotlib
previewer uses a proxy font and approximates wrapping, so it can tell you where a
box sits and never where a line ends.

Three traps it handles for you.

Hidden slides do not appear in the PDF, so page N is not slide N. The map is
printed every time, and the PNG for a slide is named by its slide number, not by
its page number.

A render older than the deck is not evidence. Any PNG left from a previous run is
deleted before this one starts, and the deck's own mtime is printed.

LibreOffice substitutes a missing font in silence. Every family the deck names is
resolved against the font directories first, and a missing one is a hard error,
because every line break in the output would be fiction.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_orphans import font_file  # noqa: E402

SOFFICE = [
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice", "/usr/local/bin/soffice", "/snap/bin/libreoffice",
]


def find_soffice():
    for p in SOFFICE:
        if os.path.exists(p):
            return p
    return shutil.which("soffice") or shutil.which("libreoffice")


def families(prs):
    """Every font family named by a run in the deck, most used first."""
    from collections import Counter
    c = Counter()
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if r.font.name:
                        c[r.font.name] += len(r.text)
    return [f for f, _n in c.most_common()]


def slide_map(prs):
    """[(slide_number, page_number or None)]. A hidden slide has no page."""
    out = []
    page = 0
    for i, slide in enumerate(prs.slides):
        hidden = slide._element.get("show") == "0"
        if hidden:
            out.append((i + 1, None))
        else:
            page += 1
            out.append((i + 1, page))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("-o", "--out", default="render", help="directory for the PNGs")
    ap.add_argument("--dpi", type=int, default=120, help="120 to review layout, 200 to read text")
    ap.add_argument("--slides", help="only write these slide numbers, comma separated")
    ap.add_argument("--keep-pdf", action="store_true")
    ap.add_argument("--allow-missing-font", action="store_true",
                    help="render anyway. Line breaks in the output will be wrong.")
    a = ap.parse_args()

    from pptx import Presentation
    prs = Presentation(a.deck)

    soffice = find_soffice()
    if not soffice:
        sys.stderr.write(
            "LibreOffice is not installed, and there is no other way to see the real\n"
            "line breaks. Install it:\n"
            "    brew install --cask libreoffice        # macOS\n"
            "    sudo apt-get install -y libreoffice    # Debian or Ubuntu\n")
        return 2

    missing = [f for f in families(prs) if font_file(f, False) is None]
    if missing:
        msg = ("the deck asks for %s and no file for it was found.\n"
               "LibreOffice will substitute another font without saying so, and every\n"
               "line break below would be fiction. Install the font, or copy it into\n"
               "/Applications/LibreOffice.app/Contents/Resources/fonts/truetype\n"
               % ", ".join(missing))
        if not a.allow_missing_font:
            sys.stderr.write(msg)
            return 2
        sys.stderr.write("WARNING: " + msg)

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    # Not `rm -f DIR/*.png`: zsh aborts the whole command on an unmatched glob.
    for old in glob.glob(os.path.join(out, "s*.png")):
        os.remove(old)

    deck = os.path.abspath(a.deck)
    print("deck    %s" % deck)
    print("        modified %s" % time.strftime("%Y-%m-%d %H:%M:%S",
                                                time.localtime(os.path.getmtime(deck))))

    r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", out, deck],
                       capture_output=True, text=True)
    pdf = os.path.join(out, os.path.splitext(os.path.basename(deck))[0] + ".pdf")
    if not os.path.exists(pdf):
        sys.stderr.write("LibreOffice produced no PDF.\n%s\n%s\n" % (r.stdout, r.stderr))
        sys.stderr.write("If PowerPoint has the deck open, a ~$ lock file is in the way.\n")
        return 2

    import pymupdf
    doc = pymupdf.open(pdf)

    smap = slide_map(prs)
    visible = [s for s, p in smap if p is not None]
    hidden = [s for s, p in smap if p is None]
    if doc.page_count != len(visible):
        sys.stderr.write("WARNING: %d pages but %d visible slides. The map below is a guess.\n"
                         % (doc.page_count, len(visible)))

    want = None
    if a.slides:
        want = {int(x) for x in a.slides.replace(" ", "").split(",") if x}

    written = 0
    for slide_no, page_no in smap:
        if page_no is None or (want and slide_no not in want):
            continue
        path = os.path.join(out, "s%02d.png" % slide_no)
        doc[page_no - 1].get_pixmap(dpi=a.dpi).save(path)
        written += 1
    page_count = doc.page_count
    doc.close()
    if not a.keep_pdf:
        os.remove(pdf)

    print("slides  %d, visible %d, hidden %d" % (len(smap), len(visible), len(hidden)))
    print("pages   %d at %d dpi, wrote %d PNG into %s" % (page_count, a.dpi, written, out))
    if hidden:
        print("\nslide to page map. Hidden slides are in the file but not in the PDF,")
        print("so do not look for slide %d on page %d." % (hidden[0], hidden[0]))
        rows = ["%d>%s" % (s, p if p else "hidden") for s, p in smap]
        for i in range(0, len(rows), 8):
            print("  " + "  ".join(rows[i:i + 8]))
    else:
        print("no hidden slides, so page N is slide N")
    return 0


if __name__ == "__main__":
    sys.exit(main())
