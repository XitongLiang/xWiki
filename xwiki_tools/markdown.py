"""Parse xWiki Markdown without changing the authoritative files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .text import normalize, slug

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
WIKILINK = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
SOURCE_PATH = re.compile(r"`(_raw/[^`]+)`")
EXCLUDED_PAGE_NAMES = {"log.md", "log-full.md"}


@dataclass(frozen=True)
class Link:
    target: str
    label: str | None
    anchor: str | None
    line: int


@dataclass(frozen=True)
class Section:
    heading: str
    level: int
    body: str
    ordinal: int


@dataclass(frozen=True)
class Page:
    id: str
    path: str
    title: str
    page_type: str
    status: str
    created: str | None
    updated: str | None
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    sources: tuple[str, ...]
    summary: str
    body: str
    content_hash: str
    topic_level: str | None
    links: tuple[Link, ...]
    sections: tuple[Section, ...]


def split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER.match(content)
    if not match:
        return {}, content
    loaded = yaml.safe_load(match.group(1)) or {}
    if not isinstance(loaded, dict):
        raise TypeError("Markdown frontmatter must be a YAML mapping.")
    return loaded, content[match.end() :]


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Frontmatter {field} must be a list of strings.")
    return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))


def _title(frontmatter: dict[str, Any], body: str, fallback: str) -> str:
    declared = frontmatter.get("title")
    if isinstance(declared, str) and declared.strip():
        return declared.strip()
    for line in body.splitlines():
        match = HEADING.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return fallback


def _summary(frontmatter: dict[str, Any], body: str) -> str:
    declared = frontmatter.get("summary")
    if isinstance(declared, str) and declared.strip():
        return re.sub(r"\s+", " ", declared.strip())
    paragraphs: list[str] = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith(("#", "- ", "* ", ">", "|")):
            if paragraphs:
                break
            continue
        paragraphs.append(stripped)
    return re.sub(r"\s+", " ", " ".join(paragraphs))[:1000]


def _sections(
    body: str, *, max_chars: int = 1800, overlap: int = 200
) -> tuple[Section, ...]:
    logical: list[tuple[str, int, str]] = []
    heading, level, lines = "Document", 0, []

    def flush() -> None:
        text = "\n".join(lines).strip()
        if text:
            logical.append((heading, level, text))

    in_fence = False
    for line in body.splitlines():
        marker = line.lstrip().startswith(("```", "~~~"))
        if marker:
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match:
            flush()
            heading, level, lines = match.group(2).strip(), len(match.group(1)), []
        else:
            lines.append(line)
    flush()

    result: list[Section] = []
    for section_heading, section_level, text in logical:
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                boundary = max(
                    text.rfind("\n", start + max_chars // 2, end),
                    text.rfind(" ", start + max_chars // 2, end),
                )
                if boundary > start:
                    end = boundary
            chunk = text[start:end].strip()
            if chunk:
                result.append(
                    Section(section_heading, section_level, chunk, len(result))
                )
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return tuple(result)


def _links(body: str) -> tuple[Link, ...]:
    result: list[Link] = []
    in_fence = False
    for line_number, line in enumerate(body.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in WIKILINK.finditer(line):
            raw = match.group(1).strip()
            target_part, separator, label = raw.partition("|")
            target, anchor_separator, anchor = target_part.partition("#")
            if target.strip():
                result.append(
                    Link(
                        target=target.strip(),
                        label=label.strip() if separator and label.strip() else None,
                        anchor=anchor.strip()
                        if anchor_separator and anchor.strip()
                        else None,
                        line=line_number,
                    )
                )
    return tuple(result)


def topic_level(relative_path: str) -> str | None:
    match = re.match(r"_wiki/topics/(l[012])(?:/|$)", relative_path, re.IGNORECASE)
    return match.group(1).upper() if match else None


def parse_page(path: Path, root: Path) -> Page:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(content)
    relative = path.relative_to(root).as_posix()
    title = _title(frontmatter, body, path.stem)
    declared_id = frontmatter.get("id")
    if declared_id is not None and (
        not isinstance(declared_id, str) or not declared_id.strip()
    ):
        raise ValueError(f"Invalid page id in {relative}.")
    page_id = (
        declared_id.strip()
        if isinstance(declared_id, str)
        else (f"{slug(title)}-{sha256(relative.encode()).hexdigest()[:10]}")
    )
    sources = _string_list(frontmatter.get("sources"), "sources")
    inline_sources = tuple(SOURCE_PATH.findall(body))
    return Page(
        id=page_id,
        path=relative,
        title=title,
        page_type=str(frontmatter.get("type") or "unknown"),
        status=str(frontmatter.get("status") or "needs-review"),
        created=str(frontmatter["created"])
        if frontmatter.get("created") is not None
        else None,
        updated=str(frontmatter["updated"])
        if frontmatter.get("updated") is not None
        else None,
        tags=_string_list(frontmatter.get("tags"), "tags"),
        aliases=_string_list(frontmatter.get("aliases"), "aliases"),
        sources=tuple(dict.fromkeys((*sources, *inline_sources))),
        summary=_summary(frontmatter, body),
        body=body.strip(),
        content_hash=sha256(content.encode()).hexdigest(),
        topic_level=topic_level(relative),
        links=_links(body),
        sections=_sections(body),
    )


def discover_pages(root: Path) -> list[Page]:
    wiki = root / "_wiki"
    if not wiki.exists():
        return []
    pages = []
    for path in sorted(wiki.rglob("*.md")):
        if path.name in EXCLUDED_PAGE_NAMES:
            continue
        pages.append(parse_page(path, root))
    return pages


def identity_keys(page: Page) -> set[str]:
    relative = Path(page.path).relative_to("_wiki").as_posix()
    candidates = {
        page.title,
        Path(page.path).stem,
        page.path,
        relative,
        relative.removesuffix(".md"),
        *page.aliases,
    }
    return {
        normalize(value.removesuffix(".md").strip())
        for value in candidates
        if value.strip()
    }
