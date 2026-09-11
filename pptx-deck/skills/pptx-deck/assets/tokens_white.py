# -*- coding: utf-8 -*-
"""Tokens for the white reference instance. See references/instance-white-ref.md.

This file holds numbers, not behaviour. Import it, or copy it next to your builder
and edit the values. Nothing here knows what a slide looks like: that is the job of
your build() and of starter_build.py.

If the user brought their own reference deck, do not use this file. Run
`python3 scripts/extract_ref.py <ref.pptx>` and let it write a tokens.py of the
same shape from their deck.
"""
from pptx.dml.color import RGBColor

# ---------------------------------------------------------------- canvas
W, H = 10.0, 5.625          # inches, 16 by 9. A 13.333 canvas needs a different type scale.
ML, MR = 0.67, 9.33         # left and right content margins
CW = MR - ML                # 8.66 in of usable width
CONTENT_BOTTOM = 5.30       # nothing but the page number may cross this line
PAGE_Y = 5.42               # baseline box top for the page number
PAGE_X, PAGE_W = 8.90, 0.43 # page number is right aligned inside this box
CAPTION_GAP = 0.16          # picture bottom to caption top

# Header block. Both are box tops, and both are fixed on every content slide.
LABEL_Y = 0.36              # small grey section label
TITLE_Y = 0.67              # slide title
BODY_TOP = 1.30             # first content block starts no higher than this

# ---------------------------------------------------------------- colour
# One ink, one grey, one chip, one marker. There is no accent colour, on purpose.
BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0xCF, 0xCF, 0xCF)    # rules, table hairlines, card outlines
CHIP = RGBColor(0xEE, 0xEE, 0xEE)    # chip and card fill
HL = "E6E6E6"                        # marker highlight, as a hex string for a:highlight

# Every text level is black. Hierarchy comes from size and weight only.
DIM = BLACK
SEC = BLACK
CARD_TXT = BLACK

# ---------------------------------------------------------------- type
FONT = "Inter"               # regular and bold only, no light and no italic
FONT_FILES = {               # the real files, for measuring line breaks with PIL
    False: "~/Library/Fonts/Inter-Regular.otf",
    True: "~/Library/Fonts/Inter-Bold.otf",
}

S_SEC = 34.2     # section divider slide
S_LABEL = 21.4   # large left hand label on a split slide
S_TITLE = 17.1   # slide title
S_BODY = 12.8    # body text and the takeaway line
S_DESC = 10.7    # secondary description under a heading. This is the body floor.
S_SMALL = 8.55   # section label, caption, page number, footnote
S_TAKE = S_BODY  # takeaway line at the bottom of a content slide

BODY_FLOOR = 10.7  # do not set body text smaller than this to make text fit

LINE = 1.12      # default line spacing multiple
AFTER = 4        # default space after a paragraph, in points

# ---------------------------------------------------------------- rules of this instance
# Kept here so a builder that imports tokens also imports the constraints.
FORBIDDEN = (
    "accent colour, coloured bands, rounded corners, shadows, "
    "table header fills, coloured cards, gradients"
)
ORPHAN_MIN_RATIO = 0.34   # a last line shorter than this share of the box is an orphan
