from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import ValidationError

from xwiki_tools.database import build_index, resolve_database
from xwiki_tools.extract import Extraction, extract_source
from xwiki_tools.mcp_server import ReadAction, SearchAction, create_server, run_server
from xwiki_tools.query import KnowledgeIndex


def frontmatter(page_type: str, *, sources: str = "[]", aliases: str = "[]") -> str:
    return (
        "---\n"
        f"type: {page_type}\n"
        "status: active\n"
        "created: 2026-10-13\n"
        "updated: 2026-10-13\n"
        "tags: [memory]\n"
        f"aliases: {aliases}\n"
        f"sources: {sources}\n"
        "---\n\n"
    )


class KnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "_wiki/topics/l0").mkdir(parents=True)
        (self.root / "_wiki/concepts").mkdir(parents=True)
        (self.root / "_wiki/sources").mkdir(parents=True)
        (self.root / "_raw/research").mkdir(parents=True)
        self.write(
            "_raw/research/memory.txt",
            "Trajectory evidence improves memory retrieval. 因果记忆保留事件关系。\n",
        )
        self.write(
            "_wiki/index.md",
            frontmatter("index") + "# Index\n\n- [[Artificial Intelligence]]\n",
        )
        self.write(
            "_wiki/topics/l0/Artificial Intelligence.md",
            frontmatter("topic")
            + "# Artificial Intelligence\n\n## Core Concepts\n\n- [[Agent Memory]]\n",
        )
        source = "_raw/research/memory.txt"
        self.write(
            "_wiki/sources/Memory Paper.md",
            frontmatter("source", sources=f'["{source}"]')
            + "# Memory Paper\n\n## Summary\n\nTrajectory-grounded memory. Source: `_raw/research/memory.txt`.\n",
        )
        self.write(
            "_wiki/concepts/Agent Memory.md",
            frontmatter(
                "concept",
                sources=f'["{source}"]',
                aliases='["Persistent Agent Memory"]',
            )
            + "# Agent Memory\n\n## Summary\n\nAgent memory stores reusable evidence. 因果记忆保留事件关系。\n\n"
            + "## Evidence\n\nSee [[Memory Paper]]. Source: `_raw/research/memory.txt`.\n",
        )
        self.database = resolve_database(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, content: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def build(self):
        return build_index(self.root)

    def test_build_search_graph_view_and_source_read(self) -> None:
        result = self.build()
        self.assertEqual(4, result["pages"])
        self.assertEqual(1, result["sources"])
        self.assertEqual([], result["warnings"])

        index = KnowledgeIndex(self.database)
        english = index.search("memory", limit=10)
        self.assertTrue(
            any(item.get("title") == "Agent Memory" for item in english["results"])
        )
        chinese = index.search("因果记忆", limit=10)
        self.assertTrue(
            any(item.get("title") == "Agent Memory" for item in chinese["results"])
        )
        raw = index.search("trajectory evidence", limit=10)
        self.assertTrue(any(item["kind"] == "source" for item in raw["results"]))

        graph = index.graph("Agent Memory")
        self.assertEqual("Memory Paper", graph["outgoing"][0]["targetTitle"])
        self.assertEqual("resolved", graph["outgoing"][0]["resolution"])
        source_graph = index.graph("Memory Paper")
        self.assertTrue(
            any(page["title"] == "Agent Memory" for page in source_graph["citedBy"])
        )

        directory = index.browse()
        self.assertEqual("Artificial Intelligence", directory["topics"][0]["title"])
        page = index.view("Agent Memory")
        section = index.view(
            "Agent Memory", section="section-1", version=page["version"]
        )
        self.assertIn("Agent memory stores", section["body"])

        source = index.read_source("_raw/research/memory.txt")
        self.assertIn("Trajectory evidence", source["segments"][0]["text"])

    def test_rebuild_replaces_stale_content(self) -> None:
        self.build()
        concept = self.root / "_wiki/concepts/Agent Memory.md"
        concept.write_text(
            concept.read_text(encoding="utf-8").replace(
                "reusable evidence", "durable evidence"
            ),
            encoding="utf-8",
        )
        self.build()
        index = KnowledgeIndex(self.database)
        self.assertTrue(
            any(
                item.get("title") == "Agent Memory"
                for item in index.search("durable")["results"]
            )
        )
        self.assertFalse(
            any(
                item.get("title") == "Agent Memory"
                for item in index.search("reusable")["results"]
            )
        )

    def test_changed_source_is_rejected_until_rebuild(self) -> None:
        self.build()
        self.write("_raw/research/memory.txt", "Changed source text.\n")
        with self.assertRaisesRegex(ValueError, "changed after indexing"):
            KnowledgeIndex(self.database).read_source("_raw/research/memory.txt")

    def test_ambiguous_wikilink_remains_visible(self) -> None:
        self.write(
            "_wiki/concepts/Other.md",
            frontmatter("concept", aliases='["Memory Paper"]')
            + "# Other\n\nA second identity.\n",
        )
        result = self.build()
        self.assertTrue(
            any(
                warning.get("kind") == "wikilink"
                and warning.get("resolution") == "ambiguous"
                for warning in result["warnings"]
            )
        )
        graph = KnowledgeIndex(self.database).graph("Agent Memory")
        self.assertEqual("ambiguous", graph["outgoing"][0]["resolution"])

    def test_fts_operators_are_treated_as_text(self) -> None:
        self.build()
        result = KnowledgeIndex(self.database).search('memory OR "*"')
        self.assertEqual('memory OR "*"', result["query"])

    def test_batch_keeps_independent_action_failures(self) -> None:
        self.build()
        batch = KnowledgeIndex(self.database).execute_batch(
            [
                {"action": "search", "query": "memory"},
                {"action": "view", "pageId": "Missing"},
            ]
        )
        self.assertEqual(1, batch["succeeded"])
        self.assertEqual(1, batch["failed"])

    def test_csv_extraction_preserves_row_locator(self) -> None:
        source = self.write("_raw/research/data.csv", "name,value\nalpha,3\n")
        extraction = extract_source(source)
        self.assertEqual("A2:B2", extraction.segments[1].locator["cell_range"])
        self.assertIn('A2="alpha"', extraction.segments[1].text)

    def test_corrupt_pdf_is_indexed_with_extraction_warning(self) -> None:
        source = "_raw/research/broken.pdf"
        (self.root / source).write_bytes(b"%PDF-1.7\nnot a valid PDF")
        self.write(
            "_wiki/sources/Broken PDF.md",
            frontmatter("source", sources=f'["{source}"]')
            + "# Broken PDF\n\n## Summary\n\nUnreadable fixture. Source: `_raw/research/broken.pdf`.\n",
        )
        result = self.build()
        warning = next(
            item for item in result["warnings"] if item.get("path") == source
        )
        self.assertFalse(warning["extracted"])
        self.assertIn("Cannot extract this source", warning["warnings"][0])

    def test_extraction_replaces_invalid_unicode(self) -> None:
        extraction = Extraction("0" * 64, "pdf")
        extraction.append("broken \ud835 text", {"page": 1}, "Page 1")
        self.assertIn("broken ? text", extraction.segments[0].text)
        self.assertTrue(
            any("Invalid Unicode" in warning for warning in extraction.warnings)
        )

    def test_mcp_models_and_server_contract(self) -> None:
        self.build()
        request = SearchAction(action="search", query="memory")
        self.assertEqual("search", request.action)
        with self.assertRaises(ValidationError):
            ReadAction(action="read", sourcePath="outside.txt")
        with self.assertRaises(ValidationError):
            SearchAction(action="search", pageType="unsupported")
        server = create_server(self.database)
        self.assertEqual("xWiki", server.name)
        with self.assertRaisesRegex(ValueError, "loopback"):
            run_server(self.database, transport="streamable-http", host="0.0.0.0")

    def test_mcp_stdio_round_trip(self) -> None:
        self.build()

        async def exercise() -> tuple[str, list[str], int]:
            repository = Path(__file__).resolve().parents[1]
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "xwiki_tools",
                    "--root",
                    str(self.root),
                    "mcp",
                ],
                cwd=str(repository),
            )
            async with (
                stdio_client(parameters) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                initialized = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "knowledge",
                    {"requests": [{"action": "search", "query": "memory", "limit": 1}]},
                )
                return (
                    initialized.server_info.name,
                    [tool.name for tool in tools.tools],
                    result.structured_content["succeeded"],
                )

        server_name, tools, succeeded = asyncio.run(exercise())
        self.assertEqual("xWiki", server_name)
        self.assertEqual(["knowledge"], tools)
        self.assertEqual(1, succeeded)


if __name__ == "__main__":
    unittest.main()
