---
name: qa-android-login
description: Login policy for Android GUI QA of a React Native / Expo app - which control may be tapped, how credentials are handled, what counts as success or as rejected credentials, and when to stop retrying. Mechanics are delegated to agent-device. Use when Android QA has determined that a login is actually required.
when_to_use: When the first snapshot of an Android session shows logged-out markers and the flow under test requires an authenticated session.
---

# Android login — policy, not mechanics

This skill deliberately contains **no command syntax**. Tapping, typing,
submitting and observing are agent-device's job, and its own version-matched
help is the source of truth for how they work.

What lives here is the part agent-device cannot know: **which** control to touch
in *this* app, **what** counts as success, and **when to stop**.

> **Historical note.** This skill used to be ~300 lines of Android mechanics
> plus a 45KB `srr-qa-android-login` shell script: `adb shell input tap` at raw
> device pixels because MCP coordinate taps drifted on high-density screens,
> splitting text into 2-5 character chunks because `mobile_type_keys` dropped
> characters, and `pm clear` on the Gboard package to recover a corrupted IME.
> **All of it is obsolete.** agent-device owns Android text entry and ships its
> own test IME, and addresses elements by semantic ref rather than coordinate.
> If you find yourself reaching for `adb shell input` or `ime set`, stop — you
> are fighting the driver. The old script was deleted; it is recoverable from
> commit `fe4412c` of the daegyu-plugins repository if it is ever needed.
> (Real runs since found one narrow case where agent-device's *own* coordinate
> tap is still the answer: a node whose accessibility rect covers a whole row, so
> its centre point is empty space. That is documented in the agent file, it never
> means `adb shell input`, and it does not apply to login fields.)

---

## Before anything: is login even needed?

Decide from the **first snapshot `open` already returned**. Do not spend a turn
re-observing. If `auth.loggedInMarkers` are present, **skip this skill entirely**.

Every command you run here still carries **`--session android-qa`**, like every
other command in the run. iOS and Android QA execute in parallel and both default
to session `default`, so an unnamed session fails with
`Session "default" is already bound to ...`.

### The skip is also a permanent blind spot — say so

A persistently authenticated test account means this skill is skipped on **every**
run. Across the first four real-device sessions it was skipped every single time,
so `loginEntryMarkers`, `testIds`, `errorMarkers` and every login-screen defect
went unexercised while the config's login section looked settled. Absence of
failures there is absence of evidence, not evidence of correctness.

Two obligations follow:

- When you skip login, **state it in the report** — "login skipped (session
  already authenticated); login markers remain unverified" — rather than letting
  silence imply coverage.
- When login itself is what is under test, a logged-out state must be reached
  **deliberately**, by logging out through the app's own logout control. That is
  the only method both safe and reversible. `adb shell pm clear <pkg>` would also
  do it and is **forbidden** — it wipes all app data, not just the session, and
  this agent does not mutate device state that other work depends on. If in-app
  logout is unreachable, report `BLOCKED` and let a human decide.

---

## Inputs — all from config, never guessed

| Key | Use |
| --- | --- |
| `auth.testIds.email` / `.password` / `.submit` | the fields and the submit control |
| `auth.loginEntryMarkers` | **the only controls you may tap to reach the login screen** |
| `auth.loggedInMarkers` | success signal |
| `auth.loggedOutMarkers` | still-logged-out signal |
| `auth.errorMarkers` | credentials rejected (terminal), not "still waiting" |
| `MOBILE_QA_EMAIL` / `MOBILE_QA_PASSWORD` | credentials — env or `.claude/mobile-qa.local.json` |

If a needed key is absent, that is **BLOCKED**. Do not substitute a similar-looking
element from the snapshot.

---

## Rule 1 — `loginEntryMarkers` is a safety fence, not a hint

Many apps land on a screen with no credential fields, where something must be
tapped first to reach the login form.

**Tap only controls listed in `auth.loginEntryMarkers`. Nothing else. Ever.**

