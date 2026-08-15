---
name: qa-ios-login
description: Login policy for iOS GUI QA of a React Native / Expo app - which control may be tapped, how credentials are handled, what counts as success or as rejected credentials, and when to stop retrying. Mechanics are delegated to agent-device. Use when iOS QA has determined that a login is actually required.
when_to_use: When the first snapshot of an iOS session shows logged-out markers and the flow under test requires an authenticated session.
---

# iOS login — policy, not mechanics

This skill deliberately contains **no command syntax**. Tapping, typing,
submitting and observing are agent-device's job, and its own version-matched
help is the source of truth for how they work.

What lives here is the part agent-device cannot know: **which** control to touch
in *this* app, **what** counts as success, and **when to stop**.

> **Historical note.** This skill used to be ~250 lines of iOS mechanics:
> logical-points vs screenshot-pixels conversion, top-left to center math,
> splitting text into 2-5 character chunks because `mobile_type_keys` dropped
> characters, and procedures for `secureTextEntry` fields invisible to the WDA
> accessibility tree. **All of it is obsolete.** agent-device addresses elements
> by semantic ref and owns text entry, so none of those failure modes are yours
> to work around. If you find yourself computing a coordinate, stop — you are
> solving a problem that no longer exists.

---

## Before anything: is login even needed?

Decide from the **first snapshot `open` already returned**. Do not spend a turn
re-observing. If `auth.loggedInMarkers` are present, **skip this skill entirely**.

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

The screen typically also carries "Sign in with Kakao", "Continue with Apple",
"Sign up" and similar. Tapping one of those leaves the app for an external OAuth
flow or starts account creation — either strands the QA run somewhere it cannot
recover from, and account creation can mutate real backend state.

If no listed marker is on screen, **report BLOCKED**. Do not go looking for
something that resembles a login button.

---

## Rule 2 — credential handling

- Read credentials from the environment or the gitignored local file. **Never**
  from the committed config, and never from app source.
- **Never echo a password**: not in a report, a log line, a shell command that
  might be transcribed, or a screenshot caption. Refer to it as
  `(MOBILE_QA_PASSWORD)`.
- Prefer agent-device's secret-safe fill facility if the installed version offers
  one — check `agent-device help scripting` **only if** you intend to record the
  session to a `.ad` script, since a naively recorded script would embed the
  password in a file.
- **Do not screenshot while a password field is focused or filled.** Screenshots
  end up in reports and in artifact directories.

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

On the **first run against a new app or a changed config**, confirm each marker
against a real snapshot in both states, and report any that were wrong as a
`CORRECTION` in the `## Learned` block. Prefer testID/role-based markers; treat
bare text as provisional.

---

## When this procedure does not fit

Stop and report, rather than improvising, when the app uses SSO/OAuth-only login,
requires an MFA code, presents a captcha, or forces a password change or app
update before proceeding. These need a human decision or a different test
account. **Improvised authentication is how a QA run mutates real account state.**
