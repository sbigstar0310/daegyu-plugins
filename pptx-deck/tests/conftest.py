# -*- coding: utf-8 -*-
"""Shared fixtures. No test measures with a font installed on the machine: the
`fonts` fixture points the font search at an empty directory and writes only the
fonts a test asks for, in which every glyph is exactly half an em wide unless the
test names the glyphs that differ.

fontTools is imported without a fallback on purpose. A test suite that skips
itself when a font tool is missing would repeat the bug it guards against.
"""
import os
import sys

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       os.pardir, "skills", "pptx-deck", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import fix_orphans as M  # noqa: E402


def make_font(path, family, style, typographic=None, widths=None):
    """A TrueType font whose printable ASCII glyphs all advance 500 of 1000 units.
    typographic is (nameID 16, nameID 17), for a static instance that keeps its
    weight in the legacy family name, such as "Inter SemiBold" / "Regular".
    widths is {character: advance} for the glyphs that differ, which makes the
    font proportional."""
    chars = list(range(32, 127))
    order = [".notdef"] + ["u%04X" % c for c in chars]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({c: "u%04X" % c for c in chars})
    glyphs = {}
    for name in order:
        pen = TTGlyphPen(None)
        if name not in (".notdef", "u0020"):
            pen.moveTo((50, 0))
            pen.lineTo((50, 700))
            pen.lineTo((450, 700))
            pen.lineTo((450, 0))
            pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    advance = {"u%04X" % ord(c): w for c, w in (widths or {}).items()}
    fb.setupHorizontalMetrics({n: (advance.get(n, 500), 0) for n in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    names = {"familyName": family, "styleName": style}
    if typographic:
        names.update(typographicFamily=typographic[0], typographicSubfamily=typographic[1])
    fb.setupNameTable(names)
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.save(path)


@pytest.fixture
def fonts(tmp_path, monkeypatch):
    """An empty font path with cold caches. Call it to add a font:

        fonts("Inter-hash.ttf", "Inter", "Regular")
        fonts("Sans.ttf", "Sans", "Regular", widths={"i": 250, "W": 900})

    A test that requests it and adds nothing runs on a machine with no fonts."""
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    monkeypatch.setattr(M, "FONT_DIRS", [str(font_dir)])
    monkeypatch.setattr(M, "_file_cache", {})
    monkeypatch.setattr(M, "_font_cache", {})
    monkeypatch.setattr(M, "_name_table", None)

    def add(filename, family, style, typographic=None, widths=None):
        path = str(font_dir / filename)
        make_font(path, family, style, typographic, widths)
        # A lookup made before this font existed must not answer for it.
        M._file_cache.clear()
        M._font_cache.clear()
        M._name_table = None
        return path

    return add
