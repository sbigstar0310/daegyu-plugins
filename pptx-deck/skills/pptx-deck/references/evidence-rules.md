# Evidence rules: comparisons, provenance, verification

Read this before building any slide that carries a number you are arguing from.
It is the discipline that survives contact with a supervisor. For a talk about
someone else's paper, read `paper-talk.md` as well.

## One regime per comparison, named on the slide

Anything that moves the metric globally (decoding schedule, prompt, batch size,
GPU, harness version) must be IDENTICAL across every cell the audience is invited
to compare, **including the baselines**, and the slide must say which one it is.

- Put the regime in the table's corner cell or the chart title, not in a footnote,
  and never leave it implicit because the whole deck uses it.
- **A missing cell is not permission to borrow a neighbour.** If the base was only
  run under a different schedule, you do not have that comparison: drop the claim,
  or run the cell. Grep the tags behind every number before it ships.
- Cells that genuinely were not run get an explicit `not run` slot, so the hole is
  visible instead of silently filled.

## Numbers must carry provenance

For any analysis or decomposition slide, add a "where the number comes from" column
or an explicit footnote per number. This is what turns "we guessed a split" into
"we decomposed the degradation", and it is what a supervisor attacks first.

- **A residual is not a measurement.** If B is defined as total minus A, then "A
  plus B reproduces the total" is circular, not a validation. Prefer quantities an
  intervention moved, each measured on its own model.
- **Cross-check with an independent route** and show the agreement.
- **The same quantity must not appear twice with different values.** Grep the
  builder for each headline number before shipping.

## Verify, do not assume

- **Data provenance**: state exactly where training data came from versus what the
  eval set is. Getting this wrong is a credibility hit.
- **Distinguish look-alike concepts visually**, and label which is which.
- **Statistical honesty**: never present a within-noise delta as a win. A tie is
  "on par", not "improves". For a surprising result, run an adversarial audit
  before claiming it.
- **Run the test, do not eyeball it.** Per-problem verdicts are usually already on
  disk; pair them and compute the exact test before any delta goes on a slide.
  Verify row alignment with a key that cannot differ between cells, never a field
  the model produced. Report the detectable effect size too, which answers "is it
  noise?" before it is asked. Mark non-significant steps in grey.
- **Verify the mechanism, do not restate the doc.** A written explanation can be
  wrong. Open the raw outputs before putting a causal claim on a slide, and fix the
  doc when it loses.
- **"Refuted" versus "unsupported".** A failed significance test does not disprove
  an effect. Reserve "refuted" for a measurement that came out the other way.
- **Show the whole taxonomy when the headline is only part of it**, otherwise the
  slide over-claims and the first question exposes it.

---

