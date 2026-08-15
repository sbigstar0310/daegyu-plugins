---
name: qa-preflight
description: Bring a React Native / Expo QA environment to a testable state before GUI testing - validate project config, verify the pinned agent-device driver and Node floor, confirm Metro, and hand device/app readiness to `agent-device doctor`. Use immediately before driving an app on an iOS Simulator or Android emulator.
when_to_use: At the start of a mobile QA session; when the app will not launch, no device is found, the driver is missing or mismatched, or the environment must be recovered mid-test.
---

# QA Preflight — reaching a testable state

Preflight answers one question: **can testing start, and if not, exactly what
must the human do?** It does not test anything and it does not judge screens.

## Scope boundary

Preflight is **out-of-band environment verification**. It runs before the QA
loop starts and it is the *only* place version and toolchain probing is allowed.

That is why it does not contradict the official agent-device guidance to
"start immediately, do not probe first with `--help` / `--version` / `devices`".
That rule governs the **agent's task loop**. Preflight is not in the loop — it is
the setup step that makes the loop's assumptions true. Once preflight passes,
the agent opens the app and starts working without further probing.

**Preflight never opens a session, never snapshots, and never taps.** Device
lifecycle and the screen belong to agent-device and to the QA agent
respectively. Duplicating either here is how the two drift apart.

---

## 0. The fast path: run the bundled script

```bash
mobile-qa-preflight all --help      # read the real contract first
mobile-qa-preflight all             # or: ios | android
mobile-qa-preflight all --start-metro
```

It performs every check below and prints a machine-readable block on **stdout**
(human progress goes to stderr):

```
=== MOBILE-QA-PREFLIGHT-SUMMARY ===
PREFLIGHT_RESULT=OK|DEGRADED|BLOCKED|CONFIG_ERROR
NODE_VERSION=      DRIVER_VERSION=     DRIVER_SOURCE=
METRO=UP|DOWN|PORT_BUSY_NOT_METRO|STARTED
IOS_STATUS=READY|BLOCKED|UNAVAILABLE|NOT_REQUESTED     IOS_FIX=<command>
ANDROID_STATUS=...                                     ANDROID_FIX=<command>
=== END-SUMMARY ===
```

Exit codes: `0` OK, `1` DEGRADED (one platform ready), `2` usage, `3` BLOCKED,
`4` config error.

**If the script's actual output disagrees with this document, trust the script.**
If it is missing entirely (`command not found`), fall through to the manual
steps below — its absence is not itself a failure.

**Do not start `--start-metro` without being asked.** An unannounced background
process is worse than a clear error message.

---

## 1. Config (the premise of everything else)

```bash
cat "$CLAUDE_PROJECT_DIR/.claude/mobile-qa.config.json"
```

Required for the platform being tested:

| Key | Meaning |
| --- | --- |
| `agentDevice.ios.app` | iOS bundle id (or app name agent-device can resolve) |
| `agentDevice.ios.device` | target simulator; empty means "let agent-device choose" |
| `agentDevice.android.app` | Android package id |
| `agentDevice.android.device` | target emulator/serial; empty means "let agent-device choose" |
| `metro.port` | default `8081` |
| `metro.startCommand` | default `npm start` |
| `reportLanguage` | language for report prose; default `en` |
| `auth.*` | testIDs and markers — see the login skills |

**Missing config is `BLOCKED`, not a puzzle to solve.** Do not infer a bundle id
from `app.json`, and do not pick a device because only one is booted. Report the
gap and stop.

Credentials are never here. They come from `MOBILE_QA_EMAIL` /
`MOBILE_QA_PASSWORD` or `.claude/mobile-qa.local.json` (gitignored).

---

## 2. Driver: pinned agent-device + Node floor

```bash
mobile-qa-device --resolve
```

Prints the Node and agent-device actually resolved, and the pinned range. It
**fails loudly rather than silently running the wrong build**:

| Exit | Meaning | Action |
| --- | --- | --- |
| `0` | resolved inside the pinned range | continue |
| `3` | no Node >= the pin floor (22.12) | **BLOCKED** — print its instructions verbatim |
| `4` | no agent-device at the pinned version | **BLOCKED** — print its instructions verbatim |
| `5` | pin file missing/unreadable | **BLOCKED** — the plugin is damaged |

The launcher already searches nvm, fnm, volta and asdf for a suitable Node even
when the shell's default is older, so exit `3` means the machine genuinely has
none. On such a host it prints the exact install command and the
`MOBILE_QA_NODE_BIN` escape hatch.

