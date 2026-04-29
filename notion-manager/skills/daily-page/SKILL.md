---
name: daily-page
description: "Create or update a Daily Log page in Notion. Use when the user asks to create today's daily page, update an existing daily page with notes/results, or review past daily pages."
---

# Daily Log Page Skill

Create and manage daily log pages in daegyu's Notion workspace.

## Workspace Location

- **Path**: `KAIST` → `MLAI 개별연구` → `Daily Log`
- **Page title format**: `YY.MM.DD` (e.g., `26.02.19` for February 19, 2026)

## Creating a New Daily Page

1. **Search** for the "Daily Log" parent page using `mcp__notion__notion-search`
2. **Check** if today's page already exists (search for the date string)
3. If it doesn't exist, **read the template** from `template.md` (in this skill's directory)
4. **Create** the page under the Daily Log parent using `mcp__notion__notion-create-pages`
5. **Verify** by fetching the created page

### Template Usage

Read the template file at the path relative to this skill:
```
Read file: .claude/plugins/notion-manager/skills/daily-page/template.md
```

Replace the placeholder `{DATE}` with the actual date in `YY.MM.DD` format.

## Updating an Existing Daily Page

1. **Search** for the page by date title
2. **Fetch** current content to understand what's already there
3. **Append or modify** content as requested — never overwrite existing content unless explicitly asked
4. **Verify** the changes

### Experiment Results Table Rules

When adding experiment results to a daily page:

- **MDL Table**: Columns = `Config | Trial 1 | Trial 2 | Trial 3 | Trial 4 | Trial 5 | Mean`
  - Values are MDL scores (lower is better)
  - Include all trials that have been run; use `—` for unrun trials
  - Calculate Mean only from completed trials

- **Accuracy Table**: Same column structure as MDL
  - Values are WebGen-Bench accuracy percentages

- **Appearance Table**: Same column structure as MDL
  - Values are appearance grades (0-5 scale, higher is better)

- **Per-App Tables**: When detailed per-app data is available
  - Columns = `App ID | Config 1 | Config 2 | ... | Baseline`
  - One row per app

- **Summary Table**: Cross-metric comparison
  - Columns = `Config | MDL (Best) | Accuracy (Best) | Appearance (Best)`

### Key Observations Section

- Bullet points summarizing notable findings
- Compare against baseline when available
- Highlight statistically significant differences
- Note any anomalies or unexpected results

## Formatting

Use Notion Enhanced Markdown format. For the full spec, read:
```
ReadMcpResourceTool with server="notion" uri="notion://docs/enhanced-markdown-spec"
```

Key formatting patterns:
- Use `## Heading 2` for major sections
- Use `---` for dividers between sections
- Use standard markdown tables for data
- Use `- [ ]` for TODO checkboxes
- Use `- [x]` for completed items
