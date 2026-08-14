# Layout scoring rubric (best-of-N)

Each candidate slide spec is scored 0–5 per criterion; total /30. Highest total
wins; ties broken by (1) overflow-safety then (2) hierarchy. A candidate that
fails to render, overflows the canvas, or overlaps elements is disqualified
(score 0) regardless of other merits.

| # | Criterion | 5 = excellent | 0 = fails |
|---|-----------|---------------|-----------|
| 1 | **Design alignment** | Roboto, on-brand palette (navy ink, blue accent, red/green only for +/−), eyebrow+title skeleton intact | off-brand colors, wrong emphasis, broken skeleton |
| 2 | **Hierarchy & focus** | one clear focal point (hero/table/key line); eye lands there first | flat wall of text, no focal point |
| 3 | **Information fidelity** | every required fact/number present and correct, nothing invented | drops a number, alters a value, adds unsupported claims |
| 4 | **Spacing & balance** | content uses the vertical space well; no big dead zones, no cramming; margins respected | large empty band OR cramped/touching elements |
| 5 | **Readability** | body ≥13pt, lines wrap cleanly, ≤~6 bullets, short lines | tiny text, run-on lines, >7 bullets |
| 6 | **Restraint** | says one thing well; no redundant callouts; matches deck-1 density (~1 table OR 3–5 bullets, +1 callout) | over-info, duplicate messages, 3+ stacked callouts |

## Notes for judging
- The reference is deck 1 (docs/ppt/Intro.pptx): clean, one idea per slide, a
  hero number or tight table on result slides, minimal prose. Score against that.
- Criterion 3 is a HARD gate for result slides — verify each number against
  `content.py`. A prettier slide with a wrong number loses to a plainer correct one.
- Prefer candidates that fill the 1.75→6.9in body band without dead zones
  (a common baseline weakness) — but never by inventing content or shrinking text.
- Overflow check: does any text block or table extend past y≈7.0in or x≈12.9in?
  If yes → disqualify.
