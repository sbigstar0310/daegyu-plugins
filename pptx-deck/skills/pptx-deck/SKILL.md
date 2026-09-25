---
name: pptx-deck
description: Build a .pptx talk deck that matches a reference deck, verify it with real renders, and ship the speaker notes and rehearsal script with it. Use when asked to make, continue, or fix a slide deck, including a paper presentation. Encodes hard-won review feedback so the FIRST draft already avoids the usual misses.
---

# pptx-deck

Produces a `.pptx` that matches a reference deck, plus the artifacts a talk
actually needs: real PNG renders, speaker notes, a rehearsal script, a Q&A sheet.

**The method here is design-system-agnostic.** The density budget, the writing
rules, the emphasis rule, the verification loop and the geometry checks do not
belong to one look. A design system supplies parameters: canvas, margins and grid,
font files, a palette with roles, a type scale with roles, an emphasis mechanism,
table and figure styling, and a list of what the deck never does. Those live in ONE
importable file per deck, `tokens.py`, and nowhere else.

`DESIGN_SYSTEM.md` and `scripts/design.py` are the **reference instance** of that
contract, the anywhere-think house style. They are an example, not the default.

---

## 0. Before any slide code: decide, gate, preflight

### 0.1 Which design system is this deck in

Say it out loud in your first reply. There are three cases.

- **The user hands you a reference deck.** It outranks everything bundled here,
  including `DESIGN_SYSTEM.md` and `rubric.md`. Go to section 1.
- **The user asks you to find a design, or says nothing about design.** Ask once, in
  one line: do you have a reference deck, or should I use the bundled default? The
  bundled default is `assets/tokens_white.py`, a white, monochrome, typographic
  deck. Searching the web for articles about slide design and calling that a
  reference is the failure this rule exists to stop. It cost a whole first draft.
- **This deck continues an existing line and nobody said otherwise.** Then
  `DESIGN_SYSTEM.md` is your spec and `scripts/example_deck_grammar.py` is your
  starting point. Do not re-extract anything.

### 0.2 Stage gates: content, then design, then build

Three gates. Each needs an explicit yes. Silence is not a yes.

1. **Content.** Slide-by-slide text in a `content.md` the user can read in one
   scroll. Nothing is built until they say so.
2. **Design.** Two sample slides in the chosen system, one text-heavy and one
   figure-heavy. Nothing else is built until they say so.
3. **Build.** Only now write the generator.

**Never default an identity fact.** The presenter's name and its romanization,
their affiliation as they write it, the date, the course, the venue: ask these in
one short block of their own before gate 1 closes, and block the build on them.
Getting the presenter's own name wrong on slide 1 costs more trust than every
layout bug in the deck combined.

**Unanswered questions are not approvals.** If you asked and got no reply, ask
again in one line, or do the part that does not depend on the answer. Building on a
default because nobody answered is how a whole draft gets thrown away.

### 0.3 Preflight: check what this deck will need

Run `python3 scripts/preflight.py` and ask for the missing pieces once, in a single
message. Do not ask for things this deck will not use.

| Need | Missing means |
|---|---|
| LibreOffice | No real renders. `brew install --cask libreoffice`. The bundled previewer uses a proxy font and cannot tell you where a line breaks |
| The deck's font, visible to LibreOffice | Silent substitution, so every line break you check is fiction |
| `claude-image-generation` plugin | No generated art. `/plugin marketplace add hex/claude-marketplace`, then `/plugin install claude-image-generation` |
| An image key | Same. Test one cheap generation before promising art on any slide |
| BasicTeX | No typeset formulas. `brew install --cask basictex`. Only if the deck needs maths |

---

## 1. Extract the reference into tokens

```
python3 scripts/extract_ref.py <ref.pptx> --out <deckdir>
```

It writes `<deckdir>/tokens.py` and renders every reference slide to
`<deckdir>/ref/preview/`. It reads **runs**, not the theme: authors override per
run, so the theme XML lies.

Then do the half a machine cannot. Open eight to twelve of those renders and fill
in the three fields the script leaves as `TODO`. These are what actually get a deck
accepted.

