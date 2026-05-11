# Query Workflow

Use this workflow when the human asks what the wiki says about a topic, asks for
a comparison, or wants a durable synthesis from existing wiki material.

## Process

1. Read `_wiki/index.md` to identify relevant source, concept, entity,
   synthesis, question, and timeline pages.
2. Search `_wiki/` for relevant terms and wikilinks.
3. Read the most relevant pages before answering.
4. Ground factual claims in cited wiki pages or the `_raw/` sources cited by
   those pages.
5. Preserve uncertainty, contradictions, and open questions instead of smoothing
   them away.
6. If the answer has durable value, save it as either:
   - `_wiki/questions/<Question>.md` for a focused answer
   - `_wiki/syntheses/<Synthesis Title>.md` for a broader synthesis
7. Update `_wiki/index.md` and append a log entry when saving the answer.

## Saved Question Format

```markdown
---
type: question
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
sources: []
---

# Question

## Answer

## Evidence

## Follow-up Questions

## Related Pages
```

## Log Format

```markdown
## [YYYY-MM-DD] query | Question or Synthesis Title

- Created: [[Question or Synthesis Title]]
- Evidence: [[Relevant Page]], [[Another Page]]
- Notes: brief description of why the answer was saved.
```

