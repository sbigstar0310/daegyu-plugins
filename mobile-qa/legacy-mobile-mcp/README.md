# legacy-mobile-mcp — TRANSITIONAL, do not extend

This directory holds the **complete pre-migration plugin**, from when the driver
was `@mobilenext/mobile-mcp` instead of Callstack `agent-device`.

Nothing here is loaded. There is no `.claude-plugin/` manifest, and the `agents/`
and `skills/` directories are not at the paths Claude Code scans, so these files
are inert. They are kept as reference only.

## Why it was kept

The migration deleted nothing. These files carry real accumulated knowledge —
months of observed device behavior — and if the migration has to be reverted, or
if a behavior turns out to have been load-bearing, this is the diff base.

## Contents

| Path | Superseded by |
| --- | --- |
| `plugin.json` | `../.claude-plugin/plugin.json` |
| `README-original.md` | `../README.md` |
| `agents/mobile-qa-ios.md` | `../agents/mobile-qa-ios.md` |
| `agents/mobile-qa-android.md` | `../agents/mobile-qa-android.md` |
| `skills/qa-preflight/SKILL.md` | `../skills/qa-preflight/SKILL.md` |
| `skills/qa-ios-login/SKILL.md` | `../skills/qa-ios-login/SKILL.md` |
| `skills/qa-android-login/SKILL.md` | `../skills/qa-android-login/SKILL.md` |
| `bin/srr-qa-preflight` (41KB) | `../bin/mobile-qa-preflight` |
| `bin/srr-qa-state` (23KB) | agent-device `snapshot` / assertions |
| `bin/srr-qa-android-login` (45KB) | agent-device `fill` / `press` and `.ad` replay |
| `examples/*` | `../examples/*` |

## What specifically became obsolete

Three classes of workaround, which together were most of the old plugin's bulk:

1. **Text-entry chunking** — splitting input into 2–5 character pieces because
   `mobile_type_keys` dropped characters. agent-device owns Android text entry.
2. **IME recovery** — `pm clear` on the Gboard package after the soft keyboard
   got into a corrupted state. agent-device ships its own test IME.
3. **Coordinate math** — converting iOS logical points to screenshot pixels, and
   `adb shell input tap` at raw device pixels on high-density Android screens.
   agent-device addresses elements by semantic ref (`@e7`).

Also obsolete: `srr-qa-state`'s `STATE=UNKNOWN` / `IOS_SHELL_DETECTION_LIMIT`
result. It existed because a shell cannot read the iOS view hierarchy. The driver
now returns an interactive snapshot from `open`, so login state is read directly
from the first observation at no extra turn cost.

## Delete this directory when

agent-device has been proven on real hardware for both platforms — at minimum a
login flow and one multi-screen flow passing on an iOS Simulator and an Android
emulator, with the `_VERIFY_ON_FIRST_RUN` items in the example config confirmed.

Keeping two descriptions of the same procedure indefinitely recreates exactly the
drift problem this migration set out to eliminate.