- `EMPHASIS`: how does this deck emphasise? Weight, size, a marker highlight, a
  colour? If you miss this you will reach for a coloured band and be wrong.
- `FORBIDDEN`: what does the reference never do? No accent colour, no bands, no
  rounded corners, no shadows, no table header fill. This list is more load-bearing
  than the palette.
- `ARCHETYPES`: for each recurring layout, a name, the source slide number, and the
  real coordinates. Lift the numbers from the extraction, do not eyeball them.

Also record `FONT_FILES`, the real `.otf` or `.ttf` paths. The typesetting checks
cannot run without them.

Matching fonts and colours but not the visual grammar is the classic failure. It
ships a corporate deck the user rejects.

If the reference has a source builder, reuse its helpers and palette verbatim. That
is the best alignment, and it is rare: a reference the user downloaded has no
builder. Do not spend long looking.

---

## 2. Build: one builder, one tokens file, shared helpers

```
cp scripts/deck_lib.py <deckdir>/
# write build() in <deckdir>/build_deck.py, importing tokens and deck_lib
python3 <deckdir>/build_deck.py
```

`scripts/deck_lib.py` holds the design-agnostic mechanics, which is to say the
places python-pptx has no answer: inline highlight runs, hanging-indent bullets,
pictures that return the size they were actually placed at, per-side table borders,
shapes with the theme style stripped, speaker notes, hidden slides, page numbers.
It contains no coordinates and no palette. It takes your tokens.

Every layout number in `build()` comes from `tokens.py` or from an `ARCHETYPES`
entry. A raw coordinate that is not derived from a token is a bug the next reader,
human or agent, cannot see.

The spec renderer in `scripts/render.py` is the alternative path for decks in the
house line. See `scripts/SCHEMA.md` for what it can and cannot express.

---

## 3. Verify on a real render, never on a proxy

```
python3 scripts/render_real.py deck.pptx --out render/     # LibreOffice, then PNG
python3 scripts/check_layout.py deck.pptx --tokens tokens.py
```

`scripts/render_preview_faithful.py` is for triage while you are still typing
coordinates, and for studying a reference. It draws real pptx coordinates, so trust
positions, overlap and margins. It uses a proxy font, so it cannot tell you where a
line breaks, and it ignores vertical anchor.

**Do not tell the user a slide is fine on the strength of it.** Every claim you
make about a layout comes from a real render of the real file. You will be asked,
twice, whether you actually looked.

**Look at two zoom levels.** A 120 dpi contact sheet for the deck, and a 200 dpi
single-slide PNG for every slide you touched this round. The contact sheet is where
caption overlaps hide.

**Then check the geometry in code, because your eyes miss 0.05 in.**
`check_layout.py` reports:

- **Measured text height against the frame.** A declared box height is decorative.
  A takeaway declared `h=0.3` that wraps to two lines has a true bottom 0.1 in
  lower, and a bounding-box audit will call that slide clean while it collides with
  the footnote.
- **Measured line width against the frame**, so you learn a caption wraps before
  you render it.
- **Partial overlaps only.** Most overlaps in a good deck are deliberate. Ignore
  intersections under 0.02 in, treat full containment as an annotation (a badge on
  a figure, an icon in a table cell, text inside a card), and flag the rest. Name
  deliberate shapes `allow:<reason>` in the builder so the exemption survives slide
  reordering.
- **Table rows that grow.** A cell that wraps one line further makes PowerPoint
  grow the row and pushes everything below the table down.
- **Bounds** from the deck's own tokens, a **dead-band** report, **orphan last
  lines**, and a lint for em-dashes and middle dots in the slides and the notes.

**A picture's placed height is not what you assumed.** `pic()` returns the size it
used. Anchor the caption to that (`y + h + CAPTION_GAP`), never to a literal.
Trimming or regenerating art changes its aspect ratio, and the caption lands on the
figure.

**Re-check after a hand edit.** A deck finished by hand in PowerPoint never runs
the builder again, so builder-side fixes stop applying. Run the checks on the file.

---

## 4. Standing rules

The user will state global rules once and expect them forever. Write them into the
project (a `RULES` block in `tokens.py` or `content.md`), re-apply them on every
build, and re-check them after any hand edit.

