# Taxonomy Workflow

Use this workflow only when the human asks for taxonomy maintenance, clustering,
or structural reorganization. Do not apply this workflow during ordinary ingest,
query answering, or page writing unless the user explicitly asks to organize the
wiki structure.

## Purpose

The wiki can grow as a navigable hierarchy rather than as a flat sitemap.
`_wiki/index.md` may link to the broadest topic layer after a taxonomy pass.
Topic pages then branch into lower levels only when the material becomes dense
enough to justify a split.

This is a controlled dynamic architecture: use exactly three possible topic
levels, start shallow, add depth when it improves navigation, and merge or
rename branches when the structure no longer matches the knowledge base.

## Topic Levels

Use topic levels as navigation layers:

- `L0`: broad domains, such as statistics, AI agents, or developer tools.
- `L1`: major subdomains inside an L0 domain.
- `L2`: narrower research lines, methods, systems, or durable problem areas.

Do not create `L3` or deeper levels. If a branch seems to need more depth,
prefer a synthesis page, a clearer concept page, or a better L2 split.

## Growth Rules

Create a new child topic when at least one of these is true:

- A parent topic has roughly 8-12 or more linked content pages and is becoming
  hard to scan.
- Three or more pages form a coherent subcluster with recurring links,
  terminology, or sources.
- The human repeatedly asks questions that naturally target a narrower area.
- A source introduces a durable research line or tool family that will likely
  accumulate future pages.

Do not create a child topic for a single isolated source unless it is clearly
the start of a durable thread. Prefer linking the source from the parent topic
until more material accumulates.

Ordinary ingest may create a new L0 topic when a source clearly opens a new
broad domain that does not fit existing L0 topics. Ordinary ingest should not
split, merge, rename, or deeply reorganize existing branches; those changes
require this taxonomy workflow.

## Merge and Rename Rules

Merge or flatten a topic when:

- it has fewer than three content pages for a sustained period;
- its scope overlaps heavily with a sibling topic;
- it exists only because of an old naming choice rather than an active cluster;
- the human's questions consistently cut across it rather than through it.

When merging or renaming, preserve page content, update links and citations, run
`python3 .tools/health.py`, and record the operation in `_wiki/log.md`.

## Current Seed Hierarchy

Current L0 topics:

- `Statistics and Bayesian Computation` with slug `statistics-and-bayesian-computation`
- `AI Agents and Memory` with slug `ai-agents-and-memory`
- `Developer Tools` with slug `developer-tools`

Current L1 topics:

- `Statistics and Bayesian Computation / PARNI Research`
- `AI Agents and Memory / Self-Evolving Agent Memory`
- `Developer Tools / Version Control`

Possible future L1/L2 branches:

- `Statistics and Bayesian Computation / MCMC`
- `Statistics and Bayesian Computation / Bayesian Structure Learning`
- `AI Agents and Memory / Self-Evolving Agents`
- `AI Agents and Memory / Agent Memory`
- `AI Agents and Memory / Skill Evolution`

Treat these as seeds, not fixed commitments. Add, rename, merge, or demote them
as the wiki grows.

## Directory Layout

When a taxonomy pass reorganizes files, use topic paths under `_raw/` and
page-type directories. The path should mirror the deepest assigned topic:

```text
_raw/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/topics/l0/<L0 Topic>.md
_wiki/topics/l1/<L0 Slug>/<L1 Topic>.md
_wiki/topics/l2/<L0 Slug>/<L1 Slug>/<L2 Topic>.md
_wiki/sources/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/concepts/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/entities/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/syntheses/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/questions/<l0-slug>/<l1-slug>/<l2-slug>/
_wiki/timelines/<l0-slug>/<l1-slug>/<l2-slug>/
```

Use only as much depth as needed. For example, if `Developer Tools` only has one
subtopic, `_wiki/sources/developer-tools/version-control/` is enough; no empty
L2 directory is required.

Keep `_inbox/` flat unless the human deliberately pre-sorts files. During
ordinary ingest, do not create topic directories just for classification. A
taxonomy pass may later move raw files into `_raw/<topic-path>/`.

## Index Policy

After a taxonomy pass, `_wiki/index.md` should be the root entry point, not a
full sitemap. It should contain:

- a short description of the wiki
- an `L0 Topics` section linking to `_wiki/topics/l0/` pages
- optional global operational links such as `[[overview]]`

Do not list every source, concept, entity, or synthesis in `_wiki/index.md`.
Those links belong on topic pages. The root index should link L0 topic pages
only, so it remains a clean top-level taxonomy anchor in Obsidian Graph View.

## Topic Page Policy

Topic pages are local maps. Topic links should be strictly layered:

- `_wiki/index.md` links only to L0 topic pages.
- L0 topic pages link only to their immediate L1 child topic pages.
- L1 topic pages link only to their immediate L2 child topic pages and content
  pages assigned directly to that L1.
- L2 topic pages link to content pages assigned to that L2.

Avoid cross-layer links in taxonomy sections. For example, an L0 page should not
link directly to sources or concepts if those pages live under an L1 or L2.
Use prose sparingly if needed, but keep navigational lists layered.

## Topic Page Format

Recommended sections:

- `# Topic Name`
- `## Scope`
- `## Child Topics`
- `## Key Sources`
- `## Core Concepts`
- `## Entities`
- `## Syntheses`
- `## Questions`
- `## Timelines`
- `## Open Questions`

Keep topic pages concise. They should help navigation and clustering, not
duplicate page content.

## Ingest Classification

Do not run a full taxonomy pass during ordinary ingest. Use the ordinary ingest
workflow to capture source-backed knowledge first. The only taxonomy change
allowed during ordinary ingest is adding a clear new L0 topic, or using a broad
provisional topic when the fit is uncertain.

## Clustering Pass

When the human asks to organize or re-cluster the wiki:

1. Read `_wiki/index.md`, existing topic pages if any, and the relevant source,
   concept, entity, synthesis, question, and timeline pages.
2. Identify candidate topic clusters and their deepest useful topic paths.
3. If a topic path does not exist, decide whether to create a new child topic
   using the growth rules above.
4. Move raw files into `_raw/<topic-path>/` only after citations can be updated.
5. Move generated pages under the matching `_wiki/<page-type>/<topic-path>/`
   directory only after wikilinks can still resolve.
6. Update the relevant topic page and its parent only when child topic links or
   directly assigned content links change.
7. Update `_wiki/index.md` only when L0 topics are added, removed, or renamed.
8. Run `python3 .tools/health.py`.
9. Record the taxonomy pass in `_wiki/log.md`.

## Cross-Topic Pages

If a page belongs to multiple topics, place it under the primary topic and link
it from secondary topic pages. Do not duplicate the page. Use Related sections
to make cross-topic relationships explicit.

## Migration Policy

When reorganizing existing pages:

- Move files without changing page titles unless a rename is explicitly desired.
- Update raw source citations after moving `_raw/` files.
- Update wikilinks only when page titles or link aliases change.
- Move in small batches by topic so health checks stay interpretable.
- Run `python3 .tools/health.py` after each migration pass.
- Record the migration in `_wiki/log.md`.
