# daegyu-plugins

Personal Claude Code plugins by [@sbigstar0310](https://github.com/sbigstar0310).

## Plugins

| Plugin | Description |
|---|---|
| `notion-manager` | Notion workspace manager — Daily Log, TODO, experiment reports |
| `progress` | Live status of long-running jobs — ETA-first, discovered from tmux/logs/GPU |
| `pptx-deck` | Design-aligned `.pptx` deck builder with faithful PNG previews |

## Install

```
/plugin marketplace add sbigstar0310/claude-plugins
/plugin install notion-manager@daegyu-plugins
/plugin install progress@daegyu-plugins
/plugin install pptx-deck@daegyu-plugins
```

Install only what you need — each skill is its own plugin.

> The repo path is `sbigstar0310/claude-plugins` but the **marketplace name is
> `daegyu-plugins`** — that is the `@suffix` you install with. They differ because
> Claude Code rejects marketplace names starting with `claude-` (they read as
> impersonating an official Anthropic marketplace).

## Notes

- **`pptx-deck`** needs `python-pptx`, `matplotlib`, `numpy`, `Pillow` for its
  render/preview scripts. Install them in whatever interpreter you point the skill at.
- **`progress`** reports clock times in KST (Asia/Seoul). Change the timezone in
  `skills/progress/SKILL.md` if you are elsewhere.
