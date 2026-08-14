"""Lightweight PIL preview of a deck spec (same schema as render.py).

Renders each slide to a PNG at ~96 DPI (1280x720) so layouts can be eyeballed
and scored WITHOUT LibreOffice. Uses Arial locally as a Roboto proxy (near-
identical metrics; the real .pptx names Roboto). This is a *layout* preview:
good for catching overflow / overlap / hierarchy / balance, not pixel-perfect.
"""
import os
from PIL import Image, ImageDraw, ImageFont
import design as D

DPI = 96
W = int(D.SLIDE_W * DPI)
H = int(D.SLIDE_H * DPI)

_AR = "/usr/share/fonts/truetype/msttcorefonts/arial.ttf"
_ARB = "/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf"
_ARI = "/usr/share/fonts/truetype/msttcorefonts/ariali.ttf"
_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
_cache = {}


def _font(size_pt, bold=False, mono=False, italic=False):
    px = int(size_pt * DPI / 72)
    key = (px, bold, mono, italic)
    if key not in _cache:
        path = _MONO if mono else (_ARB if bold else (_ARI if italic else _AR))
        _cache[key] = ImageFont.truetype(path, px)
    return _cache[key]


def _c(name):
    return "#" + D.COLORS.get(name, name)


def IN(v):
    return int(v * DPI)


def _wrap(draw, text, font, max_px):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_px or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _runs_lines(draw, runs, default_size, default_color, max_px):
    """Layout mixed runs into wrapped lines. Returns list of lines,
    each a list of (text, font, color) segments."""
    if isinstance(runs, str):
        runs = [{"text": runs}]
    lines = [[]]
    cur_w = 0
    for r in runs:
        f = _font(r.get("size", default_size), r.get("bold", False),
                  r.get("mono", False), r.get("italic", False))
        col = _c(r.get("color", default_color))
        for i, word in enumerate(r.get("text", "").split(" ")):
            seg = (" " if i > 0 else "") + word
            wpx = draw.textlength(seg, font=f)
            if cur_w + wpx > max_px and lines[-1]:
                lines.append([]); cur_w = 0
                seg = word; wpx = draw.textlength(seg, font=f)
            lines[-1].append((seg, f, col)); cur_w += wpx
    return lines


def _draw_runs_block(draw, x, y, runs, size, color, max_px, line_gap=1.25):
    lines = _runs_lines(draw, runs, size, color, max_px)
    cy = y
    for line in lines:
        cx = x
        maxh = 0
        for seg, f, col in line:
            draw.text((cx, cy), seg, font=f, fill=col)
            cx += draw.textlength(seg, font=f)
            maxh = max(maxh, f.size)
        cy += int(maxh * line_gap)
    return cy


