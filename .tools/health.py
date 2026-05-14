#!/usr/bin/env python3
"""Deterministic structural health checks for xWiki.

This script uses no LLM calls. It checks file hygiene, index coverage, log
coverage, and source-ingest consistency so it can be run before heavier wiki
maintenance.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = REPO_ROOT / "_inbox"
RAW_DIR = REPO_ROOT / "_raw"
WIKI_DIR = REPO_ROOT / "_wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"

REPORT_NAMES = {
    "health-report.md",
    "lint-report.md",
    "graph-report.md",
}
IGNORED_SOURCE_NAMES = {
    ".DS_Store",
    ".gitkeep",
}
META_NAMES = {
    "index.md",
    "log.md",
}
STUB_THRESHOLD_CHARS = 100


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def strip_frontmatter(content: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n?", "", content, flags=re.DOTALL).strip()


def all_wiki_pages() -> list[Path]:
    if not WIKI_DIR.exists():
        return []
    excluded = META_NAMES | REPORT_NAMES
    return sorted(p for p in WIKI_DIR.rglob("*.md") if p.name not in excluded)


def source_pages() -> list[Path]:
    source_dir = WIKI_DIR / "sources"
    if not source_dir.exists():
        return []
    return sorted(source_dir.rglob("*.md"))


def raw_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(p for p in RAW_DIR.rglob("*") if p.is_file() and p.name not in IGNORED_SOURCE_NAMES)


def inbox_files() -> list[Path]:
    if not INBOX_DIR.exists():
        return []
    return sorted(p for p in INBOX_DIR.rglob("*") if p.is_file() and p.name not in IGNORED_SOURCE_NAMES)


def wiki_page_names(pages: list[Path]) -> dict[str, str]:
    names: dict[str, str] = {}
    for page in pages + [INDEX_FILE, WIKI_DIR / "overview.md"]:
        if not page.exists() or page.suffix != ".md":
            continue
        content = read_text(page)
        title = extract_title(content) or page.stem
        candidates = {
            page.stem,
            title,
            rel(page),
            page.relative_to(WIKI_DIR).as_posix(),
        }
        for candidate in candidates:
            names[normalize_name(candidate)] = rel(page)
    return names


def normalize_name(value: str) -> str:
    value = value.strip()
    value = value.split("|", 1)[0]
    value = value.split("#", 1)[0]
    value = value.removesuffix(".md")
    return re.sub(r"\s+", " ", value).casefold()


def extract_title(content: str) -> str:
    fm_title = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    if fm_title:
        return fm_title.group(1).strip()
    heading = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    return heading.group(1).strip() if heading else ""


def extract_source_paths(content: str) -> set[str]:
    return set(re.findall(r"`(_raw/[^`]+)`", content))


def check_stub_pages(pages: list[Path]) -> list[dict]:
    stubs = []
    for page in pages:
        content = read_text(page)
        body = strip_frontmatter(content)
        if len(body) < STUB_THRESHOLD_CHARS:
            stubs.append(
                {
                    "path": rel(page),
                    "body_chars": len(body),
                    "status": "empty" if not body else "stub",
                }
            )
    return stubs


def check_index_sync(pages: list[Path]) -> dict:
    index = read_text(INDEX_FILE)
    names = wiki_page_names(pages)
    linked_names = {normalize_name(m) for m in re.findall(r"\[\[([^\]]+)\]\]", index)}
    linked_paths = {names[name] for name in linked_names if name in names}

    actual_paths = {
        rel(page)
        for page in pages
        if page.name not in REPORT_NAMES and page.relative_to(WIKI_DIR).as_posix() != "overview.md"
    }
    reachable_paths = set(linked_paths)
    queue = list(linked_paths)
    while queue:
        current = queue.pop(0)
        current_path = REPO_ROOT / current
        links = {normalize_name(m) for m in re.findall(r"\[\[([^\]]+)\]\]", read_text(current_path))}
        for link in links:
            target = names.get(link)
            if target and target not in reachable_paths:
                reachable_paths.add(target)
                queue.append(target)

    missing = sorted(actual_paths - reachable_paths)

    unresolved = sorted(
        {
            link
            for link in re.findall(r"\[\[([^\]]+)\]\]", index)
            if normalize_name(link) not in names
        }
    )

    return {
        "on_disk_not_in_index": missing,
        "index_links_unresolved": unresolved,
    }


def check_broken_wikilinks(pages: list[Path]) -> list[dict]:
    names = wiki_page_names(pages)
    broken = []
    for page in pages + [INDEX_FILE, WIKI_DIR / "overview.md"]:
        if not page.exists():
            continue
        links = sorted(set(re.findall(r"\[\[([^\]]+)\]\]", read_text(page))))
        missing = [link for link in links if normalize_name(link) not in names]
        if missing:
            broken.append({"path": rel(page), "links": missing})
    return broken


def check_log_coverage() -> list[dict]:
    log = read_text(LOG_FILE)
    logged_titles = {
        m.group(1).strip().casefold()
        for m in re.finditer(r"^## \[\d{4}-\d{2}-\d{2}\] ingest \| (.+)$", log, re.MULTILINE)
    }
    logged_wikilinks = {normalize_name(m) for m in re.findall(r"\[\[([^\]]+)\]\]", log)}
    missing = []
    for page in source_pages():
        title = extract_title(read_text(page)) or page.stem
        slug_title = page.stem.replace("-", " ").replace("_", " ").casefold()
        normalized_title = normalize_name(title)
        if (
            title.casefold() not in logged_titles
            and slug_title not in logged_titles
            and normalized_title not in logged_wikilinks
        ):
            missing.append({"path": rel(page), "title": title})
    return missing


def check_raw_source_coverage() -> list[dict]:
    cited_paths: set[str] = set()
    for page in source_pages():
        cited_paths.update(extract_source_paths(read_text(page)))

    missing = []
    for source in raw_files():
        source_rel = rel(source)
        if source_rel not in cited_paths:
            missing.append({"path": source_rel})
    return missing


def run_health() -> dict:
    pages = all_wiki_pages()
    return {
        "date": date.today().isoformat(),
        "total_wiki_pages": len(pages),
        "inbox_files": [rel(p) for p in inbox_files()],
        "stub_pages": check_stub_pages(pages),
        "index_sync": check_index_sync(pages),
        "broken_wikilinks": check_broken_wikilinks(pages),
        "log_coverage": check_log_coverage(),
        "raw_source_coverage": check_raw_source_coverage(),
    }


def format_report(results: dict) -> str:
    lines = [
        f"# xWiki Health Report - {results['date']}",
        "",
        f"Scanned {results['total_wiki_pages']} wiki pages. Checks are deterministic and use no LLM calls.",
        "",
    ]

    sections = [
        ("Inbox Files", results["inbox_files"], "No pending inbox files."),
        ("Stub Pages", results["stub_pages"], "No empty or stub wiki pages."),
        (
            "Index Sync: Missing From Index",
            results["index_sync"]["on_disk_not_in_index"],
            "All wiki pages are represented in the index.",
        ),
        (
            "Index Sync: Unresolved Index Links",
            results["index_sync"]["index_links_unresolved"],
            "All index wikilinks resolve.",
        ),
        ("Broken Wikilinks", results["broken_wikilinks"], "No broken wikilinks found."),
        ("Log Coverage", results["log_coverage"], "All source pages have ingest log coverage."),
        (
            "Raw Source Coverage",
            results["raw_source_coverage"],
            "All raw files are cited by source pages.",
        ),
    ]

    for title, items, empty_message in sections:
        lines.extend([f"## {title} ({len(items)})", ""])
        if not items:
            lines.extend([empty_message, ""])
            continue
        for item in items:
            if isinstance(item, str):
                lines.append(f"- `{item}`")
            elif "links" in item:
                joined = ", ".join(f"`[[{link}]]`" for link in item["links"])
                lines.append(f"- `{item['path']}`: {joined}")
            elif "title" in item:
                lines.append(f"- `{item['path']}` - {item['title']}")
            elif "body_chars" in item:
                lines.append(f"- `{item['path']}` - {item['status']} ({item['body_chars']} body chars)")
            else:
                lines.append(f"- `{item['path']}`")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic xWiki health checks.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--save", action="store_true", help="Save markdown report to _wiki/health-report.md.")
    args = parser.parse_args()

    results = run_health()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = format_report(results)
        print(report)
        if args.save:
            path = WIKI_DIR / "health-report.md"
            path.write_text(report, encoding="utf-8")
            print(f"\nSaved: {rel(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