These four came from real decks and hold everywhere.

**Match the language to the presenter, not to the topic.** Ask whether they are
presenting in their first language, and believe the answer. For a non-native
presenter: short sentences, common words, one idea per sentence, no idioms, no
clauses stacked two deep. This binds harder on the speaker notes than on the
slides, because those are said out loud. A word the presenter cannot pronounce is
worse than a word the audience does not know. `check_layout.py --lang-check`
reports the longest sentence on each slide and in its notes when it runs past 20
words (`--max-words` to change it), as warnings you can wave off. No script judges
the words themselves: read for them. If the presenter hand-edits slides
themselves, proofread and offer corrections as a list they can reject.

**No em-dashes and no middle dots.** Both read as machine-written. Use colons,
commas, periods, parentheses, or a vertical bar. This applies to separators,
captions, metadata lines, table corner cells and the author line.

**No dangling last line.** A line holding one or two words reads as broken in every
design system, and it is the most repeated review complaint on record. Fix it in
this order: **cut the text, then shrink the font a little, then adjust the box.**
Do not hunt for these by eye. `scripts/fix_orphans.py` measures with the real font
metrics and reports what is left.

**Every slide gets a picture or icons.** See section 5. A correct, well-spaced,
text-only slide still gets rejected.

**Vocabulary belongs to the user.** When they rename something, rename it
everywhere at once: slides, speaker notes, the Q&A sheet, the slide-number map.
Freeze one term per concept, take it from the source where one exists, and grep for
the competing terms rather than fixing only the two slides they named.

---

## 5. Every slide gets a picture or icons

Build the visual first and lay the text around it, not the reverse.

**Icons, in order of cost.** The plugin ships about thirty Lucide icons and eight
brand logos already rendered, plus searchable indexes of 1,820 Lucide icons and
3,459 brands, so search works offline.

```
python3 scripts/icons.py search "retry"                  # concept to candidate names
python3 scripts/icons.py sheet refresh-cw rotate-cw --out cand.png   # look, then pick
python3 scripts/icons.py add refresh-cw                  # fetch, recolour, render
python3 scripts/icons.py logo docker                     # brand logos
```

Choosing an icon from a name alone is guessing. Render the candidates to one sheet
and look. Place icons as images, never as autoshapes, and render at 1200 dpi with
alpha: at a placed size of 0.2 to 0.3 in, anything lower goes soft through the pptx
to PDF to PNG round trip. Cap a logo row at about five, and only logos the
presenter can talk about.

**Generated line art** when no icon or source figure fits. Use the image plugin,
one generation per call, two or three candidates per slot. Keep a fixed preamble
and coda so the set looks like one set:

> Minimal black line-art illustration on a pure white background. Thin, uniform
> black strokes only. No text, no letters, no labels, no numbers, no colour, no
> shading, no grey fills. Wide composition, centred, generous white margins.
> Subject: one sentence naming every element and where it sits. Nothing else in the
> picture. Style like a Lucide icon set drawing: geometric, precise, consistent
> stroke width, nothing hand-drawn.

Vary only the subject. Keep originals and always trim from them, so trimming is
idempotent, then re-measure: the aspect ratio changed.

**Native shapes** for diagrams the user may want to edit, and for anything that
must stay crisp at projector zoom.

---

## 6. Density, emphasis, structure

### Density budget (the most common rejection)

Ask which direction this presenter is in before the first build, and write the
answer into the project.

- **Key sentences only.** One takeaway per slide, detail in the notes. Then the
  caps below apply.
- **The full argument on the slide**, because the presenter reads along with the
  audience. Common when presenting in a second language. Then the caps do not
  apply. What applies instead: no dangling lines, even vertical rhythm, one
  emphasised phrase per slide.

Budget every slide BEFORE writing it, and cut to fit rather than shrinking type.

- **Three content blocks per slide, hard cap.** A block is one figure, OR one
  table, OR the bullet group, OR the band. Header and page furniture do not count.
  A fourth block is over budget: drop one.
- **At most 3 bullets, one printed line each.** Measure it with the real font
  metrics at your body token, do not guess a character count: it is canvas and font
  specific. If it wraps, it is two bullets' worth of content. Cut it, do not shrink
  the font. Two strong bullets beat three padded ones.
