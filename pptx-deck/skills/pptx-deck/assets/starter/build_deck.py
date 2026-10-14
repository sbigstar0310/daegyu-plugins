#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A three slide deck in the white reference instance, one file per slide.

Run this first, before you build anything real:

    python3 assets/starter/build_deck.py -o out.pptx
    python3 scripts/render_real.py out.pptx
    python3 scripts/check_layout.py out.pptx

If all three pass, python-pptx, the font and the renderer work, and you know what
the house grammar looks like. If one fails, fix that before writing a real deck.

The layout is the one a real deck uses:

    build_deck.py         the order, page numbers, hidden flags; assembles only
    helpers.py            shared helpers every slide imports
    slides/sNN_name.py    one slide: build(s), NOTES, optionally NUMBERED = False

Each slide module is owned by whoever edits that slide, so edits to different
slides can run in parallel. This file, helpers.py and the tokens are deck-global:
one writer, the main session. A slide agent checks its own slide with a preview
build that never touches the deck:

    python3 assets/starter/build_deck.py --only s03_weight -o preview/s03.pptx

The preview carries the page number and hidden flag the slide has in the deck.
"""
import argparse
import importlib.util
import os
import sys

from pptx import Presentation
from pptx.util import Inches

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import helpers as H  # noqa: E402

# The deck order. Deck-global: only the main session edits this list.
SLIDES = [
    "s01_title",
    "s02_grammar",
    "s03_weight",
]

# Appendix slides: kept in the file, out of the slideshow, never numbered.
HIDDEN = set()


def load(name):
    """Import slides/<name>.py by path, so a slide name needs no package."""
    path = os.path.join(HERE, "slides", name + ".py")
    spec = importlib.util.spec_from_file_location("slides." + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plan():
    """[(name, module, page number or None, hidden)] for the whole deck. Numbers
    count visible, numbered slides only, so a preview of one slide gets the same
    number it has in the full build."""
    out, n = [], 0
    for name in SLIDES:
        mod = load(name)
        hide = name in HIDDEN
        num = None
        if getattr(mod, "NUMBERED", True) and not hide:
            n += 1
            num = n
        out.append((name, mod, num, hide))
    return out


def build(prs, only=None):
    for name, mod, num, hide in plan():
        if only and name not in only:
            continue
        s = H.slide(prs)
        mod.build(s)
        if num is not None:
            H.page_number(s, num)
        if hide:
            s._element.set("show", "0")
        H.notes(s, getattr(mod, "NOTES", ""))
    return prs


def resolve(name):
    """An exact slide name, or a prefix that matches exactly one: s03 is s03_weight."""
    if name in SLIDES:
        return name
    hits = [n for n in SLIDES if n.startswith(name)]
    if len(hits) != 1:
        sys.exit("--only %s: %s" % (name, "matches %s" % ", ".join(hits) if hits
                                    else "not in SLIDES (%s)" % ", ".join(SLIDES)))
    return hits[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--out", help="output .pptx (default starter.pptx, "
                                        "or preview/<name>.pptx with --only)")
    ap.add_argument("--only", action="append", metavar="NAME",
                    help="build only this slide into a preview deck; repeatable")
    a = ap.parse_args(argv)
    only = [resolve(n) for n in a.only] if a.only else None
    out = a.out or (os.path.join("preview", only[0] + ".pptx") if only else "starter.pptx")
    if os.path.dirname(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
    prs = Presentation()
    prs.slide_width = Inches(H.T.W)
    prs.slide_height = Inches(H.T.H)
    build(prs, only)
    prs.save(out)
    print("wrote %s, %d slides" % (out, len(prs.slides)))


if __name__ == "__main__":
    main()
