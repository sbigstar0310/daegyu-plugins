# -*- coding: utf-8 -*-
"""Title. No section label, no page number."""
from helpers import T, t1, rect

NUMBERED = False

NOTES = ("Three slides. If these render and pass the layout check, "
         "the toolchain is working and you can build the real deck.")


def build(s):
    t1(s, T.ML, 2.10, T.CW, 0.90, "The white reference instance", size=T.S_SEC, bold=True)
    t1(s, T.ML, 3.10, 6.20, 0.60,
       "A starter deck that proves the toolchain works", size=T.S_BODY)
    rect(s, T.ML, 3.95, T.CW, 0.01, fill=T.GRAY)
    t1(s, T.ML, 4.15, T.CW, 0.24, "pptx-deck", size=T.S_SMALL)
