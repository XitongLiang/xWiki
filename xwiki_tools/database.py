"""Atomic SQLite projection of xWiki Markdown and cited raw sources."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .extract import (
    EXTRACTOR_VERSION,
    Extraction,
    Segment,
    detect_format,
    extract_source,
    read_stable_bytes,
)
from .markdown import Page, discover_pages, identity_keys
from .text import normalize, token_text

SCHEMA_VERSION = 1
DEFAULT_DATABASE = Path(".xwiki/knowledge.sqlite")
ROUTINE_EXTRACTION_WARNINGS = {
    "PDF text order and table layout require source review; images are not analyzed and OCR is not performed.",
    "Spreadsheet formatting, charts, and merged-cell meaning require source review.",
    "XLS extraction reads stored values and does not recalculate formulas.",
}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT;
CREATE TABLE pages (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    created TEXT,
    updated TEXT,
    tags_json TEXT NOT NULL CHECK(json_valid(tags_json)),
    aliases_json TEXT NOT NULL CHECK(json_valid(aliases_json)),
    sources_json TEXT NOT NULL CHECK(json_valid(sources_json)),
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    topic_level TEXT CHECK(topic_level IN ('L0','L1','L2'))
) STRICT;
CREATE INDEX pages_type_status ON pages(type, status, title);
CREATE TABLE sections (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
    heading TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 0 AND 6),
    body TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    UNIQUE(page_id, ordinal)
) STRICT;
CREATE TABLE links (
    id INTEGER PRIMARY KEY,
    source_page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    target_page_id TEXT REFERENCES pages(id) ON DELETE CASCADE,
    target_raw TEXT NOT NULL,
    label TEXT,
    anchor TEXT,
    relation TEXT NOT NULL CHECK(relation IN ('related','child_topic','contains')),
    resolution TEXT NOT NULL CHECK(resolution IN ('resolved','missing','ambiguous')),
    line INTEGER NOT NULL CHECK(line >= 1),
    CHECK((resolution = 'resolved') = (target_page_id IS NOT NULL))
) STRICT;
CREATE INDEX links_outgoing ON links(source_page_id, relation, target_page_id);
CREATE INDEX links_incoming ON links(target_page_id, relation, source_page_id);
CREATE TABLE sources (
    path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    file_name TEXT NOT NULL,
    format TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK(byte_size > 0),
    extracted INTEGER NOT NULL CHECK(extracted IN (0,1)),
    extractor_version TEXT,
    warnings_json TEXT NOT NULL CHECK(json_valid(warnings_json))
) STRICT;
CREATE TABLE page_sources (
    page_id TEXT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL REFERENCES sources(path) ON DELETE CASCADE,
    PRIMARY KEY(page_id, source_path)
) STRICT;
CREATE INDEX source_backlinks ON page_sources(source_path, page_id);
CREATE TABLE source_segments (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL REFERENCES sources(path) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK(ordinal >= 0),
    heading TEXT,
    body TEXT NOT NULL,
    locator_json TEXT NOT NULL CHECK(json_valid(locator_json)),
    content_hash TEXT NOT NULL,
    UNIQUE(source_path, ordinal)
) STRICT;
CREATE INDEX source_segment_order ON source_segments(source_path, ordinal);
CREATE VIRTUAL TABLE page_fts USING fts5(
    page_id UNINDEXED, title, summary, body, tokens,
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE section_fts USING fts5(
    section_id UNINDEXED, page_id UNINDEXED, heading, body, tokens,
    tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE source_fts USING fts5(
    segment_id UNINDEXED, source_path UNINDEXED, heading, body, tokens,
    tokenize='unicode61 remove_diacritics 2'
);
"""