def render_slide(spec):
    img = Image.new("RGB", (W, H), "#" + D.WHITE)
    dr = ImageDraw.Draw(img)
    mx = IN(D.MARGIN_X)
    contentw = W - 2 * mx

    if spec.get("eyebrow"):
        dr.text((mx, IN(D.MARGIN_TOP)), spec["eyebrow"].upper(),
                font=_font(D.SZ_EYEBROW, True), fill=_c("blue"))
    if spec.get("title") or spec.get("title_runs"):
        _draw_runs_block(dr, mx, IN(spec.get("title_y", 0.95)),
                         spec.get("title_runs", [{"text": spec.get("title", ""), "bold": True,
                                                  "size": spec.get("title_size", D.SZ_TITLE)}]),
                         D.SZ_TITLE, "ink", contentw)
    if spec.get("subtitle"):
        _draw_runs_block(dr, mx, IN(spec.get("subtitle_y", 1.55)),
                         spec.get("subtitle_runs", [{"text": spec["subtitle"]}]),
                         D.SZ_SUBTITLE, "gray", contentw)

    for e in spec.get("elements", []):
        t = e["type"]
        if t == "bullets":
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", D.CONTENT_TOP))
            w = IN(e.get("w", D.SLIDE_W - 2 * D.MARGIN_X))
            size = e.get("size", D.SZ_BODY)
            for item in e["items"]:
                lvl = item.get("level", 0)
                bullet = item.get("bullet", "•" if lvl == 0 else "–")
                indent = x + lvl * IN(0.3)
                runs = item.get("runs")
                if runs is None:
                    runs = [{"text": (bullet + "  " if bullet else "") + item["text"],
                             "bold": item.get("bold", False), "color": item.get("color", "ink")}]
                elif bullet:
                    runs = [{"text": bullet + "  ", "color": item.get("color", "ink")}] + runs
                y = _draw_runs_block(dr, indent, y, runs, item.get("size", size),
                                     item.get("color", "ink"), w - lvl * IN(0.3))
                y += IN(item.get("gap", 8) / 72)
        elif t == "textbox":
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", D.CONTENT_TOP))
            w = IN(e.get("w", D.SLIDE_W - 2 * D.MARGIN_X))
            for pa in e.get("paras", [{"runs": e.get("runs", "")}]):
                y = _draw_runs_block(dr, x, y, pa.get("runs", ""),
                                     pa.get("size", e.get("size", D.SZ_BODY)),
                                     pa.get("color", "ink"), w)
                y += IN(pa.get("gap", e.get("para_gap", 6)) / 72)
        elif t == "hero":
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", 2.6))
            _draw_runs_block(dr, x, y, [{"text": e["value"], "bold": True,
                                         "size": e.get("size", 44), "color": e.get("color", "ink")}],
                             44, "ink", IN(e.get("w", 8)))
            if e.get("caption"):
                dr.text((x, y + IN(e.get("size", 44) / 72 * 1.15)), e["caption"],
                        font=_font(e.get("cap_size", 14)), fill=_c(e.get("cap_color", "gray")))
        elif t == "callout":
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", 5.2))
            w = IN(e.get("w", D.SLIDE_W - 2 * D.MARGIN_X)); h = IN(e.get("h", 0.9))
            fillmap = {"blue": D.PANEL_BLUE, "green": D.PANEL_GREEN, "red": D.PANEL_RED, "light": D.LIGHT}
            barmap = {"blue": D.BLUE, "green": D.GREEN, "red": D.RED, "light": D.GRAY}
            key = e.get("fill", "blue")
            dr.rounded_rectangle([x, y, x + w, y + h], radius=IN(0.08),
                                 fill="#" + fillmap.get(key, D.LIGHT),
                                 outline="#" + barmap.get(key, D.BLUE), width=2)
            runs = e.get("runs", [{"text": e.get("text", ""), "bold": e.get("bold", False),
                                   "color": e.get("text_color", "ink")}])
            _draw_runs_block(dr, x + IN(0.22), y + IN(0.16), runs, e.get("size", D.SZ_BODY),
                             e.get("text_color", "ink"), w - IN(0.44))
        elif t == "cards":
            items = e["items"]; n = len(items)
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", D.CONTENT_TOP))
            w = IN(e.get("w", D.SLIDE_W - 2 * D.MARGIN_X)); h = IN(e.get("h", 2.6))
            gap = IN(e.get("gap", 0.3)); cw = (w - gap * (n - 1)) // n
            for i, it in enumerate(items):
                cx = x + i * (cw + gap); acc = it.get("accent", "blue")
                dr.rounded_rectangle([cx, y, cx + cw, y + h], radius=IN(0.06),
                                     fill="#" + it.get("fill", D.LIGHT), outline=_c(acc), width=2)
                yy = y + IN(0.16)
                yy = _draw_runs_block(dr, cx + IN(0.18), yy, [{"text": it["head"], "bold": True,
                                      "size": e.get("head_size", 15), "color": acc}], 15, acc, cw - IN(0.36))
                if it.get("body"):
                    body = it["body"] if isinstance(it["body"], list) else [{"text": it["body"]}]
                    yy += IN(0.08)
                    yy = _draw_runs_block(dr, cx + IN(0.18), yy, body, e.get("body_size", 13),
                                          "ink", cw - IN(0.36))
                for extra in it.get("extra_paras", []):
                    yy += IN(0.05)
                    yy = _draw_runs_block(dr, cx + IN(0.18), yy, extra.get("runs", ""),
                                          extra.get("size", 13), extra.get("color", "ink"), cw - IN(0.36))
        elif t == "line":
            x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", 3.0))
            w = IN(e.get("w", D.SLIDE_W - 2 * D.MARGIN_X))
            dr.line([x, y, x + w, y], fill="#" + e.get("color", D.LINE), width=2)
        elif t == "table":
            _preview_table(dr, e)
        elif t == "image":
            try:
                im = Image.open(e["path"]).convert("RGB")
                tw = IN(e.get("w", 3)) if e.get("w") else im.width
                th = IN(e.get("h", 3)) if e.get("h") else im.height
                im = im.resize((int(tw), int(th)))
                img.paste(im, (IN(e["x"]), IN(e["y"])))
            except Exception:
                pass

    fn = spec.get("footnote")
    if fn:
        if isinstance(fn, str):
            fn = [fn]
        fy = H - IN(0.5)
        for line in fn:
            dr.text((mx, fy), line, font=_font(D.SZ_FOOT), fill=_c("gray"))
            fy += IN(0.16)
    return img