- **At most one footnote, one line.** If a slide needs a caption above a table AND
  a footnote below it, it is over budget: fold the caption into the table's corner
  cell and delete the footnote.
- **Body type at the reference's body token.** The minimum in your tokens is a
  floor, not a budget. Dropping below it to fit more text is the failure mode
  itself. Small scattered text is what reads as noisy.
- **Numbers live in ONE place per slide.** If the chart labels carry the numbers,
  the bullet says which one wins, not the numbers again.
- Caveats, protocol notes, standard error, anchors, n: pick the ONE the audience
  needs to judge the claim. The rest is for the live Q&A.

### FLAT emphasis (the do not scatter rule)

Emphasize only the ONE thing each slide must convey; leave everything else plain
ink. Too many bold or coloured spans reads as scattered. Across a whole deck, only
a couple of emphasised phrases total. Reserve any status colour for a genuine
positive or negative.

### Slide structure (bullets must not be a flat pile)

A list of true but unrelated one-liners is the most common structural rejection.
Every bullet block needs a spine.

- **Group them**, either with short section labels near body size (a small grey
  label reads as a caption and gets ignored) or with bold lead-ins inside the
  bullet. Lead-ins cost no vertical space; use them when the slide is tight.
- **Or order them as a narrative**: symptom, cause, worst case, so the closing line
  reads as the conclusion that follows.
- **Never encode the same split twice.** If the table already has two columns,
  do not also add two headings above the bullets.
- **A claim on a slide needs its evidence on the same slide.** "Coding is intact"
  is an assertion; the table showing the column flat is the proof. Prefer lifting
  the real table over paraphrasing it.

### Diagram legibility

- **One shape per unit, never repeated punctuation.** Four dots cannot be counted
  at a glance; four outlined squares can. Add a dashed reference line at the
  correct value so the broken case visibly overshoots it.
- **Draw the prerequisite.** If reading panel B requires knowing how the system
  works, spend a small left panel showing exactly that, then let panel B assume it.
- **Collapse categories to the axis of the claim.** If the point is "lines with a
  marker break more", show 2 bars, not 3. Recompute the merged rate from the raw
  counts; do not average percentages.
- Grey out anything the deck is not arguing.

---

## 7. Evidence rules, when the deck argues from numbers

If any slide carries a number you are arguing from, read
`references/evidence-rules.md` before you build it. It covers one regime per
comparison, provenance for every number, and the verification discipline that a
supervisor attacks first. For someone else's paper, read
`references/paper-talk.md` too.

## 8. Working with the human

### The page-by-page phase is the body of the work

After the first full draft, expect fifty turns of small per-slide edits. Keep one
generator, apply the edit, rebuild, render only what changed at 200 dpi, re-check
geometry, and report in one or two lines. Identify slides by their printed number
and title, and update your own slide map whenever a slide moves, splits or merges,
because the next request will use the new numbers.

### When the user edits the deck by hand

The generator rewrites `deck.pptx` from scratch, so a hand edit dies at the next
build. The moment they say they are going to edit it:

1. **Snapshot first, before they ask.** Copy the deck and the builder into
   `backup/<timestamp>/`.
2. **Stop building.** Say so explicitly.
3. **On return, diff before anything else**: shapes, text, notes, hidden flags,
   highlights, current against the snapshot. Report which slides changed.
4. **Port their changes into the builder**, then rebuild and diff the text again to
   prove nothing else moved.
5. Tell them what PowerPoint will not maintain: **hidden-slide flags** and **page
   numbers**, both baked rather than computed. After a manual reorder, re-derive
   the visible numbering and strip numbers from hidden slides.

**PowerPoint holds the file while it is open.** A `~$deck.pptx` in the folder means
an open handle. If the user cannot save, or your extraction is missing their latest
edit, compare the file's mtime against PowerPoint's autorecover copy. If
autorecover is newer, their work is not on disk: ask for a save, do not guess, and
do not report stale content as current.

### Freeze

When the user says the deck is final: back up, port their last hand edits into the
builder, and **change the generator's output path** so a later run cannot overwrite
the deck. A warning comment is not a freeze. After that, generate only derived
artifacts.

