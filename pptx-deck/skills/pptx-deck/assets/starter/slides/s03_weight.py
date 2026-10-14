# -*- coding: utf-8 -*-
"""A card row. Still two blocks: the cards and the takeaway."""
import os

from helpers import ICONS, T, header, pic, rect, t1, takeaway, tb

NOTES = ("Cards are outlined in the one grey, never filled with colour and "
         "never rounded. Each one still carries an icon.")

CARDS = [("eye-off", "No accent", "One ink on white. Hierarchy is size and weight."),
         ("scale", "One grey", "#CFCFCF for rules, hairlines and card outlines."),
         ("flag", "One marker", "#E6E6E6 behind a single bold phrase per slide.")]


def build(s):
    header(s, "Weight, size, and one marker", section="Grammar")
    cw = (T.CW - 2 * 0.24) / 3
    for i, (icon, head, body) in enumerate(CARDS):
        x = T.ML + i * (cw + 0.24)
        rect(s, x, 1.60, cw, 2.02, fill=None, line=T.GRAY)
        path = os.path.join(ICONS, icon + ".png")
        if os.path.exists(path):
            pic(s, path, x + 0.22, 1.82, w=0.40)
        t1(s, x + 0.22, 2.40, cw - 0.44, 0.30, head, size=T.S_BODY, bold=True)
        tb(s, x + 0.22, 2.78, cw - 0.44, 0.70, [dict(t=body, size=T.S_DESC, after=0)])
    takeaway(s, "If you reach for a colour, the answer this instance wants is weight.",
             phrase="the answer this instance wants is weight")
