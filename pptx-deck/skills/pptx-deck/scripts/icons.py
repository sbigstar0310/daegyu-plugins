#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find, fetch and recolour icons. Search works with no network at all.

    python3 scripts/icons.py search retry
    python3 scripts/icons.py search "policy check" --limit 12
    python3 scripts/icons.py add shield-check refresh-cw --out build/icons
    python3 scripts/icons.py logo kubernetes docker --out build/logos
    python3 scripts/icons.py sheet --out build/icon-sheet.png
    python3 scripts/icons.py refresh-index

30 Lucide glyphs and 8 brand marks are already bundled in assets/, ready to place.
Use those first. This is for the icon the slide needs that is not in the bundle,
and search reads the bundled index, so choosing one costs nothing and needs no
network. Only `add`, `logo` and `refresh-index` go out to the internet.

Fetching is tried against three CDNs in turn, because the obvious repository
guess is wrong in both projects: Lucide lives under lucide-icons/lucide, not
lucide/lucide, and Simple Icons is on the develop branch. A bare curl at the wrong
URL writes an empty file and reports success, so anything under 50 bytes is
treated as a failure here and the next source is tried.

Icons are recoloured to your ink and rasterised with an alpha channel. Lucide's
default stroke width of 2 reads heavy next to body text at small sizes, so the
default here is 1.6.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
INDEX = os.path.join(ASSETS, "index")

MIN_BYTES = 50   # anything smaller is an error page or an empty file

LUCIDE_SOURCES = [
    "https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/{name}.svg",
    "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/{name}.svg",
    "https://unpkg.com/lucide-static@latest/icons/{name}.svg",
]
SIMPLE_SOURCES = [
    "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{name}.svg",
    "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{name}.svg",
    "https://unpkg.com/simple-icons@latest/icons/{name}.svg",
]
LUCIDE_TAGS_URL = "https://cdn.jsdelivr.net/npm/lucide-static@latest/tags.json"
SIMPLE_DATA_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/data/simple-icons.json"


# ---------------------------------------------------------------- index
def load_index(which):
    path = os.path.join(INDEX, "lucide-tags.json" if which == "lucide" else "simple-icons.json")
    if not os.path.exists(path):
        sys.stderr.write("no %s index at %s. Run: python3 scripts/icons.py refresh-index\n"
                         % (which, path))
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score(name, tags, terms):
    """Rank a candidate. An exact name match wins, then a whole word of the name,
    then a prefix, then a tag.

    A bare substring match does not count. Allowing it made "gate" return the
    brands frigate, kongregate and progate, which is worse than returning
    nothing: a plausible looking list sends you off to place the wrong glyph.
    So a substring only scores when it is a whole hyphen separated part of the
    name, or the name starts with it.
    """
    sc = 0
    words = name.replace("-", " ").split()
    for t in terms:
        if name == t:
            sc += 100
        elif t in words:
            sc += 60
        elif name.startswith(t) and len(t) >= 3:
            sc += 35
        if any(t == tag for tag in tags):
            sc += 30
        elif any(t in tag.split() for tag in tags):
            sc += 18
    return sc


def bundled_names():
    out = set()
    for sub in ("icons", "logos"):
        d = os.path.join(ASSETS, sub)
        if os.path.isdir(d):
            out |= {os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".png")}
    return out


def cmd_search(a):
    terms = [t.lower() for t in re.split(r"[\s,]+", " ".join(a.query)) if t]
    if not terms:
        return 2
    lucide = load_index("lucide")
    simple = {} if a.icons_only else load_index("simple")

    def sweep(words, weight):
        found = {}
        for name, tags in lucide.items():
            sc = score(name, [t.lower() for t in tags], words)
            if sc:
                found[("icon", name)] = (sc * weight, ", ".join(tags[:6]))
        for slug, title in simple.items():
            sc = score(slug, [title.lower()], words)
            if sc:
                found[("logo", slug)] = (sc * weight, title)
        return found

    # A direct hit always outranks a related one, however many borrowed tags
    # the related one happens to match.
    hits = {k: (v[0] + 1000, v[1]) for k, v in sweep(terms, 1.0).items()}

    # One round of expansion. A word like "retry" is a tag on exactly one icon,
    # which is a true but useless answer. Borrowing that icon's other tags finds
    # the family it belongs to, scored at a discount so the direct hit stays on
    # top.
    related = {}
    if len(hits) < a.limit:
        seeds = sorted(((v[0], k) for k, v in hits.items() if k[0] == "icon"), reverse=True)[:3]
        extra = []
        for _sc, (_kind, name) in seeds:
            extra += [t.lower() for t in lucide.get(name, [])]
        extra = [t for t in dict.fromkeys(extra) if t not in terms]
        if extra:
            for key, val in sweep(extra, 0.4).items():
                if key not in hits:
                    related[key] = val

    if not hits and not related:
        print("nothing matched %s" % " ".join(terms))
        print("Try a plainer word. The index holds %d icons and %d brands."
              % (len(lucide), len(load_index("simple"))))
        return 1

    have = bundled_names()
    rows = ([(v[0], k[0], k[1], v[1], "") for k, v in hits.items()]
            + [(v[0], k[0], k[1], v[1], "related") for k, v in related.items()])
    rows.sort(key=lambda r: (-r[0], r[2]))
    for _sc, kind, name, why, rel in rows[:a.limit]:
        mark = "bundled" if name in have else rel
        print("  %-5s %-26s %-8s %s" % (kind, name, mark, why[:54]))
    if len(rows) > a.limit:
        print("  ... %d more" % (len(rows) - a.limit))
    return 0


