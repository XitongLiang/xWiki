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
tools/     Deterministic maintenance utilities.
graph/     Generated graph data and visualization artifacts.
```

## Principles

- `_inbox` is the visible queue of material that has not been ingested yet.
- `_raw` is the source of truth for material that has entered the wiki. Files
  here should be read and cited, not edited.
- `_wiki` is the compiled knowledge layer. The LLM owns and maintains these pages.
- Entity pages are selective anchors for people, organizations, datasets,
  systems, institutions, and other named things worth tracking; paper authors
  do not become entity pages by default.
- Research paper ingests should capture method, mechanism, experiments, key
  figures/tables, implementation notes when available, novelty, limitations,
  future work, and related-work position in English.
- `_schema` defines the rules that keep the wiki consistent across sessions.
- Useful answers should be saved back into the wiki when they create durable value.
- Run deterministic health checks before heavier maintenance when the structure
  may have drifted.
- Build the graph from explicit `[[wikilinks]]` to find orphans, hubs, and
  missing page signals.
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

## Maintenance Commands

```bash
python3 tools/health.py
python3 tools/build_graph.py --report
python3 tools/file_to_md.py path/to/source.pdf
```

`health.py` performs deterministic structural checks with no LLM calls.
`build_graph.py` creates `graph/graph.json` and `graph/graph.html` from explicit
wiki links, and can print a graph health report.
`file_to_md.py` optionally converts rich source formats into markdown companions
for easier ingest.

## Starter Files To Add

- `AGENTS.md`: root pointer that tells LLM agents to read the schema.
- `_schema/AGENTS.md`: the main operating contract for LLM maintainers.
- `_schema/page-types.md`: standard wiki page types and recommended sections.
- `_schema/ingest-workflow.md`: exact process for adding new sources.
- `_schema/citation-style.md`: lightweight provenance and uncertainty rules.
- `_schema/lint-workflow.md`: periodic wiki health-check process.
- `_schema/health-workflow.md`: deterministic structural checks.
- `_schema/graph-workflow.md`: explicit-wikilink graph generation.
- `_schema/query-workflow.md`: answering and saving durable wiki questions.
- `_schema/conversion-workflow.md`: optional markdown conversion for rich inputs.
- `_wiki/index.md`: a content-oriented catalog of wiki pages.
- `_wiki/log.md`: a chronological record of ingests, queries, and maintenance.
- `_wiki/overview.md`: a human-readable map of what this wiki currently knows.
