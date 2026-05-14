# Health Workflow

Use this workflow for fast structural checks before heavier ingest, query, or
lint work.

## Purpose

`health` is deterministic and uses no LLM calls. It catches file-structure
problems that make later wiki maintenance unreliable.

Run:

```bash
python3 .tools/health.py
```

Useful variants:

```bash
python3 .tools/health.py --json
python3 .tools/health.py --save
```

## Checks

- Files still waiting in `_inbox/`.
- Empty or stub pages in `_wiki/`.
- Wiki pages missing from `_wiki/index.md`.
- Unresolved wikilinks in `_wiki/index.md`.
- Broken Obsidian links across `_wiki/`.
- Source pages in `_wiki/sources/` without matching ingest log entries.
- Raw files in `_raw/` that are not cited by source pages.

## When To Run

- At the start of a maintenance session.
- Before a semantic lint pass.
- After moving source files between `_inbox/` and `_raw/`.
- After large ingest or page-renaming work.

## Output

By default, print a markdown report to stdout. With `--save`, write
`_wiki/health-report.md`.

Health reports are maintenance artifacts. Do not treat them as source material
unless the human asks to preserve a specific finding.