def cmd_refresh_index(a):
    os.makedirs(INDEX, exist_ok=True)
    tags = json.loads(fetch(LUCIDE_TAGS_URL).decode("utf-8"))
    with open(os.path.join(INDEX, "lucide-tags.json"), "w", encoding="utf-8") as f:
        json.dump(tags, f, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    print("lucide       %d icons" % len(tags))

    data = json.loads(fetch(SIMPLE_DATA_URL).decode("utf-8"))
    index = {}
    for e in data:
        index[e.get("slug") or slugify(e["title"])] = e["title"]
    with open(os.path.join(INDEX, "simple-icons.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    print("simple icons %d brands" % len(index))
    return 0


SLUG_REPL = {"+": "plus", ".": "dot", "&": "and", "\u0111": "d", "\u0127": "h",
             "\u0131": "i", "\u0138": "k", "\u0140": "l", "\u0142": "l",
             "\u00df": "ss", "\u0167": "t", "\u00f8": "o"}


def slugify(title):
    import unicodedata
    out = []
    for ch in title.lower():
        if ch.isdigit() or ("a" <= ch <= "z"):
            out.append(ch)
        else:
            out.append(SLUG_REPL.get(ch, ""))
    s = unicodedata.normalize("NFD", "".join(out))
    return "".join(c for c in s if not unicodedata.combining(c))


# ---------------------------------------------------------------- fetching
def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "pptx-deck/2"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_svg(name, sources):
    """Try each CDN in turn. A body under MIN_BYTES is a failure, not a file: a
    bare request at a wrong URL happily writes an empty one."""
    tried = []
    for tmpl in sources:
        url = tmpl.format(name=name)
        try:
            body = fetch(url)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            tried.append("%s -> %s" % (url, e))
            continue
        if len(body) < MIN_BYTES or b"<svg" not in body:
            tried.append("%s -> %d bytes, not an svg" % (url, len(body)))
            continue
        return body, url
    raise RuntimeError("could not fetch %r:\n    %s" % (name, "\n    ".join(tried)))


# ---------------------------------------------------------------- rasterising
def rasteriser():
    for exe, kind in (("rsvg-convert", "rsvg"), ("inkscape", "inkscape")):
        p = shutil.which(exe)
        if p:
            return p, kind
    try:
        import cairosvg  # noqa: F401
        return None, "cairosvg"
    except ImportError:
        pass
    return None, None


def to_png(svg_bytes, out_png, px):
    exe, kind = rasteriser()
    if kind is None:
        raise RuntimeError(
            "no SVG rasteriser. Install one:\n"
            "    brew install librsvg              # macOS, gives rsvg-convert\n"
            "    sudo apt-get install -y librsvg2-bin\n"
            "    %s -m pip install cairosvg" % os.path.basename(sys.executable))
    if kind == "rsvg":
        subprocess.run([exe, "-w", str(px), "-h", str(px), "-o", out_png, "-"],
                       input=svg_bytes, check=True, capture_output=True)
    elif kind == "inkscape":
        tmp = out_png + ".svg"
        with open(tmp, "wb") as f:
            f.write(svg_bytes)
        subprocess.run([exe, tmp, "-w", str(px), "-h", str(px), "-o", out_png],
                       check=True, capture_output=True)
        os.remove(tmp)
    else:
        import cairosvg
        cairosvg.svg2png(bytestring=svg_bytes, write_to=out_png,
                         output_width=px, output_height=px)
    return out_png


def recolour_lucide(svg, color, stroke):
    s = svg.decode("utf-8")
    s = s.replace('stroke="currentColor"', 'stroke="%s"' % color)
    s = re.sub(r'stroke-width="[^"]*"', 'stroke-width="%s"' % stroke, s)
    if "stroke=" not in s:
        s = s.replace("<svg", '<svg stroke="%s"' % color, 1)
    return s.encode("utf-8")


def recolour_simple(svg, color):
    s = svg.decode("utf-8")
    s = re.sub(r'fill="[^"]*"', 'fill="%s"' % color, s)
    if 'fill="%s"' % color not in s:
        s = s.replace("<svg", '<svg fill="%s"' % color, 1)
    return s.encode("utf-8")


def cmd_add(a, kind):
    sources = LUCIDE_SOURCES if kind == "icon" else SIMPLE_SOURCES
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    failed = []
    for name in a.names:
        try:
            svg, url = fetch_svg(name, sources)
        except RuntimeError as e:
            sys.stderr.write("%s\n" % e)
            failed.append(name)
            continue
        raw = os.path.join(out, "svg", name + ".svg")
        with open(raw, "wb") as f:
            f.write(svg)
        inked = (recolour_lucide(svg, a.color, a.stroke) if kind == "icon"
                 else recolour_simple(svg, a.color))
        png = os.path.join(out, name + ".png")
        try:
            to_png(inked, png, a.px)
        except RuntimeError as e:
            sys.stderr.write("%s\n" % e)
            return 2
        except subprocess.CalledProcessError as e:
            sys.stderr.write("rasteriser failed on %s: %s\n" % (name, e.stderr[:200]))
            failed.append(name)
            continue
        size = os.path.getsize(png)
        if size < MIN_BYTES:
            sys.stderr.write("%s rasterised to %d bytes, which is nothing\n" % (name, size))
            failed.append(name)
            continue
        print("  %-26s %5d px  %6d bytes  from %s" % (name, a.px, size, url.split("/")[2]))
    if failed:
        print("\nfailed: %s" % ", ".join(failed))
        print("Check the spelling with: python3 scripts/icons.py search <word>")
        return 1
    return 0


def cmd_sheet(a):
    """A contact sheet, so you pick a glyph by looking at it rather than by its
    name. With no arguments it shows everything already bundled. With names it
    shows those, fetching any that are not bundled yet into a cache, which is the
    middle step between search and add: search gives you candidate names, this
    shows you what they look like, then you place the one that reads."""
    from PIL import Image, ImageDraw, ImageFont
    files = []
    if a.names:
        cache = os.path.join(ASSETS, ".cache")
        for name in a.names:
            local = next((p for p in (os.path.join(ASSETS, "icons", name + ".png"),
                                      os.path.join(ASSETS, "logos", name + ".png"),
                                      os.path.join(cache, name + ".png"))
                          if os.path.exists(p)), None)
            if local:
                files.append(local)
                continue
            try:
                svg, _url = fetch_svg(name, LUCIDE_SOURCES)
                inked = recolour_lucide(svg, "#000000", "1.6")
            except RuntimeError:
                try:
                    svg, _url = fetch_svg(name, SIMPLE_SOURCES)
                    inked = recolour_simple(svg, "#000000")
                except RuntimeError as e:
                    sys.stderr.write("%s\n" % e)
                    continue
            os.makedirs(cache, exist_ok=True)
            png = os.path.join(cache, name + ".png")
            to_png(inked, png, 400)
            files.append(png)
    else:
        for sub in ("icons", "logos"):
            d = os.path.join(ASSETS, sub)
            if os.path.isdir(d):
                files += sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    if not files:
        sys.stderr.write("nothing to draw\n")
        return 1
    cell, pad, label = 96, 18, 16
    cols = a.columns
    rows = (len(files) + cols - 1) // cols
    W = cols * (cell + pad) + pad
    H = rows * (cell + pad + label) + pad
    sheet = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.expanduser("~/Library/Fonts/Inter-Regular.otf"), 11)
    except (OSError, IOError):
        font = ImageFont.load_default()
    for i, path in enumerate(files):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + pad + label)
        im = Image.open(path).convert("RGBA")
        im.thumbnail((cell, cell))
        sheet.alpha_composite(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        draw.text((x + cell // 2, y + cell + 3), os.path.splitext(os.path.basename(path))[0],
                  fill=(60, 60, 60, 255), font=font, anchor="ma")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    sheet.convert("RGB").save(a.out)
    print("wrote %s, %d glyphs in %d columns" % (a.out, len(files), cols))
    print("Look at it before you place one. A name that sounds right often draws wrong.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="offline search over the bundled indexes")
    s.add_argument("query", nargs="+")
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--icons-only", action="store_true", help="skip brand logos")

    for cmd, helptext in (("add", "fetch Lucide icons"), ("logo", "fetch Simple Icons brand marks")):
        s = sub.add_parser(cmd, help=helptext)
        s.add_argument("names", nargs="+")
        s.add_argument("--out", default="build/icons" if cmd == "add" else "build/logos")
        s.add_argument("--color", default="#000000")
        s.add_argument("--px", type=int, default=400)
        if cmd == "add":
            s.add_argument("--stroke", default="1.6",
                           help="Lucide ships 2, which reads heavy next to body text")

    s = sub.add_parser("sheet", help="a contact sheet, of named glyphs or of the whole bundle")
    s.add_argument("names", nargs="*", help="leave empty to show everything bundled")
    s.add_argument("--out", default="build/icon-sheet.png")
    s.add_argument("--columns", type=int, default=8)

    sub.add_parser("refresh-index", help="re-download both search indexes")

    a = ap.parse_args()
    if a.cmd == "search":
        return cmd_search(a)
    if a.cmd == "add":
        return cmd_add(a, "icon")
    if a.cmd == "logo":
        a.stroke = None
        return cmd_add(a, "logo")
    if a.cmd == "sheet":
        return cmd_sheet(a)
    if a.cmd == "refresh-index":
        return cmd_refresh_index(a)
    return 2


if __name__ == "__main__":
    sys.exit(main())
