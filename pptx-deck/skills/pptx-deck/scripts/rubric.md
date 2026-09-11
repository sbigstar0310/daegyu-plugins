# Layout scoring rubric (best-of-N)

Each candidate slide spec is scored 0-5 per criterion; total /30. Highest total
wins; ties broken by (1) overflow-safety then (2) hierarchy.

**Disqualification is measured, not judged.** Build the candidate and run

    python3 scripts/check_layout.py candidate.pptx --tokens <your tokens.py>

A non-zero exit disqualifies it, whatever the rest of the scorecard says. Do not
score bounds, overlap, overflow or dangling lines by eye: the checker measures
them against the real font, and a judging agent reading a preview will both miss
real ones and invent ones that are artefacts of the proxy font.

| # | Criterion | 5 = excellent | 0 = fails |
|---|-----------|---------------|-----------|
| 1 | **Design alignment** | Roboto, on-brand palette (navy ink, blue accent, red/green only for +/−), eyebrow+title skeleton intact | off-brand colors, wrong emphasis, broken skeleton |
| 2 | **Hierarchy & focus** | one clear focal point (hero/table/key line); eye lands there first | flat wall of text, no focal point |
| 3 | **Information fidelity** | every required fact/number present and correct, nothing invented | drops a number, alters a value, adds unsupported claims |
| 4 | **Spacing & balance** | content uses the vertical space well; no big dead zones, no cramming; margins respected | large empty band OR cramped/touching elements |
| 5 | **Readability** | body at or above the instance's floor, lines wrap cleanly, ≤~6 bullets, short lines | tiny text, run-on lines, >7 bullets |
| 6 | **Restraint** | says one thing well; no redundant callouts; matches deck-1 density (~1 table OR 3–5 bullets, +1 callout) | over-info, duplicate messages, 3+ stacked callouts |

## Notes for judging
- The reference is deck 1 (docs/ppt/Intro.pptx): clean, one idea per slide, a
  hero number or tight table on result slides, minimal prose. Score against that.
- Criterion 3 is a HARD gate for result slides. Verify each number against
  `content.py`. A prettier slide with a wrong number loses to a plainer correct one.
- Prefer candidates that fill the 1.75→6.9in body band without dead zones
  (a common baseline weakness), but never by inventing content or shrinking text.
- Overflow, bounds, overlap and dangling last lines: `check_layout.py` decides,
  not the judge. Its warnings are advice; its errors are disqualifying.
- Reject findings that are artefacts of the approximate previewer. Band text that
  looks stuck to the top is centred in PowerPoint, and its line breaks are a
  character count, not the font. If a finding is about a line break, it has to
  come from `render_real.py`.
