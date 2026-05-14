# Ingest Workflow

Use this workflow when the human adds a source to `_inbox/` and asks the LLM to
process it.

## 1. Identify the Source

- Locate new files in `_inbox/`.
- Determine source type: article, paper, transcript, book chapter, webpage,
  dataset, image, note, or other.
- Check whether the source fits an existing top-level topic. If it clearly
  opens a new broad domain, ordinary ingest may create a new L0 topic page and
  add it to `_wiki/index.md`. If the fit is unclear, place it in a broad
  provisional topic and record the taxonomy uncertainty as an open question.
  Do not split, merge, or reorganize existing topic branches during ordinary
  ingest; that belongs to `_schema/taxonomy-workflow.md`.
- Record title, author, date, URL, and file path when available.
- If metadata is missing, mark it as unknown instead of inventing it.

## 2. Move Into Raw

- Move each source being ingested from `_inbox/` to `_raw/`.
- Preserve the original filename unless there is a clear reason to normalize it.
- If a file with the same name already exists in `_raw/`, avoid overwriting it;
  choose a clear disambiguating filename.
- Citations should point to the `_raw/` path, not the old `_inbox/` path.

## 3. Read and Extract

Read the source carefully enough to extract:

- one-paragraph summary
- key claims
- important evidence
- named people, organizations, places, products, projects, datasets,
  benchmarks, software, repositories, and concepts
- dates and timeline events
- contradictions with existing wiki pages
- open questions

If the source is not in English, translate extracted claims, summaries, and
analysis into English for `_wiki/` pages. Preserve original-language titles,
author names, URLs, quoted terms when necessary, and raw file paths in source
metadata. Do not invent translations for ambiguous proper nouns; keep the
original form and add a brief English gloss when useful.

For research papers, also extract:

- research problem: what gap, bottleneck, or question the paper addresses
- proposed method: the core algorithm, model, system, or theoretical move
- method structure: main components, data flow, assumptions, and key
  parameters when relevant
- mechanism analysis: why the method is expected to work, what design choices
  drive the improvement, and what failure modes those choices imply
- novelty: what is genuinely new compared with prior work
- experiments: datasets, baselines, metrics, ablations, and evaluation setup
- key results: important numbers, qualitative findings, and failure cases
- key figures or tables: the few diagrams, tables, or result plots that carry
  the paper's main evidence or mechanism explanation
- code or implementation notes: repository link, important modules, practical
  implementation constraints, and paper-code alignment when available
- limitations: limitations stated by the authors and plausible unstated
  weaknesses
- future work: author-proposed directions and natural extensions
- related-work position: which research line the paper belongs to and how it
  connects to existing wiki pages

For formulas in paper notes:

- use inline Markdown LaTeX as `$...$`
- use block Markdown LaTeX as `$$...$$` on separate lines
- do not wrap renderable formulas in code blocks
- keep notation faithful to the source instead of silently changing symbols

For images or PDFs with visual content, inspect relevant images separately when
possible and describe what evidence they add. For paper ingests, focus on a
small number of key figures or tables instead of trying to catalog every image.

## 4. Search Existing Wiki

Before writing:

- read `_wiki/index.md` if it exists
- search for related concepts, entities, and previous source summaries
- identify pages to update
- avoid duplicate pages for the same concept or entity

## 5. Write the Source Page

Create one page in `_wiki/sources/` using the source page format from
`_schema/page-types.md`.

Source pages should be written in English even when the source is in another
language. Use an English translated page title when practical, and keep the
original title in the `## Source` metadata.

Every source page should include:

- source file path
- source metadata when known
- summary
- key claims
- links to relevant concept/entity/synthesis pages
- open questions

For research papers, include the paper-specific analysis fields when they are
available and useful. Do not force every section when the source does not
support it, but prefer preserving method, experiment, limitation, and
related-work information because those are often the most reusable parts of a
paper ingest. Include `Mechanism Analysis`, `Key Figures or Tables`, and
`Code or Implementation Notes` when the paper provides enough evidence.

## 6. Update Related Pages

For every meaningful concept or entity:

- update the existing page, or create a new one if needed
- add source-backed facts
- add links to related pages
- add or update open questions
- flag contradictions or uncertainty

Do not create pages for every passing mention. Create pages when the topic is
likely to matter again.

### Entity Selection Policy

Do not create author pages automatically.

Record all known authors in the source page citation or metadata, but create a
human entity page only when the person is worth tracking across the wiki. Good
reasons include:

- the person appears across multiple ingested sources
- the person is part of the human's research network or collaboration graph
- the person's research line is itself important to the wiki
- the human explicitly asks to track that person

For ordinary paper authors who are not otherwise important to the wiki, keep the
name in the source citation and do not create an entity page.

Entity pages may also represent non-human named things when they are useful
wiki anchors, including organizations, labs, datasets, benchmarks, software
systems, repositories, institutions, products, places, and conferences.

## 7. Update Index and Log

Update `_wiki/index.md` with new or changed pages.

Append a log entry to `_wiki/log.md`:

```markdown
## [YYYY-MM-DD] ingest | Source Title

- Source: `_raw/path/to/source`
- Created: `[[Page Name]]`
- Updated: `[[Other Page]]`, `[[Another Page]]`
- Notes: brief note about major themes, contradictions, or open questions.
```

## 8. Report Back

Tell the human:

- what source was ingested
- which files were moved from `_inbox/` to `_raw/`
- which pages were created or updated
- what the most important takeaways were
- what needs review, if anything
