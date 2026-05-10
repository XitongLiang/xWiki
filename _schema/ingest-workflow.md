# Ingest Workflow

Use this workflow when the human adds a source to `_inbox/` and asks the LLM to
process it.

## 1. Identify the Source

- Locate new files in `_inbox/`.
- Determine source type: article, paper, transcript, book chapter, webpage,
  dataset, image, note, or other.
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
- named people, organizations, places, products, projects, and concepts
- dates and timeline events
- contradictions with existing wiki pages
- open questions

For images or PDFs with visual content, inspect relevant images separately when
possible and describe what evidence they add.

## 4. Search Existing Wiki

Before writing:

- read `_wiki/index.md` if it exists
- search for related concepts, entities, and previous source summaries
- identify pages to update
- avoid duplicate pages for the same concept or entity

## 5. Write the Source Page

Create one page in `_wiki/sources/` using the source page format from
`_schema/page-types.md`.

Every source page should include:

- source file path
- source metadata when known
- summary
- key claims
- links to relevant concept/entity/synthesis pages
- open questions

## 6. Update Related Pages

For every meaningful concept or entity:

- update the existing page, or create a new one if needed
- add source-backed facts
- add links to related pages
- add or update open questions
- flag contradictions or uncertainty

Do not create pages for every passing mention. Create pages when the topic is
likely to matter again.

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
