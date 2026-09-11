"""Spec -> PPTX renderer for the Anywhere-Think deck.

A slide is a plain dict ("spec"). The renderer turns it into a styled slide that
matches docs/ppt/Intro.pptx (Roboto, the custom navy/blue palette, eyebrow +
title + body + footnote skeleton). Keeping slides as data means the best-of-N
layout agents (Fable) can emit/adjust specs as JSON without touching drawing code.

Spec schema (all positions in inches; omit x/y/w/h to use sensible defaults):

    {
      "eyebrow": "RESULT",                 # top-left ALL-CAPS label (blue)
      "title": "Move thinking away ...",   # 25pt bold navy
      "subtitle": "optional line",         # 16pt gray under title
      "footnote": "citation ...",          # 10pt gray at bottom (str or list[str])
      "elements": [ <element>, ... ]
    }

Element types (each a dict with "type"):
  - {"type":"bullets", "items":[{"text","level","bold","color","runs"}], x,y,w,h, "size"}
  - {"type":"table", "header":[...], "rows":[[cell,...]], "col_w":[...], x,y,w, "cell_color":{r,c:color}}
  - {"type":"hero", "value":"61% -> 26%", "caption":"...", "color":"red", x,y,w,h}
  - {"type":"callout", "text" or "runs", "fill":"blue|green|red|light", x,y,w,h, "size", "bold"}
  - {"type":"textbox", "runs":[{text,size,color,bold,mono,italic}], x,y,w,h, "align", "para_gap"}
  - {"type":"cards", "items":[{"head","body","accent"}], x,y,w,h, "gap"]}  # row of labeled panels
  - {"type":"image", "path":"...", x,y,w,h}
  - {"type":"line", x,y,w}                 # hairline separator

A "runs" list lets one paragraph mix styles:
  "runs":[{"text":"61% ","bold":true},{"text":"-> 26%","color":"red","bold":true}]
"""
import copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

import design as D


def _rgb(name):
    return RGBColor.from_string(D.COLORS.get(name, name))


