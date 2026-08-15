# mobile-qa — React Native / Expo GUI QA plugin

Two Claude Code subagents that drive a React Native / Expo app on an iOS
Simulator and an Android emulator **in parallel**, judge it against
project-supplied criteria, and return text reports — plus three procedure skills
and a pinned driver launcher.

**The plugin is not tied to any app.** Every app-specific fact comes from
project configuration.

> The manifest `name` — **`mobile-qa`** — is what namespaces the agents and
> skills (`/mobile-qa:qa-preflight`, `@mobile-qa:mobile-qa-ios`).

## Install

```bash
claude plugin marketplace add sbigstar0310/daegyu-plugins
claude plugin install mobile-qa@daegyu-plugins
```

or, inside a session: `/plugin marketplace add sbigstar0310/daegyu-plugins`
then `/plugin install mobile-qa@daegyu-plugins`.

> ### ⚠️ This plugin deliberately has **no `version` field**
>
> Not in `.claude-plugin/plugin.json`, and not in the marketplace entry in the
> repo-root `.claude-plugin/marketplace.json`. **Do not add one.**
>
> Claude Code pins a consumer to their cached copy for as long as the resolved
> version string is unchanged. If `version` is set in *either* place, pushing
> new commits does nothing for anyone who already installed — they keep the old
> copy until the string is bumped. With `version` omitted, Claude Code
> auto-versions from the resolved git commit SHA, so every push propagates.
> (Setting it in both places is worse: the marketplace entry is then silently
> ignored.)
>
> This plugin is under active development and **has never been run against a
> real device**, so fixes must reach users immediately. Reintroduce a version
> only once it is stable *and* you commit to bumping it on every release.
>
> Consequence, on purpose: `claude plugin validate --strict` reports one
> warning (`version: No version specified`) and therefore exits non-zero. Plain
> `claude plugin validate` passes. That single warning is the intended state,
> not a regression.

**Instruction language is English.** This is a general-purpose plugin, and
instructions in another language also bleed into the host agent's output
language. Reports can still be emitted in the project's language — set
`reportLanguage` in the config (default `en`). SRR's example config uses `ko`.

---

## Driver: Callstack agent-device (pinned)

