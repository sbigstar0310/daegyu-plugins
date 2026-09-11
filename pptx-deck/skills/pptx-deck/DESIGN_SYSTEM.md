# Instance: the anywhere-think house style

**This file is ONE instance of the token contract in `SKILL.md`, not the default
and not the method.** It is the design for the anywhere-think talk decks (deck 1 =
Intro.pptx). `scripts/design.py` holds the same values as importable tokens, and
`scripts/example_deck_grammar.py` is a worked builder against them.

Use it as your spec only when this deck is in that same line. If the user handed
you a reference deck, or asked you to pick a design, this file does not apply: run
`scripts/extract_ref.py` and build from the tokens it writes, or start from
`assets/tokens_white.py`. Read this one only as an example of the shape a filled-in
token set takes.

Every value below is a parameter, not a rule. A real reference has already
contradicted all of them: 10 x 5.625 instead of 13.333 x 7.5, Inter instead of
Roboto, a grey marker instead of a blue accent bar, and no accent colour at all.
The design grammar that used to live in `SKILL.md` (the kicker, the short accent
bar, the light band, blue emphasis) is house grammar and now lives here.

## Canvas
- Size: **13.333 × 7.5 in (16:9)**.
- Content margins: **x ∈ [0.7, 12.63]**. Body region: **y ∈ [1.75, 6.9]**.

## Font
- **Roboto** everywhere (the presenter switched deck 1 to Roboto). Fallback Arial.
- Monospace for code/markers: Consolas (pptx) / DejaVu Sans Mono (preview).

## Colors (hex)
| token | hex | use |
|---|---|---|
| INK | `#1A2332` | titles, body text |
| MUTE | `#5B6372` | captions, footnotes, secondary |
| ACC (blue) | `#2563EB` | kicker, accent bar, the ONE emphasis |
| RED | `#DC2626` | error / negative only |
| GRN | `#059669` | correct / positive only |
| BAND | `#F3F4F6` | neutral band fill |
| WARN | `#FBF7F0` | caveat band fill (cream) |
| HDR | `#E9ECF1` | table header fill (light slate; NOT dark navy) |
| table alt row | `#F7F8FA` | zebra |

Fills are light; color lives in **borders and emphasized words**, not saturated
panels. No colored callout bands, no colored cards, no giant hero numbers.

## Type scale (pt)
- Deck title (slide 1): **40** bold INK.
- Slide title: **25** bold INK.
- Kicker / eyebrow: **13** bold ACC, ALL CAPS.
- Subtitle (title slide): **20** bold ACC (one line, shorten text to fit).
- Body / bullets: **14–17**. In-slide subhead: 15–16 bold.
- Band text: **15–18**. Table cells: **13–14**. Footnote: **11–12**.
- Avoid hero numbers > ~24; put numbers inline-bold in a band or chart instead.

## Header (every content slide)
```
kicker : tbox(0.6, 0.33, 12, 0.4)  → 13pt bold ACC, upper()
title  : tbox(0.6, 0.66, 12.2, 1.0) → 25pt bold INK
accent : box(0.62, 1.55, 1.4, 0.045, fill=ACC)   # short blue bar, a signature
```
Title slide instead: title 40pt at y1.8, full-width rule `box(0, 2.72, 13.333,
0.03, ACC)`, 20pt blue subtitle, 16pt mute tagline, author at y6.85.

## Per-slide composition (pick one, keep it flat)
- Bullets slide: 2–4 plain `•` bullets + ONE band with the key line.
- Table slide: one `small_table` (light HDR header) + a short read + ONE band.
- Result slide: a matplotlib chart/diagram + a text column + ONE band + footnote.
- One band per slide, vertically centered, light fill. One emphasized phrase max.

## Figures (matplotlib, deck-1 style)
- rcParams: font.size 13, no top/right spines, edge `#9ca3af`, text INK, dpi 200.
- Token strips: labeled chips (light code fill, blue marker fill), captions in MUTE
  italic. Charts: markers, colored lines, end-labels only where they don't collide,
  legend OR end-labels (not both crowding).
- Confusion matrix: TP/TN green, FP/FN red; legend below, not on the axis labels.
- Keep placed width ≤ 12.2 in (else it runs off the right margin).

## Recurring review misses (pre-empt these, see SKILL.md for detail)
1. Accent bar missing / full-bleed when it should be short (short on content
   slides, full-width only on the title).
2. Em-dashes in text. → colons/commas/periods.
3. Over-emphasis (many bold/colored spans) → flatten to one per slide.
4. Wide figure past the right margin (check left+width ≤ 12.9).
5. No padding between a table and the bullets under it (≥0.2 in).
6. Band/footnote overlap; dead vertical bands.
7. Wrong data provenance; within-noise deltas sold as wins.
8. Failed-method detail advertised; over-specified recipe trivia.

## Design grammar (academic, not corporate)

- **Header** is a small ALL-CAPS blue kicker, a 25pt bold navy title, and a SHORT
  blue accent bar under it (`box(0.62, 1.55, 1.4, 0.045)`). The accent bar is a
  signature; do not omit it. The title slide uses a full-width thin rule instead.
- **Bullets are plain**, not boxed. One text block with a bullet prefix.
- **At most one light band per slide**, and only when the slide has a real takeaway
  worth emphasizing: light gray (`#F3F4F6`) or cream (`#FBF7F0`) fill, NO saturated
  fill, usually NO colored border. Vertically centered text.
- **A band is NOT required furniture.** Do not end every slide with one. A concept,
  setup, or definition slide that is complete on its own ends with whitespace. If a
  band appears on every slide, the emphasis is uniform and nothing is emphasized;
  bands only read as "this is the conclusion" when they are rare. Before adding one,
  ask: is there one sentence the audience should carry out of this slide, and does
  it say something the bullets do not already say? If not, leave it out.
- **Results use a diagram or chart**, not a giant hero number. Numbers go inline,
  bold, inside the band or the chart.
- **Color only in borders and emphasized words.**
- Font: whatever the reference's runs use. The dominant run font wins over the theme
  default. Here it is Roboto.

## Layout pre-flight, house numbers

These are this instance's constants. On any other reference, read them from that
deck's tokens instead.

- Slide 13.333 x 7.5 in. Content margins x from 0.7 to 12.63, body y from 1.75 to 6.9.
- Wide figures overflow the right edge. Compute placed width as height times the
  aspect ratio, and keep left plus width at or under 12.9.
- A table's bottom must not touch the next bullets. Leave at least 0.2 in.
- Bullets below a figure get the full content width, 11.93, not the left column's.
- Confusion matrix: correct cells green, error cells red, with the metric formulas
  in small type.
