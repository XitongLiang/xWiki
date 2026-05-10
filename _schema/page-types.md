# Page Types

This file defines the standard page types for `_wiki/`.

All wiki pages should include YAML frontmatter when practical:

```yaml
---
type: concept | entity | source | synthesis | question | timeline | index | log
status: draft | active | needs-review
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
sources: []
---
```

## Source Page

Purpose: summarize one raw source and preserve its provenance.

Location: `_wiki/sources/`

Recommended sections:

- `# Title`
- `## Source`
- `## Summary`
- `## Key Claims`
- `## Notable Details`
- `## Links Into Wiki`
- `## Open Questions`

Use source pages for articles, papers, transcripts, books, reports, datasets,
videos, clipped webpages, and imported notes.

## Concept Page

Purpose: explain an idea that appears across multiple sources.

Location: `_wiki/concepts/`

Recommended sections:

- `# Concept Name`
- `## Summary`
- `## Why It Matters`
- `## Evidence`
- `## Related Concepts`
- `## Open Questions`

Concept pages should be updated whenever a new source changes the understanding
of the concept.

## Entity Page

Purpose: track a person, organization, product, place, project, or institution.

Location: `_wiki/entities/`

Recommended sections:

- `# Entity Name`
- `## Summary`
- `## Known Facts`
- `## Relationships`
- `## Timeline`
- `## Sources`
- `## Open Questions`

## Synthesis Page

Purpose: combine multiple pages into a higher-level interpretation, argument,
comparison, or map.

Location: `_wiki/syntheses/`

Recommended sections:

- `# Synthesis Title`
- `## Short Answer`
- `## Main Points`
- `## Evidence`
- `## Tensions or Contradictions`
- `## Implications`
- `## Related Pages`

## Question Page

Purpose: preserve a useful answer to a question asked during exploration.

Location: `_wiki/questions/`

Recommended sections:

- `# Question`
- `## Answer`
- `## Evidence`
- `## Follow-up Questions`
- `## Related Pages`

## Timeline Page

Purpose: organize time-based knowledge across sources.

Location: `_wiki/timelines/`

Recommended sections:

- `# Timeline Title`
- `## Timeline`
- `## Notes`
- `## Sources`

Timeline entries should use ISO dates when known: `YYYY-MM-DD`.