This plugin used to drive devices through `@mobilenext/mobile-mcp`. It now uses
[agent-device](https://github.com/callstack/agent-device), which **deleted three
entire classes of workaround** rather than merely improving on them:

| Retired workaround | Why it is gone |
| --- | --- |
| Chunking text into 2–5 characters because `mobile_type_keys` dropped characters | agent-device owns Android text entry |
| `pm clear` on Gboard to recover a corrupted IME | agent-device ships its own test IME |
| Converting iOS logical points to screenshot pixels | elements are addressed by semantic ref (`@e7`) |

If you find yourself computing a coordinate or reaching for `adb shell input`,
stop — you are solving a problem that no longer exists.

### Version pin

agent-device is pre-1.0 and the risk is demonstrated, not theoretical: `0.20.4`
shipped a broken npm tarball (fixed the same day in `0.20.5`), and `0.20.0`
removed gesture positionals and expired ref frames after a mutation. Eight
releases landed in 19 days, several with real migration notes. An unpinned
driver means **the skills in this plugin describe a CLI you are not running.**

`agent-device.pin.json` is the single source of truth:

| Field | Value |
| --- | --- |
| `knownGoodVersion` | `0.20.8` |
| allowed range | `0.20.5` … `0.20.8` |
| `rollbackTo` | `0.20.6` |
| `nodeMin` | `22.12.0` (the package declares `engines.node >= 22.12`; npx does **not** enforce it) |

**On the 0.20.7 vs 0.20.8 discrepancy:** both are real, and `0.20.8` is correct.
npm `dist-tags.latest` is `0.20.8` (published 2026-08-11) and the git tag
`v0.20.8` exists; Callstack simply never cut a GitHub *Release* object for it, so
the Releases page stops at `v0.20.7`. GitHub Releases is a publishing convenience,
not the registry. **Pin against npm and the git tag, not the Releases page.**

**Rollback**: edit `knownGoodVersion`/`maxVersion` in the pin file to
`rollbackTo`, delete the cached resolution
(`rm -rf "${TMPDIR:-/tmp}"/mobile-qa-device-resolve-*`), then confirm with
`mobile-qa-device --resolve`. If an MCP server entry is configured, update its
pinned version too and restart the client.

### `bin/mobile-qa-device` — the only way this plugin touches a device

It enforces the pin and the Node floor, then execs agent-device with your
arguments unchanged.

```bash
mobile-qa-device --resolve          # what actually resolved; runs nothing
mobile-qa-device --resolve --json
mobile-qa-device open <app> --platform ios --foreground
```

Exit `3` = no usable Node; `4` = no agent-device at the pinned version; `5` =
pin file damaged. All three print exactly what the human must do.

It resolves Node from `MOBILE_QA_NODE_BIN`, then `PATH`, then nvm, fnm, volta and
asdf — **so a shell sitting on Node 20 still works if a newer Node is installed
anywhere.** (Verified: it found Node 23 via nvm on a shell running Node 20.) On a
host with no suitable Node at all, it lists the versions it did find and prints
the install command plus the `MOBILE_QA_NODE_BIN` escape hatch.

`bin/agent-device` is a shim so that commands written as bare `agent-device`
still hit the pin.

> **Verified, and it is bad news for the shim.** Claude Code *does* put a
> marketplace-installed plugin's `bin/` on `PATH` — measured inside a real
> session after `claude plugin install mobile-qa@daegyu-plugins`, all three
> scripts resolve as bare commands from
> `~/.claude/plugins/cache/<marketplace>/<plugin>/<sha>/bin`. But it **appends**
> that directory, at roughly position 30, *after* `/opt/homebrew/bin` and
> `/usr/local/bin`. So on any machine that has followed the official
> agent-device skill's `npm install -g agent-device@latest`, the **global,
> unpinned binary wins** and the shim never runs.
>
> Treat the shim as a convenience that works only when no global
> `agent-device` exists. `mobile-qa-preflight` warns when a bare `agent-device`
> resolves to a different version — believe it. **Write `mobile-qa-device`,
> not `agent-device`, in anything you commit.**

---

## Boundary against the official skills — quoted verbatim

Callstack publishes official agent-device Claude Skills. This plugin **composes
with them and must never restate them.** Both agent files carry this text:

> **Owned by the official agent-device skills and the installed CLI's own
> `agent-device help <topic>` output — never restated in this plugin:**
> command syntax and flags, session lifecycle (`open` / act / `close`), ref
> semantics (`@e7`, `@e7~s4`), selector rules, text-entry behavior, platform
> backend behavior, gestures, scripting/replay, and version-specific quirks.
>
> **Owned by this plugin — and only this:** parallel iOS+Android QA policy,
> project configuration, login intent, pass/fail criteria, the report contract,
> and the learned-facts handoff.
>
> If the two ever disagree, **the CLI wins**. It is the thing actually running.

The reason is concrete: duplicated command documentation drifts the moment the
pin moves, and two instruction sets then compete for the same context window
while disagreeing about the same command.

### Installing the official skills

They are distributed from the **GitHub repository, not the npm package** — the
published tarball contains no `skills/` directory (verified against
`agent-device@0.20.8`).

```bash
npx skills add callstack/agent-device
```

That provides `agent-device` (the canonical router), `ios-simulator`,
`android-emulator`, and `dogfood`. This plugin's skills are additive policy
layers on top; nothing here replaces them.

### One deliberate deviation

The official `ios-simulator` and `android-emulator` skills say to install with
`npm install -g agent-device@latest`. **This plugin overrides that, and only
that.** `@latest` is precisely the unpinned-drift failure described above. Use
the pinned install below and drive through `mobile-qa-device`.

The official rule "do not probe first with `--help`, `--version`, `devices`,
`snapshot`" is **kept**, and preflight does not violate it: preflight is
out-of-band environment verification that runs *before* the agent's task loop.
Once it passes, the agent opens the app and starts working without probing.

---

## The four-layer model

The plugin needs four things, and **each lives somewhere different.** This
separation is the core of the design.

| # | Layer | Lives in | Contains | Committed? |
| --- | --- | --- | --- | --- |
| 1 | **Plugin (general)** | this plugin (`mobile-qa/`) | agent role, procedure skeleton, report contract | yes |
| 2 | **Config (app facts)** | `$PROJECT_ROOT/.claude/mobile-qa.config.json` | app id, device, testIDs, markers, Metro port | yes |
| 2b | **Secrets** | `$PROJECT_ROOT/.claude/mobile-qa.local.json` or env | test account credentials | **no — gitignored** |
| 3 | **App spec (app intent)** | `$PROJECT_ROOT/.claude/mobile-qa/` | `screens.md`, `flows.md`, pass criteria | yes |
| 4 | **Agent memory (learned)** | `$PROJECT_ROOT/.claude/agent-memory/<agent>/MEMORY.md` | accumulated field knowledge | yes |

One-line test for where something belongs:

- **True for other RN apps too?** → layer 1
- **A fact about this app?** → layer 2
- **What this app is supposed to do?** → layer 3
- **Something learned by running it?** → layer 4

Layer 3 matters most. A general-purpose agent does not know what the app should
do. **Without `flows.md` the agent tests only what was asked and does not invent
pass criteria.**

> **`.gitignore` note.** Layers 2, 3 and 4 are committed layers, but the repo's
> `.gitignore` excluded `.claude/` wholesale, which made them uncommittable and
> silently contradicted this table. Fixed by switching to `.claude/*` plus
> targeted un-ignores — git cannot re-include a file whose *parent directory* is
> excluded, so the trailing `/*` is load-bearing. Secrets stay ignored.

---

## Layout

```
mobile-qa/
├── .claude-plugin/plugin.json    # name: mobile-qa
├── agent-device.pin.json         # THE version pin
├── agents/
│   ├── mobile-qa-ios.md
│   └── mobile-qa-android.md
├── skills/
│   ├── qa-preflight/SKILL.md     # reach a testable state
│   ├── qa-ios-login/SKILL.md     # login POLICY (iOS)
│   └── qa-android-login/SKILL.md # login POLICY (Android)
├── bin/
│   ├── mobile-qa-device          # pinned agent-device launcher
│   ├── agent-device              # shim -> mobile-qa-device
│   └── mobile-qa-preflight       # environment verification
└── examples/                     # copy and edit; never use as-is
    ├── mobile-qa.config.json
    ├── mobile-qa.local.json
    ├── screens.md
    └── flows.md
```

### The pre-migration Mobile MCP version lives in git history

This plugin previously carried a `legacy-mobile-mcp/` directory holding the
complete pre-`agent-device` plugin — the original manifest and README, both
agents, all three skills, all four examples, and ~110KB of superseded shell
(`srr-qa-preflight`, `srr-qa-state`, `srr-qa-android-login`). It was removed
because carrying two descriptions of the same procedure is exactly the drift
problem this migration set out to eliminate.

Nothing was lost. It is recoverable in full from commit **`fe4412c`** of the
`daegyu-plugins` repository:

```bash
git show fe4412c --stat -- mobile-qa/legacy-mobile-mcp
git checkout fe4412c -- mobile-qa/legacy-mobile-mcp     # if you really need it back
```

Its three big workaround classes (text-entry chunking, Gboard IME recovery,
iOS point-to-pixel coordinate math) are obsolete under agent-device and are
described in the table at the top of this README. One fact that was *not*
driver-specific — the Expo dev-launcher menu masquerading as the app on a cold
start — was ported forward into `skills/qa-preflight/SKILL.md`.

### Agents

| Agent | Preloaded skills |
| --- | --- |
| `mobile-qa-ios` | `qa-preflight`, `qa-ios-login` |
| `mobile-qa-android` | `qa-preflight`, `qa-android-login` |

Skills are preloaded via the `skills:` frontmatter field, which injects them in
full at startup. Relying on the agent to *remember* to read a procedure file
means that the moment it forgets, it starts exploring with no procedure at all.
`tools:` also includes `Skill` so non-preloaded skills remain callable at runtime.

### `memory:` and `disallowedTools:` — resolved

Both agents previously declared `memory: project` **and**
`disallowedTools: Write, Edit`. These conflict: `memory` auto-enables Write/Edit,
`disallowedTools` removes them, so the agent received a memory directory it could
not write to.

**Resolution: `memory: project` is removed from both QA agents.** The memory file
is now named as an explicit `Read` target in each agent's step 0
(`.claude/agent-memory/<agent>/MEMORY.md`), and **writing is left to the separate
`memory-manager-agent`**, which already exists for exactly this.

Re-granting Write/Edit and merely instructing "don't edit app source" would be a
wish, not access control — a QA agent must not be able to modify the code it is
judging.

**Honest limitation:** `disallowedTools: Write, Edit` does not stop shell
redirection through `Bash`. The agents are instructed not to do it, but that part
*is* a wish. Removing `Bash` is not an option, since it is how the driver runs.

---

## Install

**Do not install agent-device globally at `@latest`.** Prefer a project-local,
lockfile-pinned install:

```bash
npm i -D agent-device@0.20.8
```

Then the official skills (from GitHub — not shipped on npm):

```bash
npx skills add callstack/agent-device
```

Load this plugin during development:

```bash
claude --plugin-dir ./mobile-qa
```

After changes, `/reload-plugins` — no restart needed.

Verify:

```bash
claude plugin validate ./mobile-qa    # --strict adds only the intentional
                                      # "No version specified" warning
mobile-qa-device --resolve            # must report 0.20.8 inside the pinned range
mobile-qa-preflight all --help
```

- Agents: `/context` → Custom Agents shows `mobile-qa:mobile-qa-ios` and
  `mobile-qa:mobile-qa-android`
- Skills: `/help` → `/mobile-qa:qa-preflight` etc.
- Scripts: `mobile-qa-preflight --help` runs as a bare command
- On failure check the **Errors** tab in `/plugin`

Optional MCP (pin the version explicitly — never `@latest`):

```json
{
  "mcpServers": {
    "agent-device": {
      "command": "npx",
      "args": ["-y", "agent-device@0.20.8", "mcp"]
    }
  }
}
```

---

## Project setup (once per app)

```bash
mkdir -p .claude/mobile-qa
# after `claude plugin install mobile-qa@daegyu-plugins`, the examples live in
# the plugin cache; a clone of the marketplace repo works just as well
P=~/.claude/plugins/cache/daegyu-plugins/mobile-qa

cp "$P"/examples/mobile-qa.config.json .claude/mobile-qa.config.json
cp "$P"/examples/screens.md            .claude/mobile-qa/screens.md
cp "$P"/examples/flows.md              .claude/mobile-qa/flows.md
```

**Then edit the values.** Leaving the sample values in place is a bug.

Credentials go in exactly one of two places:

```bash
export MOBILE_QA_EMAIL='qa@example.com'
export MOBILE_QA_PASSWORD='...'
```

or `.claude/mobile-qa.local.json`, which the `.gitignore` rules keep ignored.

### Resolution order

1. environment variables (`MOBILE_QA_*`)
2. `.claude/mobile-qa.local.json` — secrets only
3. `.claude/mobile-qa.config.json` — committed, non-sensitive
4. built-in defaults — **only for things universally true** (Metro port `8081`)

### Config keys

| Key | Meaning |
| --- | --- |
| `reportLanguage` | language for report prose (default `en`) |
| `metro.port` / `metro.startCommand` | Metro |
| `agentDevice.ios.app` / `.device` | iOS bundle id; device empty = let agent-device choose |
| `agentDevice.android.app` / `.device` | Android package id; device empty = let agent-device choose |
| `build.iosCommand` / `.androidCommand` | reported when the app is not installed — never run automatically |
| `auth.testIds.{email,password,submit}` | login fields |
| `auth.loggedInMarkers` / `loggedOutMarkers` | login-state detection |
| `auth.loginEntryMarkers` | **the only controls the agent may tap to reach login** |
| `auth.errorMarkers` | credentials rejected (terminal) vs still waiting |
| `quirks.dismissLogBox` | auto-dismiss the dev LogBox overlay |

**Driver quirks are no longer configured here.** Simulator UDIDs, coordinate
scaling and IME package names moved to agent-device's own target selection.

> **Schema change.** `ios.bundleId` / `android.package` became
> `agentDevice.ios.app` / `agentDevice.android.app`. `mobile-qa-preflight`
> still accepts the old keys and prints a migration warning, but **device pins
> are not carried over**. The live `.claude/mobile-qa.config.json` in this repo
> is still on the old schema and should be migrated.

### `loginEntryMarkers` is a safety fence

On apps whose landing screen has no credential fields, the agent must tap
something to reach the login form. **It will only tap what is listed here.** That
prevents it from wandering into Kakao/Apple OAuth (which leaves the app) or
account creation (which mutates real backend state).

### Markers must be testID-based

Prefer `testID`/role over visible text. Text markers break across locales and
collide: a bare `"Star"` or `"My"` can match onboarding copy on the *logged-out*
screen, and a false positive there runs an entire QA pass against the wrong
screen with every later failure misattributed to the app.

Find candidates with:

```bash
grep -rn 'testID=' app/ components/
```

Also check that the marker is on the **first screen after login**, not behind
tab navigation — a marker on a settings screen is absent from the first snapshot
and makes a logged-in session look logged out.

The example config carries a **`_VERIFY_ON_FIRST_RUN`** block listing exactly
what must be confirmed against a real snapshot. Nothing in it has been verified
on a device yet.

---

## Usage

QA runs **iOS and Android in parallel, always.** Never one side only. Launch both
subagents in a single message so they execute concurrently.

Suggested `max_turns`: simple check 15 / multi-step interaction 20 / full E2E 30.

Preconditions are handled by `mobile-qa-preflight all`.

---

## Report contract

The agent **must return a text report as its final message.** A subagent's result
*is* that text — no report means the whole session is lost.

Every report contains:

1. `PASS` / `FAIL` / `BLOCKED` per test, with repro steps and evidence
2. one line: `Turn budget: used N / allotted M - heaviest step: <step> (K turns)`
3. a `## Learned` block in machine-readable form:

```
TYPE | claim | evidence | confidence
```

- `TYPE` ∈ `FACT` | `CORRECTION` | `GOTCHA` | `WORKAROUND` | `UNRESOLVED`
- `evidence` is **mandatory** — an item you cannot evidence is omitted entirely
- `confidence` ∈ `high` | `medium` | `low`
- nothing learned → write exactly `none`, never omit the block
- **proposals to change PASS/FAIL criteria do not go here** (use `Notes`)
- app bugs go under `### BUG:`, not here

This block is the **only** path by which knowledge reaches layer 4 and the
plugin. The agents cannot write files, so anything omitted is lost permanently.

---

## What must never go into the plugin

The plugin's value is that it is general. These belong in project config:

- bundle ids, package names, device UDIDs, device names
- real testID strings, screen names, navigation structure
- test account credentials (**never in a plugin file, under any circumstances**)
- one app's pass criteria

And these belong in the plugin, because they are true for any RN app:

- parallel iOS+Android policy and the turn budget discipline
- the report contract and the `## Learned` handoff format
- the read-only stance and the `loginEntryMarkers` safety fence
- the version pin and the Node floor

Note what is **no longer** on the second list: tool gotchas. Text-entry chunking,
coordinate conversion and IME recovery were the plugin's main content under
Mobile MCP. They now belong to agent-device, and restating them here would only
create drift.
