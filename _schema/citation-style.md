# Citation Style

xWiki uses lightweight provenance that works in plain markdown and Obsidian.

## Basic Rule

Every important factual claim added to `_wiki/` should be traceable to at least
one source in `_raw/` or another wiki page that already cites sources.

## Preferred Citation Format

Use inline source references:

```markdown
The claim goes here. Source: `_raw/path/to/source.md`.
```

When line numbers, page numbers, timestamps, or sections are known, include
them:

```markdown
The claim goes here. Source: `_raw/paper.pdf`, p. 12.
The claim goes here. Source: `_raw/interview.md`, 00:14:32.
The claim goes here. Source: `_raw/article.md`, section "Background".
```

## Source Lists

At the bottom of concept, entity, synthesis, and question pages, include a
`## Sources` or `## Evidence` section when the page depends on multiple sources.

Example:

```markdown
## Sources

- `_raw/articles/example.md`
- `_raw/reports/example-report.pdf`, pp. 8-11
```

## Uncertainty

Do not smooth over uncertainty. Use direct labels:

- `Unverified:`
- `Tentative:`
- `Contradiction:`
- `Needs source:`
- `Open question:`

## Contradictions

When a new source conflicts with an old claim:

1. Preserve both claims if both are source-backed.
2. Add a `Contradiction:` note near the relevant claim.
3. Link or cite both sources.
4. Add an open question if more evidence is needed.

## Avoid

- Do not cite a source that was not read.
- Do not invent page numbers, line numbers, authors, dates, or URLs.
- Do not use vague citations like "according to the article" when a path is
  available.
- Do not rely on chat history as a durable source unless the answer is saved as
  a question or synthesis page.