def _preview_table(dr, e):
    x = IN(e.get("x", D.MARGIN_X)); y = IN(e.get("y", D.CONTENT_TOP))
    header = e.get("header"); rows = e["rows"]
    ncols = len(rows[0])
    total_w = e.get("w", D.SLIDE_W - 2 * D.MARGIN_X)
    col_w = e.get("col_w") or [total_w / ncols] * ncols
    col_w = [IN(c) for c in col_w]
    row_h = IN(e.get("row_h", 0.42))
    data = ([header] if header else []) + rows
    cell_color = e.get("cell_color", {}); bold_cells = set(e.get("bold_cells", []))
    cy = y
    for ri, row in enumerate(data):
        cx = x; is_head = header and ri == 0
        for ci, val in enumerate(row):
            cw = col_w[ci]
            bg = "#" + (D.INK if is_head else (D.LIGHT if (header and ri % 2 == 1) else D.WHITE))
            dr.rectangle([cx, cy, cx + cw, cy + row_h], fill=bg, outline="#" + D.LINE, width=1)
            key = f"{ri},{ci}"
            if isinstance(val, dict):
                runs = val.get("runs", [{"text": val.get("text", "")}])
                color = val.get("color", "white" if is_head else "ink"); bold = val.get("bold", is_head)
                txt = "".join(r.get("text", "") for r in runs)
                if len(runs) == 1:
                    color = runs[0].get("color", color); bold = runs[0].get("bold", bold)
            else:
                txt = str(val); color = cell_color.get(key, "white" if is_head else "ink")
                bold = is_head or (key in bold_cells)
            f = _font(e.get("size", D.SZ_TABLE), bold)
            tw = dr.textlength(txt, font=f)
            tx = cx + IN(0.1) if ci == 0 else cx + (cw - tw) // 2
            ty = cy + (row_h - f.size) // 2
            dr.text((tx, ty), txt, font=f, fill=_c(color))
            cx += cw
        cy += row_h


def render_deck(specs, out_dir, prefix="slide", combine=True):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    imgs = []
    for i, s in enumerate(specs, 1):
        im = render_slide(s)
        p = os.path.join(out_dir, f"{prefix}{i:02d}.png")
        im.save(p); paths.append(p); imgs.append(im)
    if combine and imgs:
        cols = 2
        rows = (len(imgs) + cols - 1) // cols
        pad = 16
        sheet = Image.new("RGB", (cols * W + (cols + 1) * pad, rows * H + (rows + 1) * pad), "#DDDDDD")
        for i, im in enumerate(imgs):
            r, c = divmod(i, cols)
            sheet.paste(im, (pad + c * (W + pad), pad + r * (H + pad)))
        cp = os.path.join(out_dir, f"{prefix}_contact_sheet.png")
        sheet.save(cp); paths.append(cp)
    return paths
