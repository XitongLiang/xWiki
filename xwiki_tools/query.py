"""Read-only search, graph, page, and source queries over an xWiki index."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from typing import Any

from .database import connect_readonly
from .extract import read_stable_bytes
from .text import match_expression, normalize

PAGE_TYPES = {
    "topic",
    "concept",
    "entity",
    "source",
    "synthesis",
    "question",
    "timeline",
    "index",
    "log",
    "unknown",
}
STATUSES = {"draft", "active", "needs-review"}


def _json(value: str) -> Any:
    return json.loads(value)


def _page_summary(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "pageId": row["id"],
        "path": row["path"],
        "title": row["title"],
        "type": row["type"],
        "status": row["status"],
        "summary": row["summary"],
        "tags": _json(row["tags_json"]),
        "topicLevel": row["topic_level"],
        "updated": row["updated"],
    }


class KnowledgeIndex:
    def __init__(self, database: str | Path):
        self.database = Path(database).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        return connect_readonly(self.database)

    @staticmethod
    def _filters(
        page_type: str | None, status: str | None, alias: str = "p"
    ) -> tuple[str, list[str]]:
        clauses, parameters = [], []
        if page_type is not None:
            if page_type not in PAGE_TYPES:
                raise ValueError(f"Unsupported page type: {page_type}.")
            clauses.append(f"{alias}.type=?")
            parameters.append(page_type)
        if status is not None:
            if status not in STATUSES:
                raise ValueError(f"Unsupported page status: {status}.")
            clauses.append(f"{alias}.status=?")
            parameters.append(status)
        return (" AND " + " AND ".join(clauses)) if clauses else "", parameters

    def pages(
        self,
        *,
        page_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError(
                "Page limit must be 1-1000 and offset must be nonnegative."
            )
        suffix, parameters = self._filters(page_type, status)
        where = suffix.removeprefix(" AND ") or "1"
        with closing(self._connect()) as connection:
            total = connection.execute(
                f"SELECT count(*) FROM pages p WHERE {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM pages p WHERE {where} ORDER BY title,id LIMIT ? OFFSET ?",
                [*parameters, limit, offset],
            ).fetchall()
        return {
            "indexed": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "pages": [_page_summary(row) for row in rows],
        }

    def _resolve(self, connection: sqlite3.Connection, identifier: str) -> sqlite3.Row:
        direct = connection.execute(
            "SELECT * FROM pages WHERE id=? OR path=?", (identifier, identifier)
        ).fetchall()
        if len(direct) == 1:
            return direct[0]
        key = normalize(identifier.removesuffix(".md"))
        rows = connection.execute("SELECT * FROM pages ORDER BY id").fetchall()
        matches = []
        for row in rows:
            candidates = {
                normalize(row["title"]),
                normalize(Path(row["path"]).stem),
                normalize(row["path"].removesuffix(".md")),
                normalize(
                    Path(row["path"])
                    .relative_to("_wiki")
                    .as_posix()
                    .removesuffix(".md")
                ),
                *(normalize(alias) for alias in _json(row["aliases_json"])),
            }
            if key in candidates:
                matches.append(row)
        if not matches:
            raise KeyError(f"Wiki page not found: {identifier}")
        if len(matches) > 1:
            raise ValueError(f"Wiki page identifier is ambiguous: {identifier}")
        return matches[0]

    def search(
        self,
        query: str = "",
        *,
        page_type: str | None = None,
        status: str | None = None,
        limit: int = 10,
        include_sources: bool = True,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("Search limit must be between 1 and 100.")
        if not query.strip():
            result = self.pages(page_type=page_type, status=status, limit=limit)
            return {
                "query": "",
                "results": [{"kind": "page", **page} for page in result["pages"]],
            }
        expression = match_expression(query)
        suffix, parameters = self._filters(page_type, status)
        with closing(self._connect()) as connection:
            page_rows = connection.execute(
                f"""SELECT p.*,bm25(page_fts,0,5,2,1,0.5) score,
                           snippet(page_fts,3,'[',']',' ... ',24) excerpt
                    FROM page_fts JOIN pages p ON p.id=page_fts.page_id
                    WHERE page_fts MATCH ?{suffix}
                    ORDER BY score,p.id LIMIT 201""",
                [expression, *parameters],
            ).fetchall()
            section_rows = connection.execute(
                f"""SELECT p.*,s.heading,s.ordinal,bm25(section_fts,0,0,3,1,0.5) score,
                           snippet(section_fts,3,'[',']',' ... ',24) excerpt
                    FROM section_fts
                    JOIN sections s ON s.id=section_fts.section_id
                    JOIN pages p ON p.id=section_fts.page_id
                    WHERE section_fts MATCH ?{suffix}
                    ORDER BY score,p.id,s.ordinal LIMIT 201""",
                [expression, *parameters],
            ).fetchall()
            candidates: dict[tuple[str, str], dict[str, Any]] = {}
            for rank, row in enumerate(page_rows[:200], 1):
                key = ("page", row["id"])
                candidates[key] = {
                    "rank": 1 / (60 + rank),
                    "result": {
                        "kind": "page",
                        **_page_summary(row),
                        "excerpt": row["excerpt"],
                        "matches": [],
                    },
                }
            for rank, row in enumerate(section_rows[:200], 1):
                key = ("page", row["id"])
                candidate = candidates.setdefault(
                    key,
                    {
                        "rank": 0.0,
                        "result": {
                            "kind": "page",
                            **_page_summary(row),
                            "excerpt": row["excerpt"],
                            "matches": [],
                        },
                    },
                )
                candidate["rank"] += 1 / (60 + rank)
                if len(candidate["result"]["matches"]) < 3:
                    candidate["result"]["matches"].append(
                        {
                            "heading": row["heading"],
                            "section": f"section-{row['ordinal'] + 1}",
                            "excerpt": row["excerpt"],
                        }
                    )
            source_rows = []
            if include_sources and page_type is None and status is None:
                source_rows = connection.execute(
                    """SELECT so.*,ss.heading,ss.ordinal,bm25(source_fts,0,0,3,1,0.5) score,
                              snippet(source_fts,3,'[',']',' ... ',24) excerpt
                       FROM source_fts
                       JOIN source_segments ss ON ss.id=source_fts.segment_id
                       JOIN sources so ON so.path=source_fts.source_path
                       WHERE source_fts MATCH ? ORDER BY score,so.path,ss.ordinal LIMIT 201""",
                    (expression,),
                ).fetchall()
                for rank, row in enumerate(source_rows[:200], 1):
                    key = ("source", row["path"])
                    candidate = candidates.setdefault(
                        key,
                        {
                            "rank": 0.0,
                            "result": {
                                "kind": "source",
                                "sourcePath": row["path"],
                                "fileName": row["file_name"],
                                "format": row["format"],
                                "sha256": row["sha256"],
                                "warnings": _json(row["warnings_json"]),
                                "matches": [],
                            },
                        },
                    )
                    candidate["rank"] += 1 / (60 + rank)
                    if len(candidate["result"]["matches"]) < 3:
                        candidate["result"]["matches"].append(
                            {
                                "heading": row["heading"],
                                "segment": row["ordinal"],
                                "excerpt": row["excerpt"],
                            }
                        )
            ordered = sorted(
                candidates.values(),
                key=lambda value: (
                    -value["rank"],
                    json.dumps(value["result"], sort_keys=True),
                ),
            )
        return {
            "query": query,
            "results": [candidate["result"] for candidate in ordered[:limit]],
            "candidatePoolTruncated": len(page_rows) > 200
            or len(section_rows) > 200
            or len(source_rows) > 200,
        }

    def graph(self, identifier: str, *, limit: int = 100) -> dict[str, Any]:
        if not 1 <= limit <= 1000:
            raise ValueError("Graph limit must be between 1 and 1000.")
        with closing(self._connect()) as connection:
            page = self._resolve(connection, identifier)
            outgoing = connection.execute(
                """SELECT l.*,p.title target_title,p.path target_path
                   FROM links l LEFT JOIN pages p ON p.id=l.target_page_id
                   WHERE l.source_page_id=? ORDER BY l.relation,l.target_raw LIMIT ?""",
                (page["id"], limit + 1),
            ).fetchall()
            incoming = connection.execute(
                """SELECT l.*,p.title source_title,p.path source_path
                   FROM links l JOIN pages p ON p.id=l.source_page_id
                   WHERE l.target_page_id=? ORDER BY l.relation,p.title LIMIT ?""",
                (page["id"], limit + 1),
            ).fetchall()
            sources = connection.execute(
                """SELECT s.* FROM page_sources ps JOIN sources s ON s.path=ps.source_path
                   WHERE ps.page_id=? ORDER BY s.path LIMIT ?""",
                (page["id"], limit + 1),
            ).fetchall()
            cited_by = []
            if page["type"] == "source":
                source_paths = [row["path"] for row in sources]
                if source_paths:
                    placeholders = ",".join("?" for _ in source_paths)
                    cited_by = connection.execute(
                        f"""SELECT DISTINCT p.* FROM page_sources ps JOIN pages p ON p.id=ps.page_id
                            WHERE ps.source_path IN ({placeholders}) AND p.id<>?
                            ORDER BY p.title LIMIT ?""",
                        [*source_paths, page["id"], limit + 1],
                    ).fetchall()
        return {
            "page": _page_summary(page),
            "outgoing": [
                {
                    "targetPageId": row["target_page_id"],
                    "target": row["target_raw"],
                    "targetTitle": row["target_title"],
                    "targetPath": row["target_path"],
                    "label": row["label"],
                    "anchor": row["anchor"],
                    "relation": row["relation"],
                    "resolution": row["resolution"],
                    "line": row["line"],
                }
                for row in outgoing[:limit]
            ],
            "incoming": [
                {
                    "sourcePageId": row["source_page_id"],
                    "sourceTitle": row["source_title"],
                    "sourcePath": row["source_path"],
                    "relation": row["relation"],
                    "anchor": row["anchor"],
                }
                for row in incoming[:limit]
            ],
            "sources": [
                {
                    "sourcePath": row["path"],
                    "fileName": row["file_name"],
                    "format": row["format"],
                    "sha256": row["sha256"],
                    "extracted": bool(row["extracted"]),
                    "warnings": _json(row["warnings_json"]),
                }
                for row in sources[:limit]
            ],
            "citedBy": [_page_summary(row) for row in cited_by[:limit]],
            "truncated": any(
                len(rows) > limit for rows in (outgoing, incoming, sources, cited_by)
            ),
        }

    def browse(
        self, identifier: str | None = None, *, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        if identifier is not None:
            return self.graph(identifier, limit=limit)
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError(
                "Browse limit must be 1-1000 and offset must be nonnegative."
            )
        with closing(self._connect()) as connection:
            total = connection.execute(
                "SELECT count(*) FROM pages WHERE type='topic' AND topic_level='L0'"
            ).fetchone()[0]
            rows = connection.execute(
                """SELECT * FROM pages WHERE type='topic' AND topic_level='L0'
                   ORDER BY title,id LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return {
            "indexed": True,
            "total": total,
            "offset": offset,
            "topics": [_page_summary(row) for row in rows],
        }

    def view(
        self,
        identifier: str,
        *,
        section: str | None = None,
        offset: int = 0,
        max_characters: int = 12_000,
        version: str | None = None,
    ) -> dict[str, Any]:
        if offset < 0 or not 1000 <= max_characters <= 50_000:
            raise ValueError(
                "Offset must be nonnegative and maxCharacters must be 1000-50000."
            )
        with closing(self._connect()) as connection:
            page = self._resolve(connection, identifier)
            sections = connection.execute(
                "SELECT * FROM sections WHERE page_id=? ORDER BY ordinal", (page["id"],)
            ).fetchall()
            body = page["body"]
            selected = None
            if section is not None:
                try:
                    ordinal = int(section.removeprefix("section-")) - 1
                except ValueError as exc:
                    raise ValueError("Section identifiers use section-N.") from exc
                selected = next(
                    (row for row in sections if row["ordinal"] == ordinal), None
                )
                if selected is None:
                    raise KeyError(f"Section not found: {section}")
                body = selected["body"]
            current_version = page["content_hash"]
            if version is not None and version != current_version:
                raise ValueError(
                    "Page version changed; restart the read from offset 0."
                )
            if (offset or section) and version is None:
                raise ValueError(
                    "Section and continuation reads require the returned version."
                )
            if offset > len(body):
                raise ValueError("Read offset exceeds the selected text length.")
            end = min(offset + max_characters, len(body))
            source_rows = connection.execute(
                """SELECT s.* FROM page_sources ps JOIN sources s ON s.path=ps.source_path
                   WHERE ps.page_id=? ORDER BY s.path""",
                (page["id"],),
            ).fetchall()
        return {
            "page": _page_summary(page),
            "version": current_version,
            "section": section,
            "sections": [
                {
                    "id": f"section-{row['ordinal'] + 1}",
                    "heading": row["heading"],
                    "level": row["level"],
                }
                for row in sections
            ],
            "body": body[offset:end],
            "offset": offset,
            "totalCharacters": len(body),
            "truncated": end < len(body),
            "nextOffset": end if end < len(body) else None,
            "sources": [
                {
                    "sourcePath": row["path"],
                    "fileName": row["file_name"],
                    "format": row["format"],
                    "sha256": row["sha256"],
                }
                for row in source_rows
            ],
        }

    def read_source(
        self, source_path: str, *, start: int = 0, limit: int = 3
    ) -> dict[str, Any]:
        if start < 0 or not 1 <= limit <= 10:
            raise ValueError("Source start must be nonnegative and limit must be 1-10.")
        with closing(self._connect()) as connection:
            source = connection.execute(
                "SELECT * FROM sources WHERE path=?", (source_path,)
            ).fetchone()
            if source is None:
                raise KeyError(f"Indexed source not found: {source_path}")
            if not source["extracted"]:
                raise ValueError(
                    "Source text is not available; rebuild with source extraction enabled."
                )
            root_row = connection.execute(
                "SELECT value FROM metadata WHERE key='root'"
            ).fetchone()
            root = Path(root_row[0]).resolve()
            raw_root = (root / "_raw").resolve()
            file_path = (root / source_path).resolve()
            try:
                file_path.relative_to(raw_root)
            except ValueError as exc:
                raise ValueError("Indexed source path escapes _raw/.") from exc
            content = read_stable_bytes(file_path)
            if sha256(content).hexdigest() != source["sha256"]:
                raise ValueError(
                    "Source changed after indexing; rebuild before reading it."
                )
            total = connection.execute(
                "SELECT count(*) FROM source_segments WHERE source_path=?",
                (source_path,),
            ).fetchone()[0]
            rows = connection.execute(
                """SELECT * FROM source_segments WHERE source_path=? AND ordinal>=?
                   ORDER BY ordinal LIMIT ?""",
                (source_path, start, limit),
            ).fetchall()
        return {
            "sourcePath": source["path"],
            "fileName": source["file_name"],
            "format": source["format"],
            "sha256": source["sha256"],
            "totalSegments": total,
            "segments": [
                {
                    "segment": row["ordinal"],
                    "heading": row["heading"],
                    "locator": _json(row["locator_json"]),
                    "text": row["body"],
                }
                for row in rows
            ],
            "nextStart": rows[-1]["ordinal"] + 1
            if rows and rows[-1]["ordinal"] + 1 < total
            else None,
            "warnings": _json(source["warnings_json"]),
        }

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        name = action.get("action")
        if name == "search":
            return self.search(
                str(action.get("query", "")),
                page_type=action.get("pageType"),
                status=action.get("status"),
                limit=int(action.get("limit", 10)),
                include_sources=bool(action.get("includeSources", True)),
            )
        if name == "browse":
            return self.browse(
                action.get("pageId"),
                limit=int(action.get("limit", 100)),
                offset=int(action.get("offset", 0)),
            )
        if name == "view":
            return self.view(
                str(action["pageId"]),
                section=action.get("section"),
                offset=int(action.get("offset", 0)),
                max_characters=int(action.get("maxCharacters", 12_000)),
                version=action.get("version"),
            )
        if name == "read":
            return self.read_source(
                str(action["sourcePath"]),
                start=int(action.get("start", 0)),
                limit=int(action.get("limit", 3)),
            )
        raise ValueError("Action must be search, browse, view, or read.")

    def execute_batch(self, requests: list[dict[str, Any]]) -> dict[str, Any]:
        if not 1 <= len(requests) <= 10:
            raise ValueError("A knowledge batch must contain one to ten actions.")
        results = []
        for index, action in enumerate(requests):
            name = action.get("action") if isinstance(action, dict) else None
            try:
                if not isinstance(action, dict):
                    raise TypeError("Each request must be an object.")
                results.append(
                    {
                        "requestIndex": index,
                        "action": name,
                        "ok": True,
                        "result": self.execute(action),
                    }
                )
            except (
                KeyError,
                TypeError,
                ValueError,
                FileNotFoundError,
                RuntimeError,
                sqlite3.Error,
            ) as error:
                results.append(
                    {
                        "requestIndex": index,
                        "action": name,
                        "ok": False,
                        "error": {"code": type(error).__name__, "detail": str(error)},
                    }
                )
        return {
            "total": len(results),
            "succeeded": sum(item["ok"] for item in results),
            "failed": sum(not item["ok"] for item in results),
            "results": results,
        }