The screen typically also carries "Sign in with Kakao", "Continue with Google",
"Sign up" and similar. Tapping one of those leaves the app for an external OAuth
flow or starts account creation — either strands the QA run somewhere it cannot
recover from, and account creation can mutate real backend state. On Android an
OAuth hop also hands control to a Custom Tab or another app entirely, which the
session did not open and cannot cleanly close.

If no listed marker is on screen, **report BLOCKED**. Do not go looking for
something that resembles a login button.

---

## Rule 2 — credential handling

- Read credentials from the environment or the gitignored local file. **Never**
  from the committed config, and never from app source.
- **Never echo a password**: not in a report, a log line, a shell command that
  might be transcribed, or a screenshot caption. Refer to it as
  `(MOBILE_QA_PASSWORD)`.
- **Never pass a credential as an `adb` argument.** `adb shell` command lines are
  visible to other processes and land in shell history and logcat. This alone
  disqualifies the old ADB-based login path.
- Prefer agent-device's secret-safe fill facility if the installed version offers
  one — check `agent-device help scripting` **only if** you intend to record the
  session to a `.ad` script, since a naively recorded script would embed the
  password in a file.
- **Do not screenshot while a password field is focused or filled.**

---

## Rule 3 — deciding the outcome

After submitting, the state is exactly one of four. Distinguishing them is the
entire point of this skill:

| Observation | Meaning | Action |
| --- | --- | --- |
| any `loggedInMarkers` present | **success** | proceed with the test |
| any `errorMarkers` present | **credentials rejected** | terminal — do NOT retry |
| still `loggedOutMarkers`, no error | submission not processed yet | wait and re-observe **once** |
| none of the above | unknown third screen | do not guess — report what you see |

**Rejected credentials are terminal.** Retrying with the same credentials cannot
succeed, and repeated failures can trigger server-side rate limiting or an
account lockout, which then breaks every subsequent QA run — including for other
people using the same test account. Report `BLOCKED: credentials rejected` and stop.

**Retry budget: at most one retry**, and only for the "not processed yet" case.
Prefer a settled observation over a blind retry.

Judge success by markers, **not** by "the screen looks different". A validation
error, a captcha, a forced-update modal and a terms prompt all change the screen
without logging anyone in.

---

## Rule 4 — verify markers before trusting them

`loggedInMarkers` decide whether an entire QA pass runs against the right screen.
A collision-prone marker (bare visible text such as `Star`, `My`, or a
single-word label) can match the logged-out onboarding screen and produce a
confident false positive.

`errorMarkers` are especially suspect when they were transcribed from a locale
JSON file rather than observed on a device: the rendered string may differ, may
be truncated, or may never appear at all. An `errorMarker` that never matches
silently downgrades "credentials rejected" into "still waiting", and you retry
into a lockout.

On the **first run against a new app or a changed config**, confirm each marker
against a real snapshot in both states, and report any that were wrong as a
`CORRECTION` in the `## Learned` block. Prefer testID/role-based markers; treat
bare text as provisional.

**A testID marker can fail to match on Android for a reason that has nothing to
do with the app's state.** `testID` surfaces as the `identifier` field of
`snapshot -i --json` (the plain-text snapshot omits it entirely), and that field
is not reliably populated: on a release-type build the app's views carried it
normally, while on a debug build of the same app every app view had an **empty**
`identifier` and only true native components exposed one. Which is authoritative
is unknown.

So a marker that "does not match" may mean *unmatched*, not *absent*. Re-read
with `--json`, cross-check against a visible label or a screenshot before
concluding you are logged out, and say which build type you were on. Marker
configuration that depends on `identifier` **alone** is fragile here.

---

## When this procedure does not fit

Stop and report, rather than improvising, when the app uses SSO/OAuth-only login,
requires an MFA code, presents a captcha, or forces a password change or app
update before proceeding. These need a human decision or a different test
account. **Improvised authentication is how a QA run mutates real account state.**
