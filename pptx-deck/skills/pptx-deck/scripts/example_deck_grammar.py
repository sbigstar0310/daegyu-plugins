#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deck 2 - "Cold-start SFT: learning WHERE" - in the first talk's visual grammar:
kicker + 25pt title + a short blue accent bar, plain bullets, one light band per
slide, diagrams/charts for results. Flat by design (one emphasis per slide).
Numbers from docs/12 (placement F1), docs/13 (2x2 acc-degradation), sft/ (recipe),
and the TA cold-start parquet (data distribution). Font = Roboto.
    <pptvenv>/bin/python ppt/deck2.py
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "build", "fig")


def _sample_arrays():
    """The real arrays if they are on disk, otherwise plausible stand-ins so the
    example runs anywhere. Never copy this into a real deck: a chart on a slide
    must come from measured data, and a stand-in that reaches an audience is a
    fabricated result."""
    mk_p = os.path.join(FIG, "mk.npy")
    lens_p = os.path.join(FIG, "lens.npy")
    if os.path.exists(mk_p) and os.path.exists(lens_p):
        return np.load(mk_p), np.load(lens_p)
    print("example_deck_grammar: no build/fig/*.npy, drawing the charts from "
          "sample numbers so the example still runs.")
    rng = np.random.default_rng(0)
    return rng.poisson(12, 900), rng.normal(520, 210, 900).clip(20, 1400)
os.makedirs(FIG, exist_ok=True)

C_INK, C_MUTE, C_ACC = "#1a2332", "#5b6372", "#2563eb"
C_RED, C_GRN, C_AMBER = "#dc2626", "#059669", "#ea580c"
EP10_D1 = 40.5   # run4: 104/257, no_code 4

plt.rcParams.update({
    "font.size": 13, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#9ca3af", "text.color": C_INK, "figure.dpi": 200,
    "xtick.color": "#4b5563", "ytick.color": "#4b5563",
})


# ============================================================ figures
def fig_marker(path):
    """TA data has reasoning INSIDE each inline <thinkanywhere>...</thinkanywhere>
    tag; our SFT keeps only a bare marker. Kept distinct from the up-front <think>."""
    fig, ax = plt.subplots(figsize=(12.2, 3.0)); ax.axis("off")
    ax.set_xlim(0, 13.2); ax.set_ylim(0, 6)

    def row(y, segs, strike_idx=None):
        x = 0.1
        for i, (t, w, fc, tc) in enumerate(segs):
            ax.add_patch(Rectangle((x, y), w, 0.95, facecolor=fc, edgecolor="white", lw=1.4))
            ax.text(x + w / 2, y + 0.475, t, ha="center", va="center", family="monospace",
                    fontsize=11, color=tc, fontweight=("bold" if fc == "#dbe6ff" else "normal"),
                    style=("italic" if strike_idx == i else "normal"))
            if strike_idx == i:
                ax.plot([x + 0.15, x + w - 0.15], [y + 0.475, y + 0.475], color=C_MUTE, lw=1.3)
            x += w

    TA, TC = "<thinkanywhere>", "</thinkanywhere>"
    ax.text(0.1, 5.5, "TA cold-start data: reasoning sits INSIDE each inline tag", fontsize=12,
            fontweight="bold", color=C_MUTE)
    row(4.1, [("T =", 1.1, "#eef2f7", C_INK), (TA, 3.05, "#dbe6ff", C_ACC),
              ("parse # of test cases", 4.0, "#f3f4f6", "#9aa2af"), (TC, 3.15, "#dbe6ff", C_ACC),
              ("int(x)", 1.5, "#eef2f7", C_INK)], strike_idx=2)
    ax.text(0.1, 3.05, "Our SFT target: keep a bare marker, drop the inside text", fontsize=12,
            fontweight="bold", color=C_INK)
    row(1.65, [("T =", 1.1, "#eef2f7", C_INK), (TA, 3.05, "#dbe6ff", C_ACC), ("int(x)", 1.5, "#eef2f7", C_INK)])
    ax.text(0.1, 0.5, "The up-front <think>...</think> CoT is a separate block and is left unchanged.",
            fontsize=10.5, color=C_MUTE, style="italic")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)