**Never resolve a BLOCKED driver yourself.** Do not `npm install`, do not
`npx -y agent-device@latest`, do not fall back to an unpinned global. Installing
and upgrading are user-owned setup steps. Report and stop.

If `mobile-qa-device --resolve` warns that a bare `agent-device` on PATH is a
**different** version, that is a real hazard: any command written as bare
`agent-device` would run the unpinned build. Use `mobile-qa-device` explicitly.

---

## 3. Metro

```bash
curl -s -m 4 "http://127.0.0.1:${METRO_PORT:-8081}/status"     # expect: packager-status:running
```

Three distinct outcomes — do not collapse them:

- **running** → proceed.
- **port held, but not Metro** → something else owns the port. Report the pid;
  do not kill it unasked.
- **nothing listening** → Metro is down. Report it with the start command from
  config. Start it only if explicitly permitted.

A **release/standalone build does not need Metro**. Metro matters for dev-client
and Expo Go builds. If the app under test is a release build, note it and move on.

> Metro being down does not always stop the app from launching — a dev client
> can render a previously cached bundle. That is a **stale-bundle hazard**, not a
> pass: you would be testing yesterday's JavaScript. Treat it as BLOCKED unless
> the request explicitly concerns cached behavior.

---

## 4. Device, app installation and toolchain

**Hand this to the driver. Do not reimplement it.**

```bash
mobile-qa-device doctor --platform ios      --app "<agentDevice.ios.app>"
mobile-qa-device doctor --platform android  --app "<agentDevice.android.app>"
```

`doctor` covers what previous versions of this skill did by hand — booted
devices, the app being installed, Xcode/simctl and Android SDK/adb availability,
and driver prerequisites. Its **exit code is the contract**; its exact output
text is version-specific, so read it for the human but do not parse it.

Non-zero `doctor` means **BLOCKED**. Surface its message, which carries the
corrective hint, plus the re-run command.

If the app is simply not installed, the fix is the project's own build command
(for example `npx expo run:ios` / `npx expo run:android`). **Building is a
user-owned step** — a build can take many minutes and mutate the working tree.
Report the command; do not run it unasked.

---

## 5. Login state — the largest turn saving available

Do **not** blindly run the login flow. Most RN apps persist the auth session, so
the app is frequently already logged in, and a needless login flow is the single
most expensive avoidable step in a QA run.

Determine state from the **first snapshot of the session** — the one `open`
returns — by matching `auth.loggedInMarkers` and `auth.loggedOutMarkers`.
That costs no extra turn.

- logged-in markers present → **skip login entirely**
- logged-out markers present → run the platform login skill
- **neither present** → you are on some third screen (splash, onboarding,
  update prompt, permission dialog). Do **not** guess. Re-observe after settling,
  and if it persists, report what you actually see.

Both marker sets must be **testID/role-based wherever the app supports it**.
Bare text markers are collision-prone and break across locales; a false positive
here runs the entire QA pass against the wrong screen.

---

## 6. Clearing obstructions

**dev-client LogBox overlay** (both platforms): a red error overlay swallows the
first tap and hides content. If `quirks.dismissLogBox` is true, dismiss it before
testing — and **report that it was present**, since it usually means the app
logged an error worth knowing about.

**The Expo dev-launcher menu is not your app.** A dev-client build that is
launched cold, without a deep link into the running dev server, stops on the
**development-server selection menu**. The process is running and the app looks
"launched", but every element you observe belongs to the launcher, not to the
app. Neither `loggedInMarkers` nor `loggedOutMarkers` will match, and the usual
mistake is to report that as an app defect or as an unknown third screen.
Recognise it, connect to the dev server (deep link or tap the entry for the
running Metro), confirm the app's own first screen, and only then judge login
state. This is Expo dev-client behavior and is independent of which driver you
use.

**Permission dialogs and system prompts** are part of the app's real startup.
Do not pre-clear them unless the flow under test says to; how the app handles
them is often the thing being tested.

**Do not reset the IME, clear app data, or wipe a device.** agent-device ships
its own test IME and manages text entry; the Gboard-corruption workaround that
used to live here is obsolete and now actively harmful.

---

## 7. Done criteria

Preflight passes only when **all** hold:

1. Config present and valid for the requested platform(s)
2. `mobile-qa-device --resolve` exits `0`
3. Metro running, or the build under test provably does not need it
4. `doctor` exits `0` for each requested platform

Anything else is `DEGRADED` (one platform usable — say which, and test only that)
or `BLOCKED` (report the exact fix command and stop).

**Never report a preflight as OK that you did not actually verify.** A false OK
turns into a confusing test failure several turns later, attributed to the app.