class BuildLocked(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def resolve_database(root: Path, database: str | Path | None = None) -> Path:
    candidate = Path(database) if database is not None else DEFAULT_DATABASE
    return (
        candidate.expanduser().resolve()
        if candidate.is_absolute()
        else (root / candidate).resolve()
    )


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


@contextmanager
def build_lock(database: Path) -> Iterator[None]:
    database.parent.mkdir(parents=True, exist_ok=True)
    lock = database.with_suffix(database.suffix + ".build.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise BuildLocked(
            f"Another build owns {lock}. Remove a stale lock only after confirming no build is running."
        ) from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def connect_readonly(database: Path) -> sqlite3.Connection:
    if not database.exists():
        raise FileNotFoundError(
            f"Knowledge index not found: {database}. Run the build command first."
        )
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    version = connection.execute(
        "SELECT value FROM metadata WHERE key='schema_version'"
    ).fetchone()
    if version is None or int(version[0]) != SCHEMA_VERSION:
        connection.close()
        raise RuntimeError("Knowledge index schema is incompatible. Rebuild the index.")
    return connection


def _validate_pages(pages: list[Page]) -> None:
    ids: dict[str, str] = {}
    for page in pages:
        previous = ids.get(page.id)
        if previous is not None:
            raise ValueError(
                f"Duplicate page id {page.id!r}: {previous} and {page.path}."
            )
        ids[page.id] = page.path


def _identity_index(pages: list[Page]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for page in pages:
        for key in identity_keys(page):
            index.setdefault(key, []).append(page.id)
    return index


def _relation(source: Page, target: Page | None) -> str:
    if target is None or source.page_type != "topic":
        return "related"
    if target.page_type == "topic":
        levels = {"L0": 0, "L1": 1, "L2": 2}
        if (
            source.topic_level in levels
            and target.topic_level in levels
            and levels[target.topic_level] == levels[source.topic_level] + 1
        ):
            return "child_topic"
        return "related"
    return "contains"


def _insert_page(connection: sqlite3.Connection, page: Page) -> None:
    connection.execute(
        """INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            page.id,
            page.path,
            page.title,
            page.page_type,
            page.status,
            page.created,
            page.updated,
            json.dumps(page.tags, ensure_ascii=False),
            json.dumps(page.aliases, ensure_ascii=False),
            json.dumps(page.sources, ensure_ascii=False),
            page.summary,
            page.body,
            page.content_hash,
            page.topic_level,
        ),
    )
    combined = "\n".join((page.title, page.summary, page.body, " ".join(page.tags)))
    connection.execute(
        "INSERT INTO page_fts VALUES (?,?,?,?,?)",
        (page.id, page.title, page.summary, page.body, token_text(combined)),
    )
    for section in page.sections:
        section_id = sha256(
            f"{page.id}:{section.ordinal}:{section.body}".encode()
        ).hexdigest()
        connection.execute(
            "INSERT INTO sections VALUES (?,?,?,?,?,?,?)",
            (
                section_id,
                page.id,
                section.ordinal,
                section.heading,
                section.level,
                section.body,
                sha256(section.body.encode()).hexdigest(),
            ),
        )
        connection.execute(
            "INSERT INTO section_fts VALUES (?,?,?,?,?)",
            (
                section_id,
                page.id,
                section.heading,
                section.body,
                token_text(section.heading + "\n" + section.body),
            ),
        )


def _source_path(root: Path, relative: str) -> Path:
    if not relative.startswith("_raw/"):
        raise ValueError(f"Source paths must start with _raw/: {relative}")
    raw_root = (root / "_raw").resolve()
    path = (root / relative).resolve()
    if not _inside(path, raw_root):
        raise ValueError(f"Source path escapes _raw/: {relative}")
    if not path.is_file():
        raise FileNotFoundError(f"Declared source does not exist: {relative}")
    return path


def _cached_extraction(
    database: Path, source_path: str, source_hash: str
) -> Extraction | None:
    if not database.exists():
        return None
    try:
        old = connect_readonly(database)
    except (OSError, sqlite3.Error, RuntimeError, ValueError):
        return None
    try:
        source = old.execute(
            "SELECT format,extractor_version,warnings_json FROM sources WHERE path=? AND sha256=? AND extracted=1",
            (source_path, source_hash),
        ).fetchone()
        if source is None or source["extractor_version"] != EXTRACTOR_VERSION:
            return None
        rows = old.execute(
            "SELECT heading,body,locator_json FROM source_segments WHERE source_path=? ORDER BY ordinal",
            (source_path,),
        ).fetchall()
        return Extraction(
            source_sha256=source_hash,
            format=source["format"],
            segments=[
                Segment(row["body"], json.loads(row["locator_json"]), row["heading"])
                for row in rows
            ],
            warnings=json.loads(source["warnings_json"]),
            character_count=sum(len(row["body"]) for row in rows),
        )
    finally:
        old.close()


def _insert_source(
    connection: sqlite3.Connection,
    root: Path,
    database: Path,
    relative: str,
    *,
    include_text: bool,
    encoding: str,
) -> dict[str, Any]:
    path = _source_path(root, relative)
    content = read_stable_bytes(path)
    source_hash = sha256(content).hexdigest()
    source_format = detect_format(path, content)
    extraction: Extraction | None = None
    warnings: list[str] = []
    if include_text:
        extraction = _cached_extraction(database, relative, source_hash)
        if extraction is None:
            try:
                extraction = extract_source(path, encoding=encoding)
            except (RuntimeError, ValueError, UnicodeError) as error:
                warnings.append(str(error))
            except Exception:  # noqa: BLE001 - isolate third-party parser failures per source.
                warnings.append(
                    "Cannot extract this source. Check file integrity, encryption, format, and text encoding."
                )
        if extraction is not None:
            warnings.extend(extraction.warnings)
    connection.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
        (
            relative,
            source_hash,
            path.name,
            source_format,
            len(content),
            int(extraction is not None),
            EXTRACTOR_VERSION if extraction is not None else None,
            json.dumps(warnings, ensure_ascii=False),
        ),
    )
    if extraction is not None:
        for ordinal, segment in enumerate(extraction.segments):
            body = (
                (segment.context + "\n" + segment.text).strip()
                if segment.context
                else segment.text
            )
            segment_id = sha256(
                json.dumps(
                    [relative, source_hash, ordinal, segment.locator], sort_keys=True
                ).encode()
            ).hexdigest()
            connection.execute(
                "INSERT INTO source_segments VALUES (?,?,?,?,?,?,?)",
                (
                    segment_id,
                    relative,
                    ordinal,
                    segment.heading,
                    body,
                    json.dumps(segment.locator, ensure_ascii=False, sort_keys=True),
                    sha256(body.encode()).hexdigest(),
                ),
            )
            if body.strip():
                connection.execute(
                    "INSERT INTO source_fts VALUES (?,?,?,?,?)",
                    (
                        segment_id,
                        relative,
                        segment.heading or "",
                        body,
                        token_text((segment.heading or "") + "\n" + body),
                    ),
                )
    return {
        "path": relative,
        "format": source_format,
        "extracted": extraction is not None,
        "warnings": warnings,
    }


def _check_integrity(connection: sqlite3.Connection) -> None:
    result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError("SQLite integrity check failed.")
    for table in ("page_fts", "section_fts", "source_fts"):
        connection.execute(f"INSERT INTO {table}({table}) VALUES('integrity-check')")


def build_index(
    root: str | Path,
    *,
    database: str | Path | None = None,
    include_source_text: bool = True,
    encoding: str = "utf-8",
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    if not (root_path / "_wiki").is_dir() or not (root_path / "_raw").is_dir():
        raise ValueError("The repository must contain _wiki/ and _raw/ directories.")
    database_path = resolve_database(root_path, database)
    if not _inside(database_path, root_path) and database is None:
        raise ValueError("Default database path must remain inside the repository.")
    pages = discover_pages(root_path)
    _validate_pages(pages)
    page_by_id = {page.id: page for page in pages}
    identities = _identity_index(pages)
    declared_sources = sorted({source for page in pages for source in page.sources})
    warnings: list[dict[str, Any]] = []

    with build_lock(database_path):
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=database_path.name + ".",
            suffix=".tmp",
            dir=database_path.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            connection = sqlite3.connect(temporary)
            connection.row_factory = sqlite3.Row
            try:
                connection.executescript(SCHEMA)
                connection.execute("BEGIN")
                for page in pages:
                    _insert_page(connection, page)
                source_results = []
                for source in declared_sources:
                    result = _insert_source(
                        connection,
                        root_path,
                        database_path,
                        source,
                        include_text=include_source_text,
                        encoding=encoding,
                    )
                    source_results.append(result)
                    actionable = [
                        warning
                        for warning in result["warnings"]
                        if warning not in ROUTINE_EXTRACTION_WARNINGS
                    ]
                    if actionable:
                        warnings.append(
                            {
                                "kind": "source_extraction",
                                **result,
                                "warnings": actionable,
                            }
                        )
                for page in pages:
                    for source in page.sources:
                        connection.execute(
                            "INSERT INTO page_sources VALUES (?,?)", (page.id, source)
                        )
                    for link in page.links:
                        matches = identities.get(
                            normalize(link.target.removesuffix(".md")), []
                        )
                        resolution = (
                            "resolved"
                            if len(matches) == 1
                            else "ambiguous"
                            if matches
                            else "missing"
                        )
                        target_id = matches[0] if resolution == "resolved" else None
                        target = (
                            page_by_id.get(target_id) if target_id is not None else None
                        )
                        connection.execute(
                            """INSERT INTO links
                               (source_page_id,target_page_id,target_raw,label,anchor,relation,resolution,line)
                               VALUES (?,?,?,?,?,?,?,?)""",
                            (
                                page.id,
                                target_id,
                                link.target,
                                link.label,
                                link.anchor,
                                _relation(page, target),
                                resolution,
                                link.line,
                            ),
                        )
                        if resolution != "resolved":
                            warnings.append(
                                {
                                    "kind": "wikilink",
                                    "resolution": resolution,
                                    "page": page.path,
                                    "target": link.target,
                                    "line": link.line,
                                }
                            )
                metadata = {
                    "schema_version": str(SCHEMA_VERSION),
                    "built_at": utc_now(),
                    "root": str(root_path),
                    "page_count": str(len(pages)),
                    "source_count": str(len(declared_sources)),
                    "extractor_version": EXTRACTOR_VERSION,
                    "search_strategy": "nfkc-word-cjk-bigram-v1",
                }
                connection.executemany(
                    "INSERT INTO metadata VALUES (?,?)", metadata.items()
                )
                _check_integrity(connection)
                connection.commit()
            finally:
                connection.close()
            os.replace(temporary, database_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return {
        "database": str(database_path),
        "pages": len(pages),
        "sources": len(declared_sources),
        "extracted_sources": sum(result["extracted"] for result in source_results),
        "source_warning_count": sum(
            len(result["warnings"]) for result in source_results
        ),
        "source_text": include_source_text,
        "warnings": warnings,
    }