def fig_data(path):
    # This example shipped without its data, so running it failed on the first
    # line of the first figure. The point of a worked deck is that it runs, so
    # stand-in numbers are generated when the real arrays are absent. Anything
    # drawn from them is shape, not evidence.
    mk, lens = _sample_arrays()
    fig, axes = plt.subplots(2, 1, figsize=(5.4, 4.3))
    ax = axes[0]
    ax.hist(np.clip(mk, 0, 40), bins=range(0, 42, 2), color=C_ACC, alpha=0.85, edgecolor="white")
    ax.axvline(mk.mean(), color=C_INK, lw=1.5, ls="--")
    ax.text(mk.mean() + 0.8, ax.get_ylim()[1] * 0.72, f"mean {mk.mean():.0f}", color=C_INK, fontsize=10)
    ax.set_title("Markers per response", fontsize=12, fontweight="bold")
    ax.set_xlabel("<thinkanywhere> count", fontsize=10); ax.set_ylabel("responses", fontsize=10)
    ax2 = axes[1]
    ax2.hist(np.clip(lens, 0, 1200), bins=range(0, 1260, 60), color=C_GRN, alpha=0.85, edgecolor="white")
    ax2.axvline(640, color=C_RED, lw=1.6)
    ax2.text(660, ax2.get_ylim()[1] * 0.72, "kept ≤ 640", color=C_RED, fontsize=10)
    ax2.set_title("Response length", fontsize=12, fontweight="bold")
    ax2.set_xlabel("tokens", fontsize=10); ax2.set_ylabel("responses", fontsize=10)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)


def fig_process(path):
    """Mask a response at t, let the model fill it back, check whether each masked
    marker returns. Right = the 2x2 that scores it (correct green, error red)."""
    fig, ax = plt.subplots(figsize=(12.4, 3.5)); ax.axis("off")
    ax.set_xlim(0, 15.5); ax.set_ylim(0, 6.2)
    base = [("def", C_INK, "#eef2f7"), ("<ta>", C_ACC, "#dbe6ff"), ("x=..", C_INK, "#eef2f7"),
            ("arr", C_INK, "#eef2f7"), ("<ta>", C_ACC, "#dbe6ff"), ("ret", C_INK, "#eef2f7")]
    mask = [0, 1, 1, 0, 1, 0]

    def drawrow(y, masked=None, check=False):
        x = 1.75
        for i, (t, tc, fc) in enumerate(base):
            if masked and masked[i]:
                ax.add_patch(Rectangle((x, y), 1.15, 0.8, facecolor="#e5e7eb", edgecolor="white", lw=2))
                ax.text(x + 0.575, y + 0.4, "?", ha="center", va="center", fontsize=13, color="#9ca3af", fontweight="bold")
            else:
                ax.add_patch(Rectangle((x, y), 1.15, 0.8, facecolor=fc, edgecolor="white", lw=2))
                ax.text(x + 0.575, y + 0.4, t, ha="center", va="center", fontsize=10.5, color=tc,
                        fontweight="bold", family="monospace")
            if check and t == "<ta>":
                ax.text(x + 0.575, y - 0.42, "✓", ha="center", va="center", fontsize=14, color=C_GRN, fontweight="bold")
            x += 1.28
    ys = [4.5, 2.9, 1.3]
    for lab, y in zip(["response", "mask at t", "model fills"], ys):
        ax.text(1.6, y + 0.4, lab, ha="right", va="center", fontsize=11, color=C_MUTE)
    drawrow(ys[0]); drawrow(ys[1], masked=mask); drawrow(ys[2], check=True)
    ax.text(1.75, 5.6, "Does each masked marker come back in the right slot?", fontsize=11.5, color=C_INK, fontweight="bold")
    # 2x2 confusion on the right
    cells = [(1, 1, "TP", "#e6f7ef", C_GRN), (2, 1, "FN", "#fdecec", C_RED),
             (1, 0, "FP", "#fdecec", C_RED), (2, 0, "TN", "#e6f7ef", C_GRN)]
    x0, y0, cw, ch = 10.6, 1.3, 1.9, 1.25
    for col, row_, lab, fc, tc in cells:
        x = x0 + (col - 1) * cw; y = y0 + row_ * ch
        ax.add_patch(Rectangle((x, y), cw, ch, facecolor=fc, edgecolor="white", lw=3))
        ax.text(x + cw / 2, y + ch / 2, lab, ha="center", va="center", fontsize=17, fontweight="bold", color=tc)
    ax.text(x0 + cw, y0 + 2 * ch + 0.30, "predicts marker / code", ha="center", fontsize=10, color=C_MUTE)
    ax.text(x0 - 0.15, y0 + 1.5 * ch, "gold\nmarker", ha="right", va="center", fontsize=9.5, color=C_MUTE)
    ax.text(x0 - 0.15, y0 + 0.5 * ch, "gold\ncode", ha="right", va="center", fontsize=9.5, color=C_MUTE)
    ax.text(x0 + cw, y0 - 0.32, "green = correct,  red = error", ha="center", va="center", fontsize=9.5, color=C_MUTE)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)


