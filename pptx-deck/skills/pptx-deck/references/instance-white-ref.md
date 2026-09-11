# Instance: the white reference

The bundled default when the user has no reference deck of their own. Tokens live
in `assets/tokens_white.py`; `assets/starter_build.py` is a worked three-slide deck
against them.

It was extracted from a real reference that a presenter chose for a graduate talk,
and then hardened across about a hundred rounds of page-by-page feedback.

## The shape of it

| Parameter | Value |
|---|---|
| Canvas | 10 x 5.625 in, 16 by 9 |
| Margins | x from 0.67 to 9.33, content bottom 5.30, page number at y 5.42 |
| Font | Inter, regular and bold only |
| Ink | Pure black on white |
| Rules and card fill | One grey, `#CFCFCF` |
| Chips | `#EEEEEE` |
| Emphasis | A `#E6E6E6` marker highlight behind one bold phrase, once per slide |
| Accent colour | None |

Type scale in points on this canvas: section label 8.55, body 12.8, description
10.7, small 8.55, slide title 17.1, section divider 34.2. The body floor is 10.7.
These are not transferable numbers. On a 13.333 in canvas the same optical size is
about 17 pt.

## The grammar

- A small grey section label sits above every slide title, so the audience always
  knows which part of the talk they are in. No separate section divider slides in
  the main flow.
- One takeaway line at the bottom of a content slide, with exactly one phrase on
  the marker. Not every slide needs one.
- Tables have no header fill. A hairline under the header row and nothing else.
- Figures are placed as images and captioned in small grey text below, with the
  caption anchored to the picture's returned height.
- Page numbers are drawn text, bottom right, on visible slides only.

## FORBIDDEN

Accent colour, coloured bands, rounded corners, shadows, table header fills,
coloured cards, gradients. If you find yourself reaching for one, the answer this
deck wants is weight, size, or the marker.

## Where it came from

A talk on an arXiv paper, 15 minutes plus discussion, presented by a non-native
English speaker to a graduate class. That origin explains three of its habits: the
full argument is on the slide rather than only a key sentence, every slide carries
a picture or icons, and no line is allowed to end with one or two words alone.
