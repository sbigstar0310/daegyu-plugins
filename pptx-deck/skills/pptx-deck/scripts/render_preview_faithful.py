#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight pptx -> PNG previewer (no LibreOffice needed).

Approximates each slide by drawing every shape at its real inch coordinates:
pictures are shown as their actual images; text boxes / auto-shapes are drawn
as their fill rectangle plus the text (top-aligned, wrapped roughly). Good
enough to catch PADDING, OVERLAP, and OVERFLOW problems while iterating design.

    python experiments/thinking_distance/slides/render_preview.py winner_deck.pptx
Outputs preview_01.png ... and a contact sheet preview_grid.png in the same dir.
"""
import io, os, sys, math, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

EMU = 914400.0
HERE = os.path.dirname(os.path.abspath(__file__))


def rgb(color):
    try:
        c = color.rgb
        return "#%02x%02x%02x" % (c[0], c[1], c[2])
    except Exception:
        return None


def shape_text(sh):
    if not sh.has_text_frame:
        return []
    out = []
    for p in sh.text_frame.paragraphs:
        txt = "".join(r.text for r in p.runs)
        size = 14
        bold = False
        col = "#1a2332"
        for r in p.runs:
            if r.font.size: size = r.font.size.pt
            if r.font.bold: bold = True
            if r.font.color and r.font.color.type is not None:
                cc = rgb(r.font.color)
                if cc: col = cc
            break
        align = str(p.alignment) if p.alignment is not None else "LEFT"
        out.append((txt, size, bold, col, align))
    return out


def draw_slide(slide, sw, sh, path):
    fig, ax = plt.subplots(figsize=(sw, sh), dpi=115)
    ax.set_xlim(0, sw); ax.set_ylim(0, sh); ax.invert_yaxis(); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), sw, sh, facecolor="white", edgecolor="#dddddd"))
    for shp in slide.shapes:
        L, T = shp.left/EMU, shp.top/EMU
        Wd, Hd = shp.width/EMU, shp.height/EMU
        if shp.has_table:
            tbl = shp.table
            cols = list(tbl.columns); rows = list(tbl.rows)
            cws = [c.width/EMU for c in cols]
            # scale col widths to shape width
            sc = Wd/sum(cws) if sum(cws) else 1.0
            cws = [w*sc for w in cws]
            rhs = [r.height/EMU for r in rows]
            sh_ = Hd/sum(rhs) if sum(rhs) else 1.0
            rhs = [h*sh_ for h in rhs]
            cy = T
            for ri, row in enumerate(rows):
                cx = L
                for ci in range(len(cols)):
                    cell = tbl.cell(ri, ci)
                    fc = None
                    try:
                        if cell.fill.type is not None: fc = rgb(cell.fill.fore_color)
                    except Exception: pass
                    ax.add_patch(Rectangle((cx, cy), cws[ci], rhs[ri],
                                 facecolor=fc or "white", edgecolor="#d5d9df", lw=0.8, zorder=2))
                    txt = cell.text_frame.paragraphs[0]
                    s = "".join(r.text for r in txt.runs)
                    col = "#1a2332"; bold = False; size = 13
                    for r in txt.runs:
                        if r.font.size: size = r.font.size.pt
                        if r.font.bold: bold = True
                        if r.font.color and r.font.color.type is not None:
                            cc = rgb(r.font.color)
                            if cc: col = cc
                        break
                    if s.strip():
                        ha = "left" if ci == 0 else "center"
                        xt = cx+0.1 if ci == 0 else cx+cws[ci]/2
                        ax.text(xt, cy+rhs[ri]/2, s, ha=ha, va="center", fontsize=size*0.9,
                                color=col, fontweight="bold" if bold else "normal", zorder=4)
                    cx += cws[ci]
                cy += rhs[ri]
            continue
        if shp.shape_type == MSO_SHAPE_TYPE.PICTURE:
            try:
                img = np.array(Image.open(io.BytesIO(shp.image.blob)).convert("RGBA"))
                ax.imshow(img, extent=(L, L+Wd, T+Hd, T), zorder=3)
            except Exception:
                ax.add_patch(Rectangle((L, T), Wd, Hd, facecolor="#eeeeee", edgecolor="#bbbbbb"))
            continue
        fill = None
        try:
            if shp.fill.type is not None:
                fill = rgb(shp.fill.fore_color)
        except Exception:
            pass
        line = None
        try:
            if shp.line.color and shp.line.color.type is not None:
                line = rgb(shp.line.color)
        except Exception:
            pass
        if fill or line:
            ax.add_patch(FancyBboxPatch((L, T), Wd, Hd, boxstyle="round,pad=0.01",
                         facecolor=fill or "none", edgecolor=line or "none", linewidth=1.2, zorder=1))
        # text
        lines = shape_text(shp)
        y = T + 0.06
        for txt, size, bold, col, align in lines:
            if not txt.strip():
                y += size/72.0 * 1.2
                continue
            wrapped = textwrap.wrap(txt, max(6, int(Wd / (size/72.0*0.55)))) or [txt]
            for wl in wrapped:
                if align == "CENTER":
                    ax.text(L+Wd/2, y+size/72.0, wl, ha="center", va="baseline",
                            fontsize=size*0.92, color=col, fontweight="bold" if bold else "normal", zorder=4)
                else:
                    ax.text(L+0.08, y+size/72.0, wl, ha="left", va="baseline",
                            fontsize=size*0.92, color=col, fontweight="bold" if bold else "normal", zorder=4)
                y += size/72.0 * 1.28
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(path, dpi=115); plt.close(fig)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "winner_deck.pptx"
    prs = Presentation(os.path.join(HERE, name))
    sw, sh = prs.slide_width/EMU, prs.slide_height/EMU
    paths = []
    for i, slide in enumerate(prs.slides, 1):
        p = os.path.join(HERE, f"preview_{i:02d}.png")
        draw_slide(slide, sw, sh, p); paths.append(p)
    # contact sheet
    n = len(paths); cols = 3; rows = math.ceil(n/cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols*4.6, rows*2.7))
    for ax in np.array(axes).ravel():
        ax.axis("off")
    for i, p in enumerate(paths):
        ax = np.array(axes).ravel()[i]
        ax.imshow(Image.open(p)); ax.set_title(f"S{i+1}", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "preview_grid.png"), dpi=120); plt.close(fig)
    print(f"rendered {n} slides + preview_grid.png")


if __name__ == "__main__":
    main()
