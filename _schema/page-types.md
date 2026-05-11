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

For research papers, add these sections when useful:

- `## Research Problem`
- `## Method`
- `## Method Structure`
- `## Mechanism Analysis`
- `## Experiments`
- `## Key Results`
- `## Key Figures or Tables`
- `## Novelty`
- `## Code or Implementation Notes`
- `## Limitations`
- `## Future Work`
- `## Related Work Position`

Paper source pages should stay in English. Preserve all known authors in the
source metadata, but do not create author entity pages by default. These notes
are wiki summaries, not longform blog posts: keep prose concise, cite source
paths, and avoid turning the page into a full article rewrite.

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
Entity pages are selective anchors, not automatic pages for every author or
proper noun mentioned in a source.

Location: `_wiki/entities/`

Recommended sections:

- `# Entity Name`
- `## Summary`
- `## Known Facts`
- `## Relationships`
- `## Timeline`
- `## Sources`
- `## Open Questions`

Create human entity pages only when the person is useful to track across the
wiki, such as recurring authors, collaborators, advisors, or researchers whose
body of work matters to the human. For ordinary one-source authors, keep names
in the source citation instead.

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
