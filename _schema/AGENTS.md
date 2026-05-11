# xWiki Agent Contract

This file defines how an LLM maintainer should operate inside xWiki.

xWiki is a persistent, LLM-maintained markdown knowledge base. The human curates
sources and asks questions. The LLM maintains the wiki: reading sources,
extracting claims, creating links, updating summaries, tracking contradictions,
and preserving useful analysis.

## Directory Roles

- `_inbox/`: new source material waiting to be ingested. This is the visible
  queue of not-yet-ingested material.
- `_raw/`: immutable source material after ingestion begins. Move files here
  from `_inbox/`, then read and cite these files, but do not edit them unless
  the human explicitly asks.
- `_wiki/`: generated knowledge layer. Create and update markdown pages here.
- `_schema/`: operating rules, templates, and workflows. Update these only when
  conventions need to evolve.
- `tools/`: deterministic maintenance scripts. Prefer these for structural
  checks before doing expensive or semantic wiki review.
- `graph/`: generated graph artifacts derived from `_wiki/` links.

## Core Behavior

- Read relevant schema files before changing the wiki.
- Preserve source provenance for meaningful claims.
- Prefer small, well-linked pages over large undifferentiated notes.
- Update existing pages before creating duplicates.
- Create entity pages selectively. Do not create author/person pages just
  because someone appears in a citation.
- Use Obsidian-style wiki links for internal links: `[[Page Name]]`.
- Keep raw facts separate from interpretation when possible.
- Flag uncertainty, contradictions, and missing evidence explicitly.
- Save durable answers from conversations into `_wiki/` when they add lasting
  value.
- Run `python3 tools/health.py` before broad maintenance or semantic linting when
  the wiki structure may have drifted.
- Use `python3 tools/build_graph.py --report` to inspect link structure, but do
  not create pages from graph signals without source-backed value.
- Use `python3 tools/file_to_md.py` for optional conversion when source formats
  are hard to inspect directly; preserve the original source provenance.
- Append every meaningful ingest, query filing, or maintenance pass to
  `_wiki/log.md`.

## Before Editing

1. Check `_wiki/index.md` if it exists.
2. If ingesting new material, move relevant files from `_inbox/` to `_raw/`.
3. Search `_wiki/` for related pages.
4. Read the source files or wiki pages that will support the edit.
5. Decide whether to create a new page, update an existing page, or both.

## After Editing

1. Update `_wiki/index.md`.
2. Update backlinks or "Related" sections on touched pages.
3. Add citations for new factual claims.
4. Record the operation in `_wiki/log.md`.
5. Note open questions or contradictions when they appear.

## Naming

- Use clear title-case page names for wiki pages.
- Use stable, descriptive filenames without dates unless the page is explicitly
  chronological.
- Prefer `Topic Name.md` over clever abbreviations.
- Source summary pages should use the source title when available.

## Human Review

When ingesting substantial sources, summarize the proposed changes before or
after editing and make clear which pages were touched. If the source is ambiguous
or the right taxonomy is unclear, make a reasonable first pass and record open
questions rather than blocking.
