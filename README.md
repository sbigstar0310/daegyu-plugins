# daegyu-plugins

Personal Claude Code plugins by [@sbigstar0310](https://github.com/sbigstar0310).

## Plugins

| Plugin | Description |
|---|---|
| `notion-manager` | Notion workspace manager — Daily Log, TODO, experiment reports |
| `progress` | Live status of long-running jobs — ETA-first, discovered from tmux/logs/GPU |
| `pptx-deck` | Design-aligned `.pptx` deck builder with faithful PNG previews |
| `mobile-qa` | Parallel iOS + Android GUI QA subagents for React Native / Expo apps |
| `work-style` | Working style injected at every session start and reminded every prompt — main session keeps the conversation flowing, slow work goes to the background, independent work runs in parallel subagents |

## Install

Add the marketplace once, then install only what you need — each plugin is
independent.

In a Claude Code session:

```
/plugin marketplace add sbigstar0310/daegyu-plugins
/plugin install notion-manager@daegyu-plugins
/plugin install progress@daegyu-plugins
/plugin install pptx-deck@daegyu-plugins
/plugin install mobile-qa@daegyu-plugins
/plugin install work-style@daegyu-plugins
```

Or from a shell:

```bash
claude plugin marketplace add sbigstar0310/daegyu-plugins
claude plugin install mobile-qa@daegyu-plugins
```

Update later with `/plugin marketplace update daegyu-plugins`.

> Marketplace names cannot start with `claude-` — Claude Code rejects them as
> impersonating an official Anthropic marketplace.

## Repository layout

Each plugin is a top-level directory containing its own
`.claude-plugin/plugin.json`. The marketplace catalog is
`.claude-plugin/marketplace.json` at the repo root, and its `source` paths are
relative to the **repo root** (the directory containing `.claude-plugin/`), not
to `.claude-plugin/` itself.

```
daegyu-plugins/
├── .claude-plugin/marketplace.json
├── notion-manager/
├── progress/
├── pptx-deck/
└── mobile-qa/
```

## Versioning policy

`notion-manager`, `progress` and `pptx-deck` declare a `version` in their
`plugin.json`. **`mobile-qa` deliberately does not — do not add one.**

Claude Code keeps a consumer on their cached copy for as long as the resolved
version string is unchanged. A plugin that declares `version` in `plugin.json`
*or* in its marketplace entry therefore stops receiving pushes until that
string is bumped. Omit `version` and Claude Code auto-versions from the git
commit SHA, so every push to `main` reaches consumers. Never set it in both
places — the marketplace entry is then silently ignored.

`mobile-qa` is under active development and has never been run against a real
device, so its fixes need to propagate immediately. The tradeoff is that
`claude plugin validate --strict` reports one warning for it
(`version: No version specified`) and exits non-zero; plain
`claude plugin validate` passes. That warning is intended.

## Notes

- **`pptx-deck`** needs `python-pptx`, `matplotlib`, `numpy`, `Pillow` for its
  render/preview scripts. Install them in whatever interpreter you point the skill at.
- **`progress`** reports clock times in KST (Asia/Seoul). Change the timezone in
  `skills/progress/SKILL.md` if you are elsewhere.
- **`mobile-qa`** needs Node >= 22.12 and drives devices through a pinned
  `agent-device` (0.20.8). Every app-specific fact — bundle id, device, testIDs,
  credentials — comes from your project's `.claude/mobile-qa.config.json`;
  nothing app-specific is baked into the plugin. Its `examples/` are filled in
  with values from the author's own SRR app so the sample reads as a coherent
  worked example — **copy and replace every value**. Credentials never go in a
  committed file. See `mobile-qa/README.md`.
