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

Record curated ingest scoring in `_wiki/log-full.md` under a `source-selection`
operation entry. Keep `_wiki/log.md` concise: it should summarize the counts,
decision rationale, and point to `_wiki/log-full.md` for details.

Source selection is an operational audit record, not a durable wiki question
page, so do not create `_wiki/questions/source-selection-YYYY-MM-DD.md`.

If multiple curated selections happen on the same day, append separate
`source-selection` entries to `_wiki/log-full.md` and concise matching summaries
to `_wiki/log.md`.

## Full Log Format

```markdown
## [YYYY-MM-DD] source-selection | Request summary

- Request: Original human request.
- Existing wiki context: [[Relevant Topic]], [[Relevant Source]]
- Ingest now: `N`
- Deferred: `N`
- Rejected: `N`
- Duplicates: `N`
- Notes: brief rationale or next action.

### Candidate Decisions

#### Candidate Title

- Path or URL:
- Type:
- Reading depth: metadata | skim | full
- Sections inspected:
- Proposed topic:
- Scores: relevance `0`, novelty `0`, authority `0`, specificity `0`, reusability `0`, redundancy `0`, cost `0`, selection_score `0`
- Decision: ingest-now | defer | reject | duplicate
- Reason:
- Existing overlap:
```

Keep this detailed enough to audit why a source was accepted or skipped, but do
not turn the full-log entry into a source summary.

## Concise Log Format

```markdown
## [YYYY-MM-DD] source-selection | Request summary

- Request: Original human request.
- Ingest now: `N`
- Deferred: `N`
- Rejected: `N`
- Duplicates: `N`
- Notes: brief rationale or next action.
- Details: `_wiki/log-full.md`
```

If full ingest happens immediately after source selection, also append normal
ingest log entries for the ingested sources.
