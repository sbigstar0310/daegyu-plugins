# Presenting someone else's paper

A paper talk is not a results deck. The audience is judging the paper, and the
first question will be about something the paper did not say. Read this alongside
`evidence-rules.md`.

## Before you build the narrative

**Read the PDF, not a summary of it.** A prior chat, an abstract, or your own
earlier notes are not verified. In one session the working critique claimed the
paper had no ablation. It had one, in a table, and presenting that claim would have
been an instant credibility loss in front of the authors' own field.

**Verify every headline number against the full text**, and keep the verified set
somewhere you can grep. Numbers carried across a context compaction are the ones
that go wrong.

## Structure that works for a 15 minute slot

Background, then the problem, then the formal problem definition, then the method,
then the experiment, then the result, then the ablation, then the limitation, then
discussion. Background exists for the audience, not for the paper: two slides that
make the rest legible.

Time it with the speaker notes. About 150 words per minute at a normal pace, 130 if
the presenter is careful. A 2,600 word script is a 17 minute talk and will not fit.

## Figures and tables

**Lift the paper's own figures and tables rather than redrawing them.** Presenters
ask for this by name, and a redrawn table invites "is that what the paper says?".

```
python3 scripts/paper_assets.py pages paper.pdf                 # aim by eye
python3 scripts/paper_assets.py find  paper.pdf "Figure 1" "Table 8:"
python3 scripts/paper_assets.py crop  paper.pdf 3 95 112 520 366 ref/crops/fig1.png
```

- Crop the body only, not the paper's caption. Its font will not match the deck.
  Write your own caption line under the image.
- **Never desaturate a paper figure.** If colour carries meaning, a green success
  path or a red failure edge, greyscaling it deletes what the talk points at. Embed
  crops as is, even in a monochrome deck. If a review agent harmonises the palette
  by converting images to greyscale, revert it.
- Crop only what a slide will use.

**The overview figure is the exception.** A paper's Figure 1 is drawn for a reader
with unlimited time. For the slide that carries the architecture, draw a simpler
abstract version in native shapes, then show the paper's own figure once, for a
concrete walkthrough. Do not put the same figure on three consecutive slides.

**Annotating a figure.** Numbered callouts must land on empty ink, not on the
figure's own labels. Measure instead of guessing:

```
python3 scripts/paper_assets.py probe ref/crops/fig1.png 0.295 0.365   # arrow midpoints
python3 scripts/paper_assets.py empty ref/crops/fig1.png 0.11 0.15 0.085 0.125
```

Place the badge at a measured arrow midpoint or in a verified empty band, and leave
a comment naming the edge it marks. Guessing from a thumbnail took four rounds and
still covered labels; measuring took one.

Draw the badges as images, never as a digit inside an oval autoshape: vertical
centring of a run inside a shape differs between LibreOffice and PowerPoint, so the
render lies to you.

```
python3 scripts/paper_assets.py badges build/badges 7 ~/Library/Fonts/Inter-Bold.otf
```

## Formulas

Typeset them, do not retype them. Mathematical symbols in a body font look wrong
beside a cropped figure from the same paper.

```
python3 scripts/paper_assets.py eq  '\mathsf{Complete} \iff \mathsf{RepoValid}(R^{*})' build/eq/complete.png
python3 scripts/paper_assets.py sym 'q' build/eq/sym_q.png
```

- BasicTeX ships no `standalone.cls`. Use the `article` class with a wide
  `\textwidth`, `\pagestyle{empty}`, and trim on the alpha channel.
- `pdflatex` is not on PATH on macOS. It lives at `/Library/TeX/texbin/pdflatex`.
- For a symbol legend, wrap each symbol in `\vphantom{\mathcal{Z}^{*}}` so they
  share a height and the rows line up.
- A `cases` block is the compact way to put two end states on one line.

## What the paper does not show

Give it its own slide, and be specific to this paper. Unspecified method details, a
missing baseline, no released code, a component that is never ablated. Name what is
absent, not what you dislike.

## Discussion questions

A question that could be asked of any paper is filler. A good one puts two of the
paper's own results against each other, and has no settled answer.

- Weak: is this scalable?
- Strong: the ablation removes diagnosis, repair, re-planning and retries at once;
  the first try passes 18 of 140 and the budget allows 20 tries, so about 21
  independent tries would already reach 94 percent against the reported 95. Which
  is it?

Offer two or three defensible positions so the room can take sides, and cite the
outside work that makes the question live. Keep your own answer in the notes until
they have chosen.

## The appendix

Hide it rather than cutting it. After the last visible slide, add a divider and the
backup slides, then hide them so they are excluded from the slideshow and the PDF
but reachable by typing the slide number. Say in the Q&A sheet which one you expect
to need.

## The Q&A sheet

`qa-prep.md`: the likely questions, a short answer each, and the slide number to
jump to. If the talk is not in the presenter's first language, add a few stock
phrases for buying a second: "That is a good question. The paper does not say. My
reading is ..."
