# Graph Workflow

Use this workflow to inspect the structure of the wiki as a link graph.

## Purpose

The graph builder is deterministic. It reads explicit Obsidian-style
`[[wikilinks]]` from `_wiki/` and writes graph artifacts under `graph/`.

It does not infer semantic relationships and does not create pages from missing
links. Missing links are reported as maintenance signals only.

Run:

```bash
python3 tools/build_graph.py
```

Useful variants:

```bash
python3 tools/build_graph.py --report
python3 tools/build_graph.py --save-report
python3 tools/build_graph.py --json-only
```

## Outputs

- `graph/graph.json`: node and edge data, including unresolved wikilinks.
- `graph/graph.html`: self-contained browser visualization shell.
- `graph/graph-report.md`: optional graph health report when `--save-report`
  is used.

Generated graph outputs are reproducible maintenance artifacts. They should not
be cited as sources for factual claims.

## Report Checks

- Node and edge counts.
- Edge/node ratio.
- Orphan pages with no graph connections.
- Hub pages with unusually high degree.
- Phantom hubs: missing `[[wikilinks]]` referenced by multiple pages.
- Largest connected components.

## Page Creation Policy

Do not auto-create pages from phantom hubs. Use them as prompts for human or LLM
review. Create a page only when the target is meaningfully supported by source
material and fits the selective page policy in `_schema/page-types.md`.
