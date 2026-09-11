#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An approximate pptx to PNG previewer that needs no LibreOffice.

    python3 scripts/render_preview_faithful.py deck.pptx
    python3 scripts/render_preview_faithful.py deck.pptx -o build/preview

Every shape is drawn at its real inch coordinates, so positions, overlap and
margins are trustworthy. Nothing else is. It uses a proxy font, its wrapping is a
character count, and it ignores vertical anchor, so band text that looks stuck to
the top is centred in PowerPoint. Every frame carries a banner saying so, because
a preview reviewed as if it were a render produces fixes for bugs that do not
exist.

Never judge a line break here. For that, and before shipping anything, use
render_real.py, which is LibreOffice, and check_layout.py, which is arithmetic.
"""
import io, os, sys, math, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
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


BANNER = ("approximate: proxy font, character count wrapping, vertical anchor "
          "ignored. Positions are real, line breaks are not.")


def draw_slide(slide, sw, sh, path, label=""):
    fig, ax = plt.subplots(figsize=(sw, sh), dpi=115)
    ax.set_xlim(0, sw); ax.set_ylim(0, sh); ax.invert_yaxis(); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), sw, sh, facecolor="white", edgecolor="#dddddd"))
    for shp in slide.shapes:
        # Connectors carry no fill and no text, so the generic path below draws
        # nothing for them and every arrow in a diagram vanishes.
        if shp.shape_type == MSO_SHAPE_TYPE.LINE:
            L, T = shp.left / EMU, shp.top / EMU
            Wd, Hd = shp.width / EMU, shp.height / EMU
            flip_h = shp._element.spPr.xfrm.get("flipH") == "1"
            flip_v = shp._element.spPr.xfrm.get("flipV") == "1"
            x0, x1 = (L + Wd, L) if flip_h else (L, L + Wd)
            y0, y1 = (T + Hd, T) if flip_v else (T, T + Hd)
            col = None
            try:
                col = rgb(shp.line.color)
            except Exception:
                pass
            ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                         mutation_scale=9, linewidth=1.0,
                                         color=col or "#1a2332", zorder=3))
            continue
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
            # Square corners. The old rounded box invented a corner radius the
            # deck did not have and sent reviewers chasing it.
            ax.add_patch(Rectangle((L, T), Wd, Hd,
                         facecolor=fill or "none", edgecolor=line or "none",
                         linewidth=1.2, zorder=1))
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
    ax.add_patch(Rectangle((0, 0), sw, 0.17, facecolor="#FFF3BF", edgecolor="none", zorder=9))
    ax.text(0.06, 0.115, BANNER + ("   " + label if label else ""), ha="left", va="baseline",
            fontsize=5.4, color="#6b5b00", zorder=10)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(path, dpi=115); plt.close(fig)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("-o", "--out", help="directory for the PNGs. Defaults to beside the deck.")
    a = ap.parse_args()

    # The old version joined the given name onto this script's own directory and
    # wrote its output there too, so an absolute path was mangled and every run
    # left PNGs in the skill folder. People then reviewed a stale render and
    # fixed bugs that were already gone.
    deck = os.path.abspath(a.deck)
    out = os.path.abspath(a.out) if a.out else os.path.dirname(deck)
    os.makedirs(out, exist_ok=True)

    prs = Presentation(deck)
    sw, sh = prs.slide_width / EMU, prs.slide_height / EMU
    paths = []
    for i, slide in enumerate(prs.slides, 1):
        hidden = slide._element.get("show") == "0"
        p = os.path.join(out, "preview_%02d.png" % i)
        draw_slide(slide, sw, sh, p, label="HIDDEN SLIDE" if hidden else "")
        paths.append(p)

    n = len(paths); cols = 3; rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.6, rows * 2.7))
    for ax in np.array(axes).ravel():
        ax.axis("off")
    for i, p in enumerate(paths):
        ax = np.array(axes).ravel()[i]
        ax.imshow(Image.open(p)); ax.set_title("S%d" % (i + 1), fontsize=9)
    fig.tight_layout()
    grid = os.path.join(out, "preview_grid.png")
    fig.savefig(grid, dpi=120); plt.close(fig)
    print("rendered %d slides and preview_grid.png into %s" % (n, out))
    print("This is approximate. Judge line breaks with render_real.py instead.")


if __name__ == "__main__":
    main()
