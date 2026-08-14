# Design system (PRE-DECIDED — use directly, do not re-extract)

This is the fixed design for the anywhere-think talk decks, matching deck 1
(ICE/experiments/thinking_distance/slides/build_deck2.py → Intro.pptx). For a NEW
deck in this line, use these values as-is; only re-extract if you are matching a
DIFFERENT reference presentation. `scripts/example_deck_grammar.py` encodes all of
this in working code — copy its helpers.

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
- Subtitle (title slide): **20** bold ACC (one line — shorten text to fit).
- Body / bullets: **14–17**. In-slide subhead: 15–16 bold.
- Band text: **15–18**. Table cells: **13–14**. Footnote: **11–12**.
- Avoid hero numbers > ~24; put numbers inline-bold in a band or chart instead.

## Header (every content slide)
```
kicker : tbox(0.6, 0.33, 12, 0.4)  → 13pt bold ACC, upper()
title  : tbox(0.6, 0.66, 12.2, 1.0) → 25pt bold INK
accent : box(0.62, 1.55, 1.4, 0.045, fill=ACC)   # short blue bar — signature
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

## Recurring review misses (pre-empt these — see SKILL.md for detail)
1. Accent bar missing / full-bleed when it should be short (short on content
   slides, full-width only on the title).
2. Em-dashes in text. → colons/commas/periods.
3. Over-emphasis (many bold/colored spans) → flatten to one per slide.
4. Wide figure past the right margin (check left+width ≤ 12.9).
5. No padding between a table and the bullets under it (≥0.2 in).
6. Band/footnote overlap; dead vertical bands.
7. Wrong data provenance; within-noise deltas sold as wins.
8. Failed-method detail advertised; over-specified recipe trivia.