---

## 9. Delegating to another agent

**Ask which agent, and default to the one the user already pays for.** In practice
the request is explicit. A fan-out you chose yourself is slower and more expensive
than the tool they named.

**One writer at a time.** While a delegate holds the builder, do not edit it and do
not start a second job against it. Queue incoming feedback, or apply it as anchored
patches that assert their anchor matches exactly once, so a collision fails loudly
instead of clobbering silently. Work that touches no file, such as brainstorming or
checking numbers, can run in parallel.

**Every brief carries invariants, not just a style.** Name what must NOT change:
slide text and speaker notes unchanged, source figures keep their original colours,
do not delete icons or artwork, do not add furniture the deck does not use, keep
the tokens. A brief that says only "keep the reference style, black and white, no
decoration" produces a greyscaled, icon-stripped deck.

**Hand over `tokens.py`, not a prose description of it.**

**A launcher returning is not a job finishing.** A wrapper can report success while
the real work has only started in the background. Confirm from the artifact or the
diff.

**Verify the delegate's output yourself.** Render it for real, diff the text and
shape inventory against the pre-delegation snapshot, and read the code it wrote.
Delegates have greyscaled every embedded image, emitted the same figure on three
consecutive slides, and reported success having changed nothing.

**A geometry claim without coordinates is not evidence.** The delegate's sandbox
may have no renderer. Require it to say so.

**Codex, when available.** If the `openai-codex` plugin is installed, ask once, then
use it for the two things it is good at: an independent verification pass over the
whole deck, and best-of-N layout candidates for one hard slide, returned as patches
against a recorded source hash. Render and pick yourself.

Quota: fan-outs are expensive. When the user flags low quota, do the rewrite and the
geometry fixes yourself.

---

## 10. Deliver

The deck is one of several artifacts. Ask which the talk needs, and keep them in
sync on every build.

- `deck.pptx` and `deck.pdf`, in the project folder beside the reference. Make the
  PDF with `render_real.py --skip-hidden --keep-pdf`, so the appendix stays out.
- `render/`, the contact sheet plus a 200 dpi PNG per slide.
- **Speaker notes inside the pptx**, one block per slide, written as you build.
- **A rehearsal script derived from the notes**, never from the content doc, which
  goes stale the moment a note is edited. Report the word count and the runtime at
  150 and 130 words per minute: that is the only honest fit check for a timed talk.
  Ask the medium before formatting it. Printed wants one sentence per line; a phone
  wants one paragraph per slide.
- `content.md`, the signed-off text, and `qa-prep.md`, likely questions with the
  slide number to jump to.
- `backup/`, a timestamped snapshot before every hand-off and before the freeze.

**Appendix slides are hidden, not deleted.** Call it Appendix, never Backup. Hide
with `slide._element.set("show", "0")`: excluded from the slideshow and from the
exported PDF, still reachable by typing the slide number. `render_real.py` renders
them anyway, so the appendix is checked like any other slide. For the handout PDF,
pass `--skip-hidden --keep-pdf`.

---

## Files

- `DESIGN_SYSTEM.md`, the house instance of the token contract.
- `references/paper-talk.md`, presenting someone else's paper.
- `references/troubleshooting.md`, tool traps that each cost real time.
- `references/instance-white-ref.md`, the bundled white default.
- `references/evidence-rules.md`, what a number on a slide has to satisfy.
- `assets/tokens_white.py` and `assets/starter_build.py`, the default instance.
- `assets/icons/`, `assets/logos/`, `assets/index/`, bundled art and search indexes.
- `scripts/preflight.py`, `extract_ref.py`, `deck_lib.py`, `render_real.py`,
  `check_layout.py`, `fix_orphans.py`, `paper_assets.py`, `icons.py`.
- `scripts/example_deck_grammar.py`, a worked deck in the house grammar.
- `scripts/render.py`, `preview.py`, `render_candidate.py`, `SCHEMA.md`, the spec
  renderer for house-line decks.
- `scripts/render_preview_faithful.py`, the approximate previewer, and
  `scripts/rubric.md`, the scoring rubric.