def _set_cell_border(cell, color=D.LINE, w_pt=0.75):
    """python-pptx has no cell-border API; poke the XML directly."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for old in tcPr.findall(qn(tag)):
            tcPr.remove(old)
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = tcPr.makeelement(qn(tag), {"w": str(int(w_pt * 12700)),
                                        "cap": "flat", "cmpd": "sng", "algn": "ctr"})
        fill = ln.makeelement(qn("a:solidFill"), {})
        clr = ln.makeelement(qn("a:srgbClr"), {"val": color})
        fill.append(clr)
        ln.append(fill)
        tcPr.append(ln)


def _apply_runs(para, runs, default_size, default_color="ink"):
    """Fill a paragraph with styled runs. runs: list of dicts or a single str."""
    if isinstance(runs, str):
        runs = [{"text": runs}]
    for rspec in runs:
        r = para.add_run()
        r.text = rspec.get("text", "")
        f = r.font
        f.name = D.FONT_MONO if rspec.get("mono") else D.FONT
        f.size = Pt(rspec.get("size", default_size))
        f.bold = rspec.get("bold", False)
        f.italic = rspec.get("italic", False)
        f.color.rgb = _rgb(rspec.get("color", default_color))


def _add_textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Pt(0)
    tf.margin_top = tf.margin_bottom = Pt(0)
    return tb, tf


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(D.SLIDE_W)
        self.prs.slide_height = Inches(D.SLIDE_H)
        self._blank = self.prs.slide_layouts[6]  # truly blank

    def save(self, path):
        self.prs.save(path)

    # ---------- element renderers ----------
    def _el_bullets(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", D.CONTENT_TOP)
        w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X); h = e.get("h", 4.0)
        size = e.get("size", D.SZ_BODY)
        _, tf = _add_textbox(slide, x, y, w, h)
        for i, item in enumerate(e["items"]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            lvl = item.get("level", 0)
            p.level = lvl
            p.space_after = Pt(item.get("gap", 8))
            p.space_before = Pt(item.get("gap_before", 0))
            bullet = item.get("bullet", "•" if lvl == 0 else "–")
            runs = item.get("runs")
            if runs is None:
                txt = item["text"]
                prefix = (bullet + "  ") if bullet else ""
                runs = [{"text": prefix + txt, "bold": item.get("bold", False),
                         "color": item.get("color", "ink")}]
            else:
                if bullet:
                    runs = [{"text": bullet + "  ", "color": item.get("color", "ink")}] + runs
            _apply_runs(p, runs, item.get("size", size), item.get("color", "ink"))

    def _el_textbox(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", D.CONTENT_TOP)
        w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X); h = e.get("h", 3.0)
        _, tf = _add_textbox(slide, x, y, w, h, e.get("anchor", MSO_ANCHOR.TOP))
        paras = e.get("paras", [{"runs": e.get("runs", "")}])
        align_map = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}
        for i, pa in enumerate(paras):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align_map.get(pa.get("align", e.get("align", "left")))
            p.space_after = Pt(pa.get("gap", e.get("para_gap", 6)))
            _apply_runs(p, pa.get("runs", ""), pa.get("size", e.get("size", D.SZ_BODY)),
                        pa.get("color", "ink"))

    def _el_hero(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", 2.6)
        w = e.get("w", 5.2); h = e.get("h", 1.9)
        _, tf = _add_textbox(slide, x, y, w, h, MSO_ANCHOR.MIDDLE)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if e.get("align", "left") == "left" else PP_ALIGN.CENTER
        _apply_runs(p, [{"text": e["value"], "bold": True, "size": e.get("size", 44),
                         "color": e.get("color", "ink")}], 44)
        if e.get("caption"):
            cp = tf.add_paragraph()
            cp.alignment = p.alignment
            cp.space_before = Pt(4)
            _apply_runs(cp, [{"text": e["caption"], "size": e.get("cap_size", 14),
                              "color": e.get("cap_color", "gray")}], 14)

    def _el_callout(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", 5.2)
        w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X); h = e.get("h", 0.9)
        fillmap = {"blue": D.PANEL_BLUE, "green": D.PANEL_GREEN, "red": D.PANEL_RED,
                   "light": D.LIGHT, "none": None}
        barmap = {"blue": D.BLUE, "green": D.GREEN, "red": D.RED, "light": D.GRAY, "none": D.BLUE}
        key = e.get("fill", "blue")
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                     Inches(x), Inches(y), Inches(w), Inches(h))
        box.adjustments[0] = 0.06
        if fillmap.get(key):
            box.fill.solid(); box.fill.fore_color.rgb = RGBColor.from_string(fillmap[key])
        else:
            box.fill.background()
        box.line.color.rgb = RGBColor.from_string(barmap[key]); box.line.width = Pt(0.0)
        box.shadow.inherit = False
        tf = box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Inches(0.22); tf.margin_right = Inches(0.22)
        tf.margin_top = Inches(0.1); tf.margin_bottom = Inches(0.1)
        p = tf.paragraphs[0]
        p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER}.get(e.get("align", "left"))
        runs = e.get("runs", [{"text": e.get("text", ""), "bold": e.get("bold", False),
                               "color": e.get("text_color", "ink")}])
        _apply_runs(p, runs, e.get("size", D.SZ_BODY), e.get("text_color", "ink"))

    def _el_table(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", D.CONTENT_TOP)
        header = e.get("header")
        rows = e["rows"]
        nrows = len(rows) + (1 if header else 0)
        ncols = len(rows[0])
        col_w = e.get("col_w")
        total_w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X)
        if not col_w:
            col_w = [total_w / ncols] * ncols
        row_h = e.get("row_h", 0.42)
        gtbl = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y),
                                      Inches(sum(col_w)), Inches(row_h * nrows))
        tbl = gtbl.table
        tbl.first_row = bool(header)
        tbl.horz_banding = False
        # kill default table style -> we style manually
        for ci, cw in enumerate(col_w):
            tbl.columns[ci].width = Inches(cw)
        cell_color = e.get("cell_color", {})   # {"r,c":"colorname"}
        bold_cells = set(e.get("bold_cells", []))  # ["r,c", ...]
        data = ([header] if header else []) + rows
        for ri, row in enumerate(data):
            tbl.rows[ri].height = Inches(row_h)
            for ci, val in enumerate(row):
                cell = tbl.cell(ri, ci)
                cell.margin_left = Inches(0.1); cell.margin_right = Inches(0.08)
                cell.margin_top = Inches(0.03); cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                is_head = header and ri == 0
                cell.fill.solid()
                if is_head:
                    cell.fill.fore_color.rgb = RGBColor.from_string(D.INK)
                elif ri % 2 == 0 and header:
                    cell.fill.fore_color.rgb = RGBColor.from_string(D.WHITE)
                else:
                    cell.fill.fore_color.rgb = RGBColor.from_string(D.LIGHT if (header and ri % 2 == 1) else D.WHITE)
                _set_cell_border(cell)
                tf = cell.text_frame; tf.word_wrap = True
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
                # per-cell overrides
                key = f"{ri},{ci}"
                if isinstance(val, dict):
                    runs = val.get("runs", [{"text": val.get("text", "")}])
                    color = val.get("color", "white" if is_head else "ink")
                    bold = val.get("bold", is_head)
                    _apply_runs(p, runs, e.get("size", D.SZ_TABLE), color)
                else:
                    color = cell_color.get(key, "white" if is_head else "ink")
                    bold = is_head or (key in bold_cells)
                    _apply_runs(p, [{"text": str(val), "bold": bold, "color": color}],
                                e.get("size", D.SZ_TABLE), color)

    def _el_cards(self, slide, e):
        items = e["items"]
        x = e.get("x", D.MARGIN_X); y = e.get("y", D.CONTENT_TOP)
        w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X); h = e.get("h", 2.6)
        gap = e.get("gap", 0.3)
        n = len(items)
        cw = (w - gap * (n - 1)) / n
        for i, it in enumerate(items):
            cx = x + i * (cw + gap)
            accent = it.get("accent", "blue")
            box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                         Inches(cx), Inches(y), Inches(cw), Inches(h))
            box.adjustments[0] = 0.05
            box.fill.solid(); box.fill.fore_color.rgb = RGBColor.from_string(it.get("fill", D.LIGHT))
            box.line.color.rgb = _rgb(accent); box.line.width = Pt(1.25)
            box.shadow.inherit = False
            tf = box.text_frame; tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.TOP
            for m in (tf.margin_left, ):
                pass
            tf.margin_left = Inches(0.18); tf.margin_right = Inches(0.18)
            tf.margin_top = Inches(0.16); tf.margin_bottom = Inches(0.12)
            p = tf.paragraphs[0]
            _apply_runs(p, [{"text": it["head"], "bold": True, "size": e.get("head_size", 15),
                             "color": accent}], 15)
            if it.get("body"):
                bp = tf.add_paragraph(); bp.space_before = Pt(6)
                body_runs = it["body"] if isinstance(it["body"], list) else [{"text": it["body"]}]
                _apply_runs(bp, body_runs, e.get("body_size", 13), "ink")
            for extra in it.get("extra_paras", []):
                ep = tf.add_paragraph(); ep.space_before = Pt(4)
                _apply_runs(ep, extra.get("runs", ""), extra.get("size", 13), extra.get("color", "ink"))

    def _el_line(self, slide, e):
        x = e.get("x", D.MARGIN_X); y = e.get("y", 3.0)
        w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X)
        ln = slide.shapes.add_connector(2, Inches(x), Inches(y), Inches(x + w), Inches(y))
        ln.line.color.rgb = RGBColor.from_string(e.get("color", D.LINE))
        ln.line.width = Pt(e.get("weight", 1.0))

    def _el_image(self, slide, e):
        slide.shapes.add_picture(e["path"], Inches(e["x"]), Inches(e["y"]),
                                 Inches(e["w"]) if e.get("w") else None,
                                 Inches(e["h"]) if e.get("h") else None)

    _DISPATCH = {
        "bullets": _el_bullets, "textbox": _el_textbox, "hero": _el_hero,
        "callout": _el_callout, "table": _el_table, "cards": _el_cards,
        "line": _el_line, "image": _el_image,
    }

    # ---------- slide skeleton ----------
    def add_slide(self, spec):
        slide = self.prs.slides.add_slide(self._blank)
        # white background
        bg = slide.background
        bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor.from_string(D.WHITE)

        if spec.get("eyebrow"):
            _, tf = _add_textbox(slide, D.MARGIN_X, D.MARGIN_TOP, 10, 0.35)
            p = tf.paragraphs[0]
            _apply_runs(p, [{"text": spec["eyebrow"].upper(), "bold": True,
                             "size": D.SZ_EYEBROW, "color": "blue"}], D.SZ_EYEBROW)
        title_y = spec.get("title_y", 0.95)
        if spec.get("title") or spec.get("title_runs"):
            _, tf = _add_textbox(slide, D.MARGIN_X, title_y, D.SLIDE_W - 2 * D.MARGIN_X, 0.9)
            p = tf.paragraphs[0]
            title_runs = spec.get("title_runs", [{"text": spec.get("title", ""), "bold": True,
                                                  "size": spec.get("title_size", D.SZ_TITLE),
                                                  "color": "ink"}])
            _apply_runs(p, title_runs, D.SZ_TITLE, "ink")
        if spec.get("subtitle"):
            _, tf = _add_textbox(slide, D.MARGIN_X, spec.get("subtitle_y", 1.55),
                                 D.SLIDE_W - 2 * D.MARGIN_X, 0.5)
            p = tf.paragraphs[0]
            sub_runs = spec.get("subtitle_runs", [{"text": spec["subtitle"],
                                                   "size": D.SZ_SUBTITLE, "color": "gray"}])
            _apply_runs(p, sub_runs, D.SZ_SUBTITLE, "gray")

        for e in spec.get("elements", []):
            fn = self._DISPATCH.get(e["type"])
            if fn is None:
                raise ValueError(f"unknown element type: {e['type']}")
            fn(self, slide, e)

        fn = spec.get("footnote")
        if fn:
            if isinstance(fn, str):
                fn = [fn]
            _, tf = _add_textbox(slide, D.MARGIN_X, D.SLIDE_H - 0.55,
                                 D.SLIDE_W - 2 * D.MARGIN_X, 0.45, MSO_ANCHOR.BOTTOM)
            for i, line in enumerate(fn):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                _apply_runs(p, [{"text": line, "size": D.SZ_FOOT, "color": "gray"}], D.SZ_FOOT)

        if spec.get("notes"):
            slide.notes_slide.notes_text_frame.text = spec["notes"].strip()
        if spec.get("hidden"):
            # Stays in the file, and out of both the slideshow and the exported
            # PDF. Still reachable during the talk by typing its slide number.
            slide._element.set("show", "0")
        return slide


def build(specs, out_path):
    deck = Deck()
    for s in specs:
        deck.add_slide(s)
    deck.save(out_path)
    return out_path
