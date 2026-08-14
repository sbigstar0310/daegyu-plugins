"""Render one candidate slide spec (JSON) to a preview PNG + validate pptx.

usage: render_candidate.py <spec.json> <out.png>
Exits non-zero (and prints ERROR ...) if the spec fails to render or overflows.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import render, preview, design as D


def check_overflow(spec):
    """Cheap guard: flag elements whose declared box clearly leaves the canvas."""
    problems = []
    for e in spec.get("elements", []):
        x = e.get("x", D.MARGIN_X); y = e.get("y", D.CONTENT_TOP)
        w = e.get("w", 0); h = e.get("h", 0)
        if x + (w or 0) > D.SLIDE_W + 0.05:
            problems.append(f"{e.get('type')} x+w={x+w:.2f}>13.33")
        if y + (h or 0) > D.SLIDE_H + 0.05:
            problems.append(f"{e.get('type')} y+h={y+h:.2f}>7.5")
        if y > 7.1:
            problems.append(f"{e.get('type')} y={y:.2f} below body")
    return problems


def main():
    spec_path, out_png = sys.argv[1], sys.argv[2]
    with open(spec_path) as f:
        spec = json.load(f)
    probs = check_overflow(spec)
    # render preview
    img = preview.render_slide(spec)
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    img.save(out_png)
    # validate pptx path renders too
    tmp_pptx = out_png.rsplit(".", 1)[0] + ".pptx"
    render.build([spec], tmp_pptx)
    print("OK", out_png)
    if probs:
        print("WARN overflow:", "; ".join(probs))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR", type(e).__name__, str(e))
        sys.exit(1)
