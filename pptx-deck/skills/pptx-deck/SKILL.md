---
name: pptx-deck
description: Build a polished .pptx talk deck that matches an existing presentation's design. Use when asked to make or continue a slide deck aligned to a prior one. Encodes hard-won review feedback so the FIRST draft already avoids the usual misses.
---

# pptx-deck — design-aligned deck builder

Produces a `.pptx` (+ faithful PNG previews) that visually matches a reference
deck. Two ways to author slides: (a) **adopt the reference's own builder** if one
exists (best alignment), or (b) the data-driven spec renderer in `scripts/`.
No LibreOffice needed — a matplotlib previewer renders the real .pptx coordinates.

## 0. The design system is ALREADY documented — use it directly
For decks in THIS line, do not re-extract anything: **`DESIGN_SYSTEM.md`** holds the
fixed tokens (canvas, Roboto, palette, type scale, the header + accent bar spec,
per-slide composition), and **`scripts/example_deck_grammar.py`** encodes all of it
in working code — copy its helpers (`header`, `box`, `bullets`, `band`, `para`,
`small_table`) and the RGB constants, then just write `build()`.

Only when matching a DIFFERENT reference presentation do you re-extract, and even
then the #1 mistake is matching fonts/colors from the theme XML but NOT the visual
grammar, which ships a "corporate" deck the user rejects. In that case:
1. Find the reference `.pptx` AND its source builder if one exists (search
   adjacent repos for `python-pptx`, `.pptx`, `render_preview`).
2. **Render the reference to images and study it** with
   `scripts/render_preview_faithful.py <ref.pptx>` (real shape/table coords): boxes
   per slide, fill saturation, whitespace, where color lives, hero vs. table.
3. If it has a builder, reuse its helpers and palette verbatim, then update
   `DESIGN_SYSTEM.md` with the new tokens.

## Design grammar (academic, NOT corporate) — the target
- **Header** = small ALL-CAPS blue kicker + 25pt bold navy title + a SHORT blue
  accent bar under it (`box(0.62, 1.55, 1.4, 0.045)`). The accent bar is a
  signature; don't omit it. Title slide uses a full-width thin rule instead.
- **Bullets are plain** (not boxed). One text block, `•` prefix.
- **One light band per slide** carries the key line: light gray (`#F3F4F6`) or
  cream (`#FBF7F0`) fill, NO saturated fill, usually NO colored border. Vertically
  centered text.
- **Results use a diagram or chart**, not a giant hero number. Numbers go inline,
  bold, inside the band or the chart.
- **Color only in borders and emphasized words.** Palette: ink `#1A2332`, blue
  `#2563EB`, gray `#5B6372`, green `#059669`, red `#DC2626`.
- Font: whatever the reference's *runs* use (check `grep typeface slides/*.xml` —
  the dominant run font wins over the theme default). Here it was **Roboto**.

## Density budget (the #1 rejection: "내용이 너무 많다 / 산만하다")
The presenter has rejected drafts for density more than for anything else. Budget
every slide BEFORE writing it, and cut to fit rather than shrinking type.

- **Three content blocks per slide, hard cap.** A block = one figure, OR one
  table, OR the bullet group, OR the band. Header and page furniture do not count.
  A fourth block (figure AND table AND bullets AND band) is over budget: drop one.
- **At most 3 bullets, one printed line each.** ~85 characters at 15-16pt across
  the full content width. If it wraps, it is two bullets' worth of content: cut it,
  do not shrink the font. Two strong bullets beat three padded ones.
- **At most one footnote, one line.** If a slide needs a caption line above a
  table AND a footnote below it, it is over budget: fold the caption into the
  table's corner cell (`HumanEval ep6 · 164 problems`) and delete the footnote.
- **Body type 15-17pt, not 13.** Dropping to 13.5pt to fit more text is the
  failure mode itself. Small scattered text is what reads as noisy.
- **Numbers live in ONE place per slide.** If the chart labels say `+7.8 (46.7)`,
  the bullet says "MBPP gains the most", not the numbers again.
- Caveats, protocol notes, SE, anchors, n: pick the ONE that the audience needs to
  judge the claim. The rest is for the live Q&A, not the slide.

## FLAT emphasis (the "don't scatter" rule)
Emphasize only the ONE thing each slide must convey; leave everything else plain
ink. Too many bold/colored spans reads as "scattered." Across a whole deck, only a
couple of blue phrases total. No red/green except a tiny result check or a genuine
negative. Bands: plain text with at most one bold phrase.

## Writing style
- **No em-dashes (`—`).** They read as AI-generated. Use colons, commas, periods,
  or parentheses.
- Short declarative sentences. Bullet points over prose. Cut filler.
- **Reduce detail on failed methods** — don't advertise an analysis that didn't
  work (mention it only if the user asks live).
