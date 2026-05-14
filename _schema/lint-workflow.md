# Lint Workflow

Use this workflow to health-check the wiki periodically.

Before semantic linting, run the deterministic health check:

```bash
python3 .tools/health.py
```

Fix structural issues first so semantic review does not spend attention on
empty pages, stale index entries, or broken links.

## Checks

- Pages missing frontmatter.
- Pages missing citations for important factual claims.
- Orphan pages with no links to or from the rest of the wiki.
- Duplicate pages that should be merged.
- Important concepts mentioned repeatedly but lacking a page.
- Stale claims that newer sources may supersede.
- Contradictions that are not explicitly labeled.
- Broken Obsidian links.
- Source files still waiting in `_inbox/`.
- Source files in `_raw/` that appear not to have corresponding source pages.
- Wiki pages missing from `_wiki/index.md`.

## Process

1. Read `_wiki/index.md` and `_wiki/log.md`.
2. List wiki files and raw files.
3. Search for markers such as `Needs source:`, `Open question:`,
   `Contradiction:`, and `TODO`.
4. Inspect likely problem pages.
5. Make small fixes directly when safe.
6. For larger conceptual issues, create a short maintenance report in
   `_wiki/questions/` or `_wiki/syntheses/`.
7. Append the lint pass to `_wiki/log.md`.

## Log Format

```markdown
## [YYYY-MM-DD] lint | Wiki health check

- Checked: brief scope.
- Fixed: pages or links changed.
- Found: issues that still need attention.
```
