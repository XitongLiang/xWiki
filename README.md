# xWiki

xWiki is a personal LLM-maintained knowledge base inspired by Andrej Karpathy's
LLM Wiki pattern.

The goal is to build a persistent, compounding wiki instead of a pile of files
that must be rediscovered from scratch every time. Raw sources stay immutable;
the LLM reads them, extracts useful knowledge, and maintains a structured
markdown wiki with links, summaries, citations, contradictions, and evolving
synthesis pages.

## Structure

```text
_inbox/    New material waiting to be ingested.
_raw/      Source material after ingestion begins; cited by the wiki.
_wiki/     Generated knowledge: summaries, concepts, entities, syntheses, logs.
_schema/   Operating rules: workflows, page conventions, citation style.
```

## Principles

- `_inbox` is the visible queue of material that has not been ingested yet.
- `_raw` is the source of truth for material that has entered the wiki. Files
  here should be read and cited, not edited.
- `_wiki` is the compiled knowledge layer. The LLM owns and maintains these pages.
- `_schema` defines the rules that keep the wiki consistent across sessions.
- Useful answers should be saved back into the wiki when they create durable value.
- The wiki should be periodically linted for stale claims, missing links,
  contradictions, orphan pages, and open research questions.

## Basic Workflow

1. Add new sources to `_inbox`.
2. Ask the LLM to ingest the inbox.
3. The LLM moves each source into `_raw`, reads it, creates or updates wiki
   pages, adds citations and cross-links, updates the index, and records the
   activity in the log.
4. Browse the result in Obsidian, ask follow-up questions, and save valuable
   analyses back into `_wiki`.

## Starter Files To Add

- `AGENTS.md`: root pointer that tells LLM agents to read the schema.
- `_schema/AGENTS.md`: the main operating contract for LLM maintainers.
- `_schema/page-types.md`: standard wiki page types and recommended sections.
- `_schema/ingest-workflow.md`: exact process for adding new sources.
- `_schema/citation-style.md`: lightweight provenance and uncertainty rules.
- `_schema/lint-workflow.md`: periodic wiki health-check process.
- `_wiki/index.md`: a content-oriented catalog of wiki pages.
- `_wiki/log.md`: a chronological record of ingests, queries, and maintenance.
- `_wiki/overview.md`: a human-readable map of what this wiki currently knows.
