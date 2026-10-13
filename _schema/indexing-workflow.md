# Knowledge Index Workflow

The local knowledge database is a rebuildable projection of `_wiki/` and cited
files in `_raw/`. Markdown and original source files remain authoritative. The
database must never become the only copy of a fact, citation, link, or analysis.

## Setup

Install the Python dependencies with Python 3.11 or newer in a local environment:

```bash
python3 -m venv .env
.env/bin/python -m pip install -r requirements.txt
```

The default database is `.xwiki/knowledge.sqlite`. The entire `.xwiki/`
directory is Git-ignored and may be deleted at any time.

## Build

Run a staged, atomic rebuild after meaningful Wiki or raw-source changes:

```bash
.env/bin/python -m xwiki_tools build
```

The builder:

- scans Markdown under `_wiki/`, excluding operational log pages
- projects page metadata, sections, wikilinks, topic levels, and raw provenance
- resolves links as `resolved`, `missing`, or `ambiguous` without inventing a
  target
- extracts cited PDF, text, CSV, TSV, XLSX, and XLS sources when possible
- stores physical page, line, sheet, or cell-range locators
- indexes English words and deterministic CJK unigram/bigram fallback tokens
- validates SQLite and FTS integrity before replacing the previous database

Use `--skip-source-text` for a fast metadata/graph build. Sources whose format
is unsupported or whose text requires OCR remain indexed as files with an
explicit extraction warning.

The build takes a cooperative `.build.lock`. Remove a stale lock only after
confirming no builder is running. A failed build preserves the prior database.

## Query Commands

```bash
.env/bin/python -m xwiki_tools search "agent memory"
.env/bin/python -m xwiki_tools pages --type concept --status active
.env/bin/python -m xwiki_tools browse
.env/bin/python -m xwiki_tools graph "Agent Memory"
.env/bin/python -m xwiki_tools view "Agent Memory"
.env/bin/python -m xwiki_tools read "_raw/path/to/source.pdf" --start 0 --limit 3
```

`browse` without a page identifier returns L0 topics. `graph` returns incoming
and outgoing links, raw-source associations, and source backlinks. `view` and
`read` return bounded content with continuation information.

Search is lexical SQLite FTS5 retrieval. It does not currently create
embeddings, call a model, translate queries, infer synonyms, or rerank with a
learned model. Vector or hybrid retrieval remains separate future work.

## Extraction

Inspect one supported source without writing to the Wiki or database:

```bash
.env/bin/python -m xwiki_tools extract /absolute/path/to/source.pdf
```

Extraction is a reading aid. It does not perform OCR, interpret figures,
evaluate spreadsheet formulas, or establish that a claim is factually
supported. Preserve the original source and review warnings.

## Safety And Privacy

- Index only files already declared through Wiki source provenance.
- Reject source paths outside `_raw/`.
- Verify an original's SHA-256 before returning indexed raw text.
- Do not commit `.xwiki/`, private source files, or generated query output.
- Do not build or query the private index in CI unless the test uses temporary
  fixtures.
