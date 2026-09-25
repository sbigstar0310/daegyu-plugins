# Bundled assets

Everything here is offline. No network call is needed to search, pick and place
an icon in a deck.

## icons/

30 Lucide glyphs, already recoloured to ink black at stroke width 1.6 and
rasterised to 400 x 400 RGBA PNG with a transparent background. `svg/` holds the
upstream source of each one, unmodified, so the recolour is reproducible at any
size.

Licence: ISC, see `icons/LICENSE`. Attribution is not required on a slide.

## logos/

8 Simple Icons brand marks, same treatment. Licence: CC0 1.0, see
`logos/LICENSE`. The marks themselves are trademarks of their owners: use them to
name a tool, not to imply endorsement.

## index/

- `lucide-tags.json`: all 1,820 Lucide icon names with their synonym tags. This
  is what lets `scripts/icons.py search retry` answer `refresh-cw, rotate-cw,
  list-restart` without a network call.
- `simple-icons.json`: all 3,459 Simple Icons brands as `slug` to `title`.

Both are snapshots. `python3 scripts/icons.py refresh-index` pulls current ones.

- `google-fonts.txt`: all 1,946 Google Fonts family names, one per line, taken
  2026-09-25. `check_layout.py --portable` reads it for a Google Slides target
  and never fetches it. Refresh it with:

      curl -s https://fonts.google.com/metadata/fonts | python3 -c 'import json, sys; t = sys.stdin.read(); print("\n".join(sorted({f["family"] for f in json.loads(t[t.index("{"):])["familyMetadataList"]})))' > assets/index/google-fonts.txt

- `google-fonts-korean.txt`: the 38 of those with a Korean subset, taken the same
  day. `--portable` counts Hangul as covered when a run's `ea` font is one of
  them. Refresh it with:

      curl -s https://fonts.google.com/metadata/fonts | python3 -c 'import json, sys; t = sys.stdin.read(); print("\n".join(sorted({f["family"] for f in json.loads(t[t.index("{"):])["familyMetadataList"] if "korean" in f["subsets"]})))' > assets/index/google-fonts-korean.txt

## tokens_white.py and starter_build.py

The default instance: a white deck at 10 x 5.625 in with Inter, described in
`references/instance-white-ref.md`. `starter_build.py` builds a three slide deck
from those tokens and is the fastest way to check that python-pptx, the font and
the renderer all work before you build anything real.
