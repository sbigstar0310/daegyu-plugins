"""Design tokens for the Anywhere-Think talk deck.

Extracted from the first presentation (docs/ppt/Intro.pptx) so the follow-up
deck stays visually aligned. Fonts/colors were read out of the actual slide XML
run properties (the theme XML still carries the default Highcharts palette; the
author overrode it per-run, so THESE values, not the theme, are the truth).

Slide size: 12191675 x 6858000 EMU = 13.33 x 7.5 in = 16:9 widescreen.
Font: Roboto dominates (816 runs) vs Arial/Calibri leftovers -> primary = Roboto.
"""

# ---- geometry (inches) ----
SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN_X = 0.62      # left/right content margin
MARGIN_TOP = 0.55    # eyebrow baseline
CONTENT_TOP = 1.75   # where body content usually starts

# ---- fonts ----
FONT = "Roboto"
FONT_MONO = "Consolas"   # for literal code / markers where a mono face reads better

# ---- color palette (hex, no leading #) ----
INK = "1A2332"       # titles + body (dark navy)
BLUE = "2563EB"      # primary accent: eyebrow labels, emphasis, arrows
GRAY = "5B6372"      # secondary body text, captions, author line
GREEN = "059669"     # positive / "yes"
GREEN_DK = "38761D"  # code-ish positive token (#TODO in original)
RED = "DC2626"       # negative / "no" / collapse
LIGHT = "F3F5F8"     # subtle panel fill
LINE = "E2E6EC"      # hairline separators / table borders
WHITE = "FFFFFF"
PANEL_BLUE = "EEF3FE"  # very light blue callout fill
PANEL_GREEN = "ECF7F1"
PANEL_RED = "FCEEEE"

# semantic aliases used by specs
COLORS = {
    "ink": INK, "blue": BLUE, "gray": GRAY, "green": GREEN,
    "green_dk": GREEN_DK, "red": RED, "white": WHITE, "line": LINE,
}

# ---- type scale (points) ----
SZ_TITLE_HERO = 40   # slide-1 deck title
SZ_TITLE = 25        # per-slide section title
SZ_SUBHEAD = 21      # in-slide subhead ("Next steps")
SZ_EYEBROW = 13      # top-left ALL-CAPS section label
SZ_SUBTITLE = 16     # line under the title
SZ_BODY = 15
SZ_BODY_SM = 13
SZ_TABLE = 13
SZ_SMALL = 12
SZ_FOOT = 10         # footnote citations

def emu(inch):
    return int(inch * 914400)