- Simplify over-specified recipes ("1/t reweighted, per-sample normalized" →
  "follows the standard SFT recipe"); drop trivia (e.g. "0.52% of params").
- **Never reference another deck from a slide** ("deck 2", "as in the previous
  deck", "n = 164, deck 2"). The audience sees one deck at a time. Reuse the
  earlier deck's *content*, never a pointer to it; rename its row labels into this
  deck's vocabulary (`SFT ep10` → `v1 ep10`).
- **Footnotes are load-bearing or deleted.** Keep only what the slide cannot be
  read without (e.g. "( ) = markers per problem"). `n = 164` belongs in the table
  header, not a footnote. Method reminders the audience already heard: cut.
- **Don't advertise undecided work.** A candidate/next-steps table lists what is
  verified and what runs next. Options still under discussion, and rejected ones,
  stay off the slide.

## Slide structure (bullets must not be a flat pile)
A list of true-but-unrelated one-liners is the most common rejection ("말이 너무
따로 노는 것 같다"). Every bullet block needs a spine:
- **Group them**, either with short section labels (13.5pt bold ink, near body
  size — a small grey label reads as a caption and gets ignored) or with bold
  lead-ins inside the bullet (`**Delivered**: ...` / `**Cost**: ...`). Lead-ins
  cost no vertical space; use them when the slide is tight.
- **Or order them as a narrative**: symptom → cause → worst case, so the band
  reads as the conclusion that follows.
- **Never encode the same split twice.** If the table already has `plain` and
  `marker` columns, don't also add DELIVERED / COST headings above the bullets.
- **A claim on a slide needs its evidence on the same slide.** "Coding is intact"
  is an assertion; the two-column table showing the plain column flat is the
  proof. Prefer lifting the earlier deck's real table (same columns, row order,
  and number formatting) over paraphrasing it.

## One regime per comparison, named on the slide
Anything that moves the metric globally (decoding schedule, prompt, batch size,
GPU, harness version) must be IDENTICAL across every cell the audience is invited
to compare, **including the baselines**, and the slide must say which one it is.
- Put the regime in the table's corner cell or the chart title
  (`HumanEval ep6 · 164 problems · factor decoding f = 0.3`), not in a footnote,
  and never leave it implicit because "the whole deck uses it".
- **A missing cell is not permission to borrow a neighbour.** If the base was only
  run under a different schedule, you do not have that comparison: drop the claim
  (or run the cell). Mixing `base @ sequential` with `model @ factor` invents a
  result. Grep the tags behind every number and check the suffix before it ships.
- Cells that genuinely were not run get an explicit `not run` slot, so the hole is
  visible instead of silently filled.

## Numbers must carry provenance
For any analysis/decomposition slide, add a "where the number comes from" column
or an explicit footnote per number. This is what turns "we guessed a split" into
"we decomposed the degradation," and it is what a supervisor attacks first.
- **A residual is not a measurement.** If B is defined as (total − A), then
  "A + B reproduces the total" is circular, not a validation. Say so, or replace
  it: prefer quantities that an *intervention moved*, each measured on its own
  model, over quantities obtained by subtraction and carried across models.
- **Cross-check with an independent route** and show the agreement (hand-reading
  20 problems = 12.2 pts vs a decoding ablation removing 11.6 pts).
- **The same quantity must not appear twice with different values.** Grep the
  builder for each headline number before shipping; one slide saying "55%" while
  another says "71%" about the same split is an instant credibility loss.

## Content correctness (verify, don't assume)
- **Data provenance**: state exactly where training data came from vs. what the
  eval set is. (Here: trained on TA cold-start data, evaluated on MBPP — NOT
  trained on MBPP. Getting this wrong is a credibility hit.)
- **Distinguish look-alike concepts visually** (e.g. inline `<thinkanywhere>`
  markers vs. an up-front `<think>` CoT; make the diagram label which is which).
- **Statistical honesty**: never present a within-noise delta as a win. If SFT
  scores 40.5 vs base 38.5, that is a tie (McNemar p≈0.5) → say "on par / no
  degradation," not "improves." For a surprising result, run an adversarial audit
  agent (opus) to check fair comparison, silent PASS, leakage, and stripping
  no-ops BEFORE claiming it.
- **Run the test, don't eyeball it.** Per-problem verdicts are usually already on
  disk; pair them and compute exact McNemar before any delta goes on a slide.
  Verify row alignment with a per-problem key that cannot differ between cells
  (the ground-truth hash), never a field the model produced (an extracted function
  name differs precisely *because* the models differ). Report the detectable
  effect size too ("this cell only resolves gaps above ~8.5 pts") — that answers
  "is it noise?" before it is asked. Mark non-significant steps in a waterfall in
  grey with `n.s.`, not in the win colour.
- **Verify the mechanism, don't restate the doc.** A written explanation can be
  wrong: our notes said no-code rose from canvas truncation, but the generations
  showed the code started at the same offset and simply lost its markdown fence.
  Open the raw outputs before putting a causal claim on a slide, and fix the doc
  when it loses.
- **"Refuted" vs "unsupported".** A failed significance test does not disprove an
  effect. Say the claim is unsupported at this n; reserve "refuted" for a
  measurement that came out the other way.
- **Show the whole taxonomy when the headline is only part of it.** If the
  mechanism you explain covers 11 of 20 damaged cases, put all four categories on
  the slide with examples of the other nine; otherwise the slide over-claims and
  the first question exposes it.

## Layout / geometry pre-flight (catch before the user does)
Slide 13.333 × 7.5 in. Content margins x ∈ [0.7, 12.63], body y ∈ [1.75, 6.9].
- **Wide figures overflow the right edge.** Compute placed width = height ×
  (fig_w/fig_h); ensure `left + width ≤ 12.9`. A tall skinny slide is fine; a wide
  short figure at full height is not.
- **Padding between blocks.** A table's bottom must not touch the next bullets —
  leave ≥0.2 in. (table_bottom = y + rows×row_h.) Recompute every stacked element.
- **Band vs. footnote**: band_bottom = y + h; the footnote must start below it.
- **Even vertical fill**: no dead band > ~1.2 in; no cramming. Redistribute y's.
- **Legend/label overlap**: two texts at the same (x,y) collide — check figure
  annotations (move legends below the plot, not onto axis labels).
- **Confusion-matrix convention**: correct cells (TP, TN) green; error cells (FP,
  FN) red. Add the metric formulas in small font (precision = TP/(TP+FP), etc.).
- **Bullets below a figure get the full content width** (`width=11.93`), not the
  left column's width. The proxy font wraps earlier than Roboto, so a bullet that
  looks like one line in your head becomes two and lands on the band.

## Diagram legibility
- **One shape per unit, never repeated punctuation.** Rendering four spaces as
  `····` cannot be counted at a glance; four outlined squares can. Add a dashed
  reference line at the correct value so the broken case visibly overshoots it,
  and colour-code which token owns which unit.
- **Draw the prerequisite.** If reading panel B requires knowing how the system
  works (e.g. that diffusion unmasks k positions per step, independently), spend a
  small left panel showing exactly that, then let panel B assume it.
- **Collapse categories to the axis of the claim.** If the point is "lines with a
  marker break more", show 2 bars, not 3 split by marker position. Recompute the
  merged rate from the raw counts (`14+29+45` over `672+459+544`); do not average
  the percentages.
- Grey out anything the deck is not arguing (a future version in a concept
  diagram, a non-significant step in a waterfall).

## Preview caveats (the faithful previewer)
`scripts/render_preview_faithful.py` draws real pptx coords, so trust
positions/overlap/margins. But: it uses a proxy font (not the real one), its text
wrap is approximate (don't nitpick line breaks), and it **ignores vertical anchor**
— band text that looks "stuck to the top" is actually centered in PowerPoint.
Tables ARE rendered (this copy adds that; the stock ICE version does not).

**It ignores `--out`**: PNGs land in the *script's own directory*. Pass an absolute
pptx path, then move them, or you will review a stale render and "fix" bugs that
are already gone:
```
python .claude/skills/pptx-deck/scripts/render_preview_faithful.py /abs/path/deck.pptx
mv .claude/skills/pptx-deck/scripts/preview_*.png <your build dir>/
```

## best-of-N + review (agent teams)
- Generation: for a slide worth exploring, spawn N Fable agents (`model:"fable"`)
  with distinct layout angles, each self-validating its render. Score with
  `scripts/rubric.md`, pick the winner.
- Review: after a draft, spawn one Fable agent PER SLIDE with the faithful render +
  the reference + the builder section; have them REPORT coordinate-level fixes (do
  not let them all edit one file). Apply fixes yourself. Reject preview-artifact
  findings (e.g. "band text hugs top").
- Quota: these fan-outs are expensive. When the user flags low quota, do the flat
  rewrite and geometry fixes yourself instead of spawning a review team.

## Files
- `scripts/example_deck_grammar.py` — worked deck in the academic grammar (header
  with accent bar, plain bullets, one band, matplotlib figures). Copy its helpers.
- `scripts/render_preview_faithful.py` — .pptx → PNG previews (+ tables).
- `scripts/render.py` / `preview.py` / `render_candidate.py` — the alternative
  spec (JSON) renderer + its overflow-guard validator.
- `scripts/SCHEMA.md`, `scripts/rubric.md` — the spec format + the scoring rubric.

## Deliver
Send the `.pptx` and a preview PNG. Put the final deck next to the reference (same
`docs/ppt/` dir), not in a build folder.