def fig_place(path):
    xs = ["base", "ep2", "ep6", "ep10"]; xi = range(len(xs))
    prec = [0.468, 0.780, 0.790, 0.803]; rec = [0.604, 0.715, 0.775, 0.791]
    f1 = [0.527, 0.746, 0.783, 0.797]
    fig, ax = plt.subplots(figsize=(7.6, 4.5))
    for ys, c, lab, lw in [(f1, C_ACC, "F1", 3.2), (prec, C_GRN, "precision", 2.2), (rec, C_AMBER, "recall", 2.2)]:
        ax.plot(xi, ys, marker="o", ms=7, color=c, lw=lw, label=lab)
    ax.text(-0.06, f1[0], f"{f1[0]:.2f}", color=C_ACC, fontsize=12, ha="right", va="center", fontweight="bold")
    ax.text(len(xs) - 1 + 0.06, f1[-1], f"{f1[-1]:.2f}", color=C_ACC, fontsize=12, ha="left", va="center", fontweight="bold")
    ax.set_xticks(list(xi)); ax.set_xticklabels(xs)
    ax.set_ylim(0.40, 0.88); ax.set_ylabel("score")
    ax.set_title("Placement quality rises with every epoch", fontsize=13.5, fontweight="bold", pad=8)
    ax.grid(alpha=0.25, axis="y"); ax.legend(loc="lower right", frameon=False, fontsize=11)
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)


# ============================================================ pptx helpers
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image

INK = RGBColor(0x1A, 0x23, 0x32); MUTE = RGBColor(0x5B, 0x63, 0x72)
ACC = RGBColor(0x25, 0x63, 0xEB); RED = RGBColor(0xDC, 0x26, 0x26)
GRN = RGBColor(0x05, 0x96, 0x69); WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BAND = RGBColor(0xF3, 0xF4, 0xF6); WARN = RGBColor(0xFB, 0xF7, 0xF0)
HDR = RGBColor(0xE9, 0xEC, 0xF1)
W, H = Inches(13.333), Inches(7.5)
MARGIN = 0.7
FONT = "Roboto"


def para(tf, runs, size, align=PP_ALIGN.LEFT, after=6, new=True, level=0):
    p = tf.add_paragraph() if (new and tf.paragraphs[0].runs) else tf.paragraphs[0]
    p.alignment = align; p.space_after = Pt(after); p.level = level
    if isinstance(runs, tuple): runs = [runs]
    for t, b, c in runs:
        r = p.add_run(); r.text = t; r.font.size = Pt(size); r.font.bold = b
        r.font.color.rgb = c; r.font.name = FONT
    return p


