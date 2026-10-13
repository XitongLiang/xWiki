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
- `.tools/`: deterministic maintenance scripts. Prefer these for structural
  checks before doing expensive or semantic wiki review.
- `xwiki_tools/`: rebuildable extraction, SQLite FTS/graph indexing, query, and
  read-only MCP code. It projects the file-based wiki and never replaces it as
  the source of truth.
- `.agents/skills/`: repository-local agent entry points. The xWiki ingest skill
  routes work through this schema; it must not redefine conflicting rules.
- `skills/`: portable client skills. The xWiki knowledge MCP skill supports
  read-only retrieval and does not authorize Wiki writes or index repair.

## Core Behavior

- Read relevant schema files before changing the wiki.
- Use `.agents/skills/xwiki-ingest/SKILL.md` for ingest, source analysis that
  should enter the Wiki, and explicit taxonomy maintenance. If it conflicts
  with `_schema/`, follow `_schema/` and repair the skill separately.
- Preserve source provenance for meaningful claims.
- Prefer small, well-linked pages over large undifferentiated notes.
- Update existing pages before creating duplicates.
- Create entity pages selectively. Do not create author/person pages just
  because someone appears in a citation.
- Use Obsidian-style wiki links for internal links: `[[Page Name]]`.
- Use `_schema/taxonomy-workflow.md` only for explicit taxonomy maintenance,
  clustering, or reorganization requests. Do not reorganize directories during
  ordinary ingest or query answering.
- Distinguish exhaustive ingest from curated ingest. `ingest inbox` means every
  readable, non-duplicate inbox source should be ingested. `curated ingest ...`
  means candidates should be selected using `_schema/source-selection-workflow.md`
  before full ingest, with selection scores recorded in `_wiki/log.md`.
- Write wiki pages in English by default. When sources are in Chinese or any
  other non-English language, translate extracted summaries, claims, and
  analysis into English while preserving original titles, names, URLs, and
  source paths in source metadata.
- Keep raw facts separate from interpretation when possible.
- Flag uncertainty, contradictions, and missing evidence explicitly.
- Save durable answers from conversations into `_wiki/` when they add lasting
  value.
- Run `python3 .tools/health.py` before broad maintenance or semantic linting when
  the wiki structure may have drifted.
- Run `python3 .tools/lint.py` after broad content edits to validate page schema,
  citations, raw references, identities, wikilinks, and topic-layer rules.
- Use `python3 .tools/file_to_md.py` for optional conversion when source formats
  are hard to inspect directly; preserve the original source provenance.
- Rebuild `.xwiki/knowledge.sqlite` with `python3 -m xwiki_tools build` after
  content changes when local search or MCP retrieval is in use. Follow
  `_schema/indexing-workflow.md`; never treat the database as authored content.
- Keep MCP read-only and local by default. Follow `_schema/mcp-workflow.md` and
  do not expose private vault content over a public unauthenticated endpoint.
- Append every meaningful ingest, query filing, or maintenance pass to
  `_wiki/log.md`.

## Before Editing

1. Check `_wiki/index.md` if it exists.
2. If the request is curated ingest, perform source selection before moving
   files into `_raw/`.
3. If ingesting accepted new material, move relevant files from `_inbox/` to
   `_raw/`.
4. Search `_wiki/` for related pages.
5. Read the source files or wiki pages that will support the edit.
6. Decide whether to create a new page, update an existing page, or both.

## After Editing

1. Update `_wiki/index.md`.
2. Update backlinks or "Related" sections on touched pages.
3. Add citations for new factual claims.
4. Record the operation in `_wiki/log.md`.
5. Note open questions or contradictions when they appear.
6. Run `python3 .tools/health.py` and `python3 .tools/lint.py` after broad edits.
7. Rebuild the optional knowledge index when the user relies on CLI or MCP
   retrieval; an index failure must not roll back valid Markdown edits.

## Naming

- Use clear title-case page names for wiki pages.
- Prefer English page titles and filenames. Preserve non-English source titles
  in source metadata, but use an English translated title for the wiki page when
  it will be easier to link, search, and reuse.
- Use stable, descriptive filenames without dates unless the page is explicitly
  chronological.
- Prefer `Topic Name.md` over clever abbreviations.
- Source summary pages should use the source title when available.

## Human Review

When ingesting substantial sources, summarize the proposed changes before or
after editing and make clear which pages were touched. If the source is ambiguous
or the right taxonomy is unclear, make a reasonable first pass and record open
questions rather than blocking.
