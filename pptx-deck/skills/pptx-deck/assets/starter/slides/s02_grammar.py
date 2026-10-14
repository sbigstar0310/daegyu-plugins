# -*- coding: utf-8 -*-
"""Bullets plus icons. Two blocks, so it is inside the density budget."""
import os

from helpers import ICONS, T, bullets, header, pic, t1, takeaway

NOTES = ("The icons come from assets/icons. They are already ink black at "
         "stroke width 1.6, so they sit at the same weight as the body text.")


def build(s):
    header(s, "Every slide carries a picture", section="Grammar")
    bullets(s, T.ML, 1.50, 5.40, 2.40, [
        ("Header", "a grey label above a bold title, on every slide"),
        ("Body", "at most three blocks, and one of them is a picture"),
        ("Takeaway", "one closing line, one phrase on the marker"),
    ], after=16)
    for i, name in enumerate(["workflow", "shield-check", "gauge"]):
        path = os.path.join(ICONS, name + ".png")
        if os.path.exists(path):
            pic(s, path, 6.55, 1.55 + i * 1.05, w=0.46)
            t1(s, 7.20, 1.60 + i * 1.05, 2.10, 0.30, name, size=T.S_DESC)
    takeaway(s, "A slide with no picture is a slide the audience reads instead of listens to.",
             phrase="reads instead of listens")