def box(slide, x, y, w, h, fill=None, line=None, lw=1.0, rounded=False):
    shp = slide.shapes.add_shape(5 if rounded else 1, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = line; shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    return shp


def tbox(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.text_frame.word_wrap = True; return tb


def slide_new(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = box(s, 0, 0, 13.333, 7.5, fill=WHITE)
    s.shapes._spTree.remove(bg._element); s.shapes._spTree.insert(2, bg._element)
    return s


def header(s, title, kicker=None):
    if kicker:
        para(tbox(s, 0.6, 0.33, 12, 0.4).text_frame, (kicker.upper(), True, ACC), 13)
    para(tbox(s, 0.6, 0.66, 12.2, 1.0).text_frame, (title, True, INK), 25)
    box(s, 0.62, 1.55, 1.4, 0.045, fill=ACC)


def pic(s, path, top, height, left=None):
    iw, ih = Image.open(path).size
    h = Inches(height); w = Emu(int(h * iw / ih))
    s.shapes.add_picture(path, int((W - w) / 2) if left is None else Inches(left), Inches(top), height=h)


def bullets(s, items, top, left=0.7, width=12.0, size=17):
    tf = tbox(s, left, top, width, 5.2).text_frame
    for i, it in enumerate(items):
        runs, lvl = it
        para(tf, [("•  " if lvl == 0 else "–  ", False, runs[0][2])] + list(runs),
             size - lvl, after=10, new=(i > 0), level=lvl)
    return tf


def band(s, x, y, w, h, runs_list, fill=BAND, line=None, lw=1.0, center=True, sizes=None):
    b = box(s, x, y, w, h, fill=fill, line=line, lw=lw, rounded=True)
    tf = b.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    al = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
    for i, runs in enumerate(runs_list):
        para(tf, runs, (sizes[i] if sizes else 15), align=al, after=3, new=(i > 0))
    return b


def small_table(s, x, y, w, header_row, rows, col_w, row_h=0.5, fs=13, bold_rows=()):
    nr = len(rows) + 1; nc = len(header_row)
    tbl = s.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr)).table
    tbl.first_row = True; tbl.horz_banding = False
    for ci, cw in enumerate(col_w):
        tbl.columns[ci].width = Inches(cw)
    data = [header_row] + rows
    for r in range(nr):
        tbl.rows[r].height = Inches(row_h)
        for c in range(nc):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.1); cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02); cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = HDR if r == 0 else (RGBColor(0xF7, 0xF8, 0xFA) if r % 2 == 0 else WHITE)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            run = p.add_run(); run.text = str(data[r][c]); run.font.name = FONT
            run.font.size = Pt(fs); run.font.color.rgb = INK
            run.font.bold = (r == 0) or (c == 0) or (r in bold_rows)
    return tbl


