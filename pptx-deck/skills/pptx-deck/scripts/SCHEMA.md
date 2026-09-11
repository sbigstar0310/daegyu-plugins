# Slide-spec schema (what the renderer draws)

**Scope. This schema belongs to one instance: the 13.333 x 7.5 in house deck with
the blue accent, described in `DESIGN_SYSTEM.md`.** Its canvas, its palette names
and its type scale are baked in. It is not the general way to build a deck, and it
cannot express a deck with a different canvas or no accent colour.

Use it when you are adding slides to a deck already in that line. For anything
else, write a builder with `scripts/deck_lib.py` and your own tokens: that path
has no fixed canvas, no fixed palette, and is what `extract_ref.py` produces
tokens for.

A slide is a JSON/dict object. `render.py` (to .pptx) and `preview.py` (to .png)
both consume this exact schema, so a layout is fully described by data.
All positions are **inches**; slide is **13.333 x 7.5 in (16:9)**. Omit x/y/w/h
to use sensible defaults.

## Slide skeleton (top-level keys)
- `eyebrow`: str, top-left ALL-CAPS blue label (e.g. `"RESULT / PLACEMENT"`). Omit for title slide.
- `title`: str, 25 pt bold navy. `title_size` to override; `title_runs` for mixed styles; `title_y` (default 0.95).
- `subtitle`: str, 16 pt gray under title. `subtitle_runs` / `subtitle_y` (default 1.55).
- `footnote`: str | list[str], 10 pt gray at slide bottom (citations, eval config).
- `elements`: list[element], the body (see below).
- `notes`: str, speaker notes for this slide. Written to the .pptx notes slide by
  `render.py` and ignored by `preview.py`. Write these as you build, not
  afterwards: the notes are how you time the talk, and a deck whose notes arrive
  last is a deck nobody timed.
- `hidden`: bool, keep the slide in the file but out of the slideshow and out of
  the exported PDF. This is how an appendix is handled: hide it, do not cut it.

## Design tokens (use color NAMES, not hex)
- colors (this instance only): `ink` (navy text), `blue` (primary accent), `gray` (secondary), `green`/`green_dk` (positive), `red` (negative), `line` (hairline), `white`.
- font: Roboto (auto). Set `"mono": true` on a run for code/markers.
- type scale (pt): title 25, eyebrow 13, subtitle 16, body 15, body_sm/table 13, small 12, footnote 10, hero ~40-44.

## A "runs" list = one paragraph, mixed styles
`"runs": [{"text": "61% ", "bold": true}, {"text": "-> 26%", "color": "red", "bold": true}]`
Each run: `text`, `size`, `color`, `bold`, `italic`, `mono`.

## Elements (each has `"type"`)
- **bullets**, `items: [{text|runs, level(0/1), bold, color, bullet, size, gap}]`, plus `x,y,w,size`.
- **textbox**, free text block. `paras: [{runs, size, color, align, gap}]` (or single `runs`), `x,y,w,align`.
- **hero**, big stat. `value` (str, ~44 pt bold), `caption`, `color`, `x,y,w`.
- **callout**, rounded panel. `text` or `runs`, `fill: blue|green|red|light|none`, `bold`, `x,y,w,h`.
- **table**, `header: [...]`, `rows: [[cell,...]]`, `col_w: [in,...]`, `x,y,w,row_h,size`.
  A cell is a str, or `{"text"/"runs", "color", "bold"}` for emphasis. Header row auto = dark navy fill, white bold.
  `bold_cells: ["r,c"]`, `cell_color: {"r,c": color}` for str cells (r counts the header as row 0).
- **cards**, row of labeled panels. `items: [{head, body(str|runs), accent, fill, extra_paras}]`, `x,y,w,h,gap`.
- **line**, hairline separator. `x,y,w,color,weight`.
- **image**, `path,x,y,w,h`.

## Layout guidance (match deck 1)
- One eyebrow + one title per slide; keep the title to one line if possible.
- Body starts ~1.75 in; leave the bottom ~0.6 in for footnotes.
- Emphasis: blue for key/positive points & arrows, red for collapse/negative, green for "yes".
- Prefer a hero number or a tight table over dense prose on a result slide.
- Don't overfill: deck 1 slides carry ~1 table OR ~3-5 bullets OR a card row, not all at once.
