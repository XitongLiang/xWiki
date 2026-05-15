# Source Selection Workflow

Use this workflow before full ingest when the human requests curated ingest,
such as `curated ingest inbox`, `curated ingest causal`, `ingest useful papers
about X`, or search-based ingest where not every candidate should enter the
wiki.

## Purpose

Curated ingest separates lightweight selection from full source-page ingest. The
goal is to avoid filling the wiki with low-value, redundant, off-topic, or
untrustworthy material while making the selection decision auditable.

## Selection Depth

Use the lightest reading depth that supports a defensible decision:

- `metadata`: title, authors, venue or site, date, abstract, URL, file name,
  source type, and obvious topic fit.
- `skim`: metadata plus abstract, introduction, conclusion, headings, figures,
  tables, and one or two key sections.
- `full`: only when the decision cannot be made without deeper reading.

Do not imply a source was fully read when only metadata or skim reading was
performed. Record the reading depth and sections inspected.

## Candidate Decisions

Classify every candidate as exactly one of:

- `ingest-now`: source is relevant and worth full ingest.
- `defer`: potentially useful, but not worth ingesting now.
- `reject`: low relevance, low quality, too generic, promotional, inaccessible,
  or otherwise not worth preserving.
- `duplicate`: already covered by an existing source page or a better version.

Only `ingest-now` candidates enter the normal ingest workflow.

## Scoring

Score each candidate from 0 to 5 on:

- `relevance`: fit with the requested topic and existing wiki branches.
- `novelty`: whether it adds concepts, evidence, methods, data, or perspective
  not already captured.
- `authority`: reliability of the source, authors, venue, publisher, or project.
- `specificity`: whether it contains concrete extractable claims rather than
  generic commentary.
- `reusability`: likelihood that the source will be cited or compared again.
- `redundancy`: overlap with already ingested sources, where higher means more
  redundant.
- `cost`: expected effort to read and maintain, where higher means more costly.

Use this heuristic:

```text
selection_score = relevance + novelty + authority + specificity + reusability - redundancy - cost
```

The score informs the decision but does not replace judgment. Always include a
short reason that names the wiki gap the source fills, the main redundancy, or
the reason it should be skipped.

## Output Location

Record curated ingest scoring in a durable question page:

```text
_wiki/questions/source-selection-YYYY-MM-DD.md
```

If multiple curated selections happen on the same day, append to the same page
under a new section. This page is a decision record, not a source page.

## Selection Page Format

```markdown
---
type: question
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [source-selection, curated-ingest]
sources: []
---

# Source Selection - YYYY-MM-DD

## Request

Original human request.

## Existing Wiki Context

- [[Relevant Topic]]
- [[Relevant Source]]

## Candidates

### Candidate Title

- Path or URL:
- Type:
- Reading depth: metadata | skim | full
- Sections inspected:
- Proposed topic:
- Scores:
  - relevance:
  - novelty:
  - authority:
  - specificity:
  - reusability:
  - redundancy:
  - cost:
  - selection_score:
- Decision: ingest-now | defer | reject | duplicate
- Reason:
- Existing overlap:

## Summary

- Ingest now:
- Deferred:
- Rejected:
- Duplicates:
```

## Log Format

Append a concise entry to `_wiki/log.md`:

```markdown
## [YYYY-MM-DD] source-selection | Request summary

- Created or updated: [[Source Selection - YYYY-MM-DD]]
- Ingest now: `N`
- Deferred: `N`
- Rejected: `N`
- Duplicates: `N`
- Notes: brief rationale or next action.
```

If full ingest happens immediately after source selection, also append normal
ingest log entries for the ingested sources.