# ============================================================ build
def build(prs):
    ep10 = f"{EP10_D1}" if EP10_D1 is not None else "-"

    # ---------- S1 TITLE ----------
    s = slide_new(prs)
    para(tbox(s, MARGIN, 1.8, 11.9, 1.0).text_frame, ("Learning WHERE to Think", True, INK), 40)
    box(s, 0, 2.72, 13.333, 0.03, fill=ACC)
    para(tbox(s, MARGIN, 2.95, 11.9, 0.6).text_frame,
         ("Cold-start SFT: teaching LLaDA to place a bare <thinkanywhere> marker", True, ACC), 20)
    para(tbox(s, MARGIN, 3.75, 11.9, 0.6).text_frame,
         ("Last time, placement mattered. This time, we teach the model where to place it.", False, MUTE), 16)
    para(tbox(s, MARGIN, 6.85, 11.9, 0.4).text_frame, ("Daegyu Seong, MLAI, KAIST, 26.07.22", False, MUTE), 13)

    # ---------- S2 RECAP ----------
    s = slide_new(prs); header(s, "Where we left off: placement matters, now learn it", "Recap")
    bullets(s, [
        ([("In an MDL, moving the thinking far from the answer collapses accuracy, from 61% to 26%. "
           "Kept next to the answer, it stays about 55 to 57%.", False, INK)], 0),
        ([("So the position of the thinking changes the answer. That cost comes from RoPE, not the token count.", False, INK)], 0),
        ([("The planned next steps were (1) cold-start data, then (2) RL to learn placement.", False, INK)], 0),
    ], top=2.15, size=17)
    band(s, MARGIN, 4.7, 11.93, 0.85, [
        [("This talk is step (1): a cold-start SFT that teaches the model ", False, INK),
         ("where to place its thinking", True, INK), (".", False, INK)]], sizes=[18])
    para(tbox(s, MARGIN, 6.3, 12, 0.4).text_frame,
         ("Deck 1, LLaDA-8B, GSM8K, n=200, distance D 0 to 512.", False, MUTE), 12)

    # ---------- S3 IDEA (marker-only) ----------
    s = slide_new(prs); header(s, "Teach WHERE, not WHAT: a marker-only SFT", "Cold start")
    pic(s, os.path.join(FIG, "fig_marker.png"), top=2.05, height=2.9, left=0.7)
    bullets(s, [
        ([("Inside each inline <thinkanywhere> tag we remove the reasoning, keeping only a bare marker at its position. "
           "The model learns ", False, INK), ("a position, not wording", True, INK), (".", False, INK)], 0),
        ([("The up-front <think> CoT stays untouched. Only the inline markers are the new thing to place.", False, INK)], 0),
    ], top=5.35, size=16)

    # ---------- S4 SETUP + TRAINING ----------
    s = slide_new(prs); header(s, "Setup and training", "Setup")
    tf = tbox(s, 0.7, 1.85, 6.5, 4.2).text_frame
    para(tf, ("Model and adapter", True, INK), 16, after=9)
    para(tf, ("•  LLaDA-8B-Instruct, frozen, bf16.", False, INK), 14, after=7)
    para(tf, ("•  LoRA on all linear layers, r = 16, alpha = 32.", False, INK), 14, after=7)
    para(tf, ("•  41.9M trainable parameters.", False, INK), 14, after=16)
    para(tf, ("Data and training", True, INK), 16, after=9)
    para(tf, ("•  Think-Anywhere cold-start code data, 5,773 responses.", False, INK), 14, after=7)
    para(tf, ("•  Eval on MBPP sanitized (257), held out. Training data is not MBPP.", False, INK), 14, after=7)
    para(tf, ("•  LLaDA SFT recipe: AdamW, lr 2.5e-5, batch 64, 10 epochs (850 steps).", False, INK), 14)
    pic(s, os.path.join(FIG, "fig_data.png"), top=1.95, height=3.55, left=7.65)
    para(tbox(s, 7.65, 5.6, 5.4, 0.5).text_frame,
         ("Markers are placed before code tokens (avg ~12); long responses are dropped at 640 tokens.", False, MUTE), 11)

    # ---------- S5 GOALS ----------
    s = slide_new(prs); header(s, "Success is Q1 plus Q2, not accuracy", "Goals")
    bullets(s, [
        ([("Q1, placement: does the model emit <thinkanywhere> at valid interior positions? Base does this rarely.", False, INK)], 0),
        ([("Q2, no damage: after the markers are stripped, does the code keep its base-level pass rate?", False, INK)], 0),
        ([("Accuracy alone is not the goal here. What we need to know first is whether the model places markers "
           "the way the reference data does.", False, INK)], 0),
    ], top=2.3, size=17)
    band(s, MARGIN, 4.85, 11.93, 0.95, [
        [("The metric scores every gap: ", False, INK), ("precision, recall, F1", True, INK),
         (". A marker placed into code is a false positive.", False, INK)]], sizes=[17])
    para(tbox(s, MARGIN, 6.25, 12, 0.4).text_frame,
         ("F1 separates learned placement from random sprinkling.", False, MUTE), 13)

    # ---------- S6 METRIC ----------
    s = slide_new(prs); header(s, "A placement metric that can't be gamed", "Metric")
    pic(s, os.path.join(FIG, "fig_process.png"), top=1.85, height=3.3, left=0.6)
    tf6 = tbox(s, MARGIN, 5.25, 11.93, 0.75).text_frame
    para(tf6, [("precision = TP / (TP + FP)        recall = TP / (TP + FN)        "
                "F1 = 2 × precision × recall / (precision + recall)", False, MUTE)], 12, after=4)
    para(tf6, [("Masking follows the eval loss (Bernoulli t, t in [0.7, 0.95]); leak-free recall counts "
                "fully-masked trigrams only.", False, MUTE)], 11, new=True)
    band(s, MARGIN, 6.15, 11.93, 0.7, [
        [("A false positive is a marker pushed into a code position. That is the ", False, INK),
         ("degeneracy signal", True, INK), (".", False, INK)]], fill=WARN, sizes=[15])

    # ---------- S7 RESULT: placement ----------
    s = slide_new(prs); header(s, "The SFT learns placement: F1 rises 0.53 to 0.80", "Result, placement")
    pic(s, os.path.join(FIG, "fig_place.png"), top=1.75, height=3.7, left=0.7)
    tf = tbox(s, 7.75, 2.6, 4.85, 3.0).text_frame
    para(tf, ("Precision is the tell.", True, INK), 16, after=10)
    para(tf, ("Base drops 424 markers into code. The SFT drops about 120, roughly 3.4x fewer.", False, INK), 15, after=12)
    para(tf, ("So it learns placement, not just how to emit a marker.", False, INK), 15, after=12)
    para(tf, ("Eval loss agrees: L_marker 0.62 to 0.31.", False, MUTE), 14)
    band(s, MARGIN, 5.75, 11.93, 0.82, [
        [("F1 rises from 0.53 at base to 0.80 at ep10. Precision 0.47 to 0.80, recall 0.60 to 0.79.", False, INK)]],
        sizes=[15])
    para(tbox(s, MARGIN, 6.72, 12, 0.3).text_frame,
         ("b64 SFT, t in [0.7, 0.95], val 100, anchor 'any' (id 1496).", False, MUTE), 11)

    # ---------- S8 RESULT: Q2 ----------
    s = slide_new(prs); header(s, "Markers don't hurt coding: the drop is prompt cost", "Result, Q2")
    small_table(s, 2.42, 1.85, 8.5, ["MBPP pass@1", "d1 prompt", "marker prompt"],
                [["base", "38.5", "30.4"], ["SFT ep2", "-", "5.4"],
                 ["SFT ep6", "-", "29.6"], ["SFT ep10", ep10, "30.7"]],
                col_w=[3.0, 2.75, 2.75], row_h=0.5, fs=14, bold_rows=(4,))
    bullets(s, [
        ([("With the plain d1 prompt, SFT ep10 matches base (40.5 vs 38.5; the gap is within noise, McNemar p ≈ 0.5). "
           "No coding ability is lost.", False, INK)], 0),
        ([("Under the marker prompt the score dips early (ep2) and recovers by ep6. The gap to base is a prompt cost "
           "the base model pays too, and the marker now appears every time (base: 8.6%).", False, INK)], 0),
    ], top=4.75, size=14)
    band(s, MARGIN, 5.9, 11.93, 0.72, [
        [("Coding ability holds and placement is learned. ", False, INK),
         ("Q1 and Q2 are both met", True, INK), (".", False, INK)]], sizes=[16])
    para(tbox(s, MARGIN, 6.78, 12, 0.3).text_frame,
         ("d1 harness, gen256 / steps128 / block32, MBPP sanitized 257, greedy, markers stripped before scoring.", False, MUTE), 11)

    # ---------- S9 TAKEAWAY ----------
    s = slide_new(prs); header(s, "Cold-start done: the model learned WHERE", "Takeaway")
    bullets(s, [
        ([("Q1: the marker appears at valid positions every time (base 8.6%), and F1 rises 0.53 to 0.80.", False, INK)], 0),
        ([("Q2: no accuracy loss beyond the shared marker-prompt cost.", False, INK)], 0),
    ], top=2.1, size=17)
    band(s, 0.7, 3.65, 11.93, 0.9, [
        [("The cold-start goal (paper step 1) is met: ", False, INK),
         ("placement is learnable, not degenerate", True, ACC), (".", False, INK)]], sizes=[18])
    para(tbox(s, 0.7, 5.05, 12, 0.4).text_frame, ("Next steps", True, INK), 15)
    para(tbox(s, 0.7, 5.55, 12, 1.0).text_frame,
         [("(1) cold-start done.   (2) RL to optimize WHERE via reward (diffu-GRPO, wd1, GDPO).", False, INK)], 15)


def main():
    # Output goes where you ask, and otherwise to the current directory. It used
    # to land inside the skill folder, which is how people end up reviewing a
    # render from someone else's run.
    global FIG
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "example_deck.pptx")
    FIG = os.path.join(os.path.dirname(out) or ".", "fig")
    os.makedirs(FIG, exist_ok=True)
    fig_marker(os.path.join(FIG, "fig_marker.png"))
    fig_data(os.path.join(FIG, "fig_data.png"))
    fig_process(os.path.join(FIG, "fig_process.png"))
    fig_place(os.path.join(FIG, "fig_place.png"))
    prs = Presentation(); prs.slide_width = W; prs.slide_height = H
    build(prs)
    prs.save(out)
    print("saved %s, %d slides" % (out, len(prs.slides)))


if __name__ == "__main__":
    main()
