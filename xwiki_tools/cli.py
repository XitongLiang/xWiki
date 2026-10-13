"""Command-line interface for extraction, indexing, retrieval, graph, and MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .database import build_index, resolve_database
from .extract import extract_source
from .query import KnowledgeIndex

REPO_ROOT = Path(__file__).resolve().parent.parent


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="xwiki",
        description="Build and query a local SQLite projection of an xWiki Markdown vault.",
    )
    root.add_argument("--root", default=str(REPO_ROOT), help="xWiki repository root.")
    root.add_argument(
        "--database", help="SQLite index path. Defaults to .xwiki/knowledge.sqlite."
    )
    commands = root.add_subparsers(dest="command", required=True)

    extract = commands.add_parser(
        "extract", help="Extract local source text with physical locators."
    )
    extract.add_argument("source")
    extract.add_argument("--encoding", default="utf-8")

    build = commands.add_parser(
        "build", help="Atomically rebuild the local knowledge index."
    )
    build.add_argument("--skip-source-text", action="store_true")
    build.add_argument("--encoding", default="utf-8")

    search = commands.add_parser(
        "search", help="Search indexed Wiki pages and raw-source text."
    )
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--type", dest="page_type")
    search.add_argument("--status", choices=("draft", "active", "needs-review"))
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--pages-only", action="store_true")

    pages = commands.add_parser("pages", help="List indexed Wiki pages.")
    pages.add_argument("--type", dest="page_type")
    pages.add_argument("--status", choices=("draft", "active", "needs-review"))
    pages.add_argument("--limit", type=int, default=100)
    pages.add_argument("--offset", type=int, default=0)

    browse = commands.add_parser(
        "browse", help="Browse L0 topics or one page's graph neighborhood."
    )
    browse.add_argument("page_id", nargs="?")
    browse.add_argument("--limit", type=int, default=100)
    browse.add_argument("--offset", type=int, default=0)

    graph = commands.add_parser(
        "graph", help="Inspect incoming links, outgoing links, and provenance."
    )
    graph.add_argument("page_id")
    graph.add_argument("--limit", type=int, default=100)

    view = commands.add_parser("view", help="Read one indexed Wiki page or section.")
    view.add_argument("page_id")
    view.add_argument("--section")
    view.add_argument("--offset", type=int, default=0)
    view.add_argument("--max-characters", type=int, default=12_000)
    view.add_argument("--version")

    read = commands.add_parser("read", help="Read indexed raw-source segments.")
    read.add_argument("source_path")
    read.add_argument("--start", type=int, default=0)
    read.add_argument("--limit", type=int, default=3)

    mcp = commands.add_parser("mcp", help="Run the read-only local MCP server.")
    mcp.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default="stdio"
    )
    mcp.add_argument("--host", default="127.0.0.1")
    mcp.add_argument("--port", type=int, default=8765)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    root = Path(arguments.root).expanduser().resolve()
    database = resolve_database(root, arguments.database)
    try:
        if arguments.command == "extract":
            emit(
                extract_source(
                    Path(arguments.source).expanduser().resolve(),
                    encoding=arguments.encoding,
                ).as_dict()
            )
            return 0
        if arguments.command == "build":
            emit(
                build_index(
                    root,
                    database=database,
                    include_source_text=not arguments.skip_source_text,
                    encoding=arguments.encoding,
                )
            )
            return 0
        if arguments.command == "mcp":
            from .mcp_server import run_server

            run_server(
                database,
                transport=arguments.transport,
                host=arguments.host,
                port=arguments.port,
            )
            return 0
        index = KnowledgeIndex(database)
        if arguments.command == "search":
            emit(
                index.search(
                    arguments.query,
                    page_type=arguments.page_type,
                    status=arguments.status,
                    limit=arguments.limit,
                    include_sources=not arguments.pages_only,
                )
            )
        elif arguments.command == "pages":
            emit(
                index.pages(
                    page_type=arguments.page_type,
                    status=arguments.status,
                    limit=arguments.limit,
                    offset=arguments.offset,
                )
            )
        elif arguments.command == "browse":
            emit(
                index.browse(
                    arguments.page_id, limit=arguments.limit, offset=arguments.offset
                )
            )
        elif arguments.command == "graph":
            emit(index.graph(arguments.page_id, limit=arguments.limit))
        elif arguments.command == "view":
            emit(
                index.view(
                    arguments.page_id,
                    section=arguments.section,
                    offset=arguments.offset,
                    max_characters=arguments.max_characters,
                    version=arguments.version,
                )
            )
        elif arguments.command == "read":
            emit(
                index.read_source(
                    arguments.source_path, start=arguments.start, limit=arguments.limit
                )
            )
        return 0
    except KeyboardInterrupt:
        return 130
    except (FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError) as error:
        print(f"xwiki: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
