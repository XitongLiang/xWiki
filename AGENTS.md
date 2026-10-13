# xWiki Instructions

Before maintaining this wiki, read:

- `_schema/AGENTS.md`
- `_schema/page-types.md`
- `_schema/ingest-workflow.md`
- `_schema/source-selection-workflow.md`
- `_schema/citation-style.md`
- `_schema/lint-workflow.md`
- `_schema/health-workflow.md`
- `_schema/taxonomy-workflow.md`
- `_schema/query-workflow.md`
- `_schema/conversion-workflow.md`
- `_schema/indexing-workflow.md`
- `_schema/mcp-workflow.md`

For source ingestion, source analysis that should enter the Wiki, or explicit
taxonomy work, use `.agents/skills/xwiki-ingest/SKILL.md` as the operational
entry point. The `_schema/` files remain authoritative.

This project follows an LLM-maintained wiki pattern:

- `_inbox/` contains new material waiting to be ingested.
- `_raw/` contains immutable source material after ingestion begins.
- `_wiki/` contains generated markdown knowledge pages.
- `_schema/` contains the operating rules for maintaining the wiki.
- `.agents/skills/xwiki-ingest/` routes repository maintenance through those
  rules without duplicating them.
- `skills/xwiki-knowledge-mcp/` is a portable, read-only retrieval skill for
  external agents connected to the xWiki MCP server.
