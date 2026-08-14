# Slide-spec schema (what the renderer draws)

A slide is a JSON/dict object. `render.py` (→ .pptx) and `preview.py` (→ .png)
both consume this exact schema, so a layout is fully described by data.
All positions are **inches**; slide is **13.333 × 7.5 in (16:9)**. Omit x/y/w/h
to use sensible defaults.

## Slide skeleton (top-level keys)
- `eyebrow`: str — top-left ALL-CAPS blue label (e.g. `"RESULT · PLACEMENT"`). Omit for title slide.
- `title`: str — 25 pt bold navy. `title_size` to override; `title_runs` for mixed styles; `title_y` (default 0.95).
- `subtitle`: str — 16 pt gray under title. `subtitle_runs` / `subtitle_y` (default 1.55).
- `footnote`: str | list[str] — 10 pt gray at slide bottom (citations, eval config).
- `elements`: list[element] — the body (see below).

## Design tokens (use color NAMES, not hex)
- colors: `ink` (navy text), `blue` (primary accent), `gray` (secondary), `green`/`green_dk` (positive), `red` (negative), `line` (hairline), `white`.
- font: Roboto (auto). Set `"mono": true` on a run for code/markers.
- type scale (pt): title 25 · eyebrow 13 · subtitle 16 · body 15 · body_sm/table 13 · small 12 · footnote 10 · hero ~40-44.

## A "runs" list = one paragraph, mixed styles
`"runs": [{"text": "61% ", "bold": true}, {"text": "-> 26%", "color": "red", "bold": true}]`
Each run: `text`, `size`, `color`, `bold`, `italic`, `mono`.

## Elements (each has `"type"`)
- **bullets** — `items: [{text|runs, level(0/1), bold, color, bullet, size, gap}]`, plus `x,y,w,size`.
- **textbox** — free text block. `paras: [{runs, size, color, align, gap}]` (or single `runs`), `x,y,w,align`.
- **hero** — big stat. `value` (str, ~44 pt bold), `caption`, `color`, `x,y,w`.
- **callout** — rounded panel. `text` or `runs`, `fill: blue|green|red|light|none`, `bold`, `x,y,w,h`.
- **table** — `header: [...]`, `rows: [[cell,...]]`, `col_w: [in,...]`, `x,y,w,row_h,size`.
  A cell is a str, or `{"text"/"runs", "color", "bold"}` for emphasis. Header row auto = dark navy fill, white bold.
  `bold_cells: ["r,c"]`, `cell_color: {"r,c": color}` for str cells (r counts the header as row 0).
- **cards** — row of labeled panels. `items: [{head, body(str|runs), accent, fill, extra_paras}]`, `x,y,w,h,gap`.
- **line** — hairline separator. `x,y,w,color,weight`.
- **image** — `path,x,y,w,h`.

## Layout guidance (match deck 1)
- One eyebrow + one title per slide; keep the title to one line if possible.
- Body starts ~1.75 in; leave the bottom ~0.6 in for footnotes.
- Emphasis: blue for key/positive points & arrows, red for collapse/negative, green for "yes".
- Prefer a hero number or a tight table over dense prose on a result slide.
- Don't overfill: deck 1 slides carry ~1 table OR ~3-5 bullets OR a card row — not all at once.
