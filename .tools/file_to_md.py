#!/usr/bin/env python3
"""Convert source files to markdown for xWiki ingest.

Markdown and plain-text files are copied into markdown form directly. Rich
formats use Microsoft's optional markitdown package when it is installed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "_inbox" / "converted"
TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".rst"}


def slug_output_name(path: Path) -> str:
    return f"{path.stem}.md"


def convert_text_file(source: Path, target: Path) -> None:
    content = source.read_text(encoding="utf-8", errors="replace")
    if source.suffix.lower() in {".md", ".markdown"}:
        target.write_text(content, encoding="utf-8")
        return
    target.write_text(
        f"# {source.stem}\n\nSource file: `{source.as_posix()}`\n\n```text\n{content}\n```\n",
        encoding="utf-8",
    )


def convert_with_markitdown(source: Path, target: Path) -> None:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "markitdown is required for this file type. Install it with: "
            "python3 -m pip install markitdown"
        ) from exc

    converter = MarkItDown()
    result = converter.convert(str(source))
    target.write_text(result.text_content, encoding="utf-8")


def iter_inputs(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(path)
    return files


def convert_file(source: Path, output_dir: Path, overwrite: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / slug_output_name(source)
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists; pass --overwrite to replace it")

    suffix = source.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        convert_text_file(source, target)
    else:
        convert_with_markitdown(source, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert source files to markdown for xWiki ingest.")
    parser.add_argument("paths", nargs="+", help="Files or directories to convert.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for converted markdown files. Defaults to _inbox/converted.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing converted markdown files.")
    args = parser.parse_args()

    sources = iter_inputs([Path(p).expanduser().resolve() for p in args.paths])
    output_dir = Path(args.output_dir).expanduser().resolve()

    failures = 0
    for source in sources:
        try:
            target = convert_file(source, output_dir, args.overwrite)
            print(f"Converted: {source} -> {target}")
        except Exception as exc:  # noqa: BLE001 - command-line tool should continue through batch failures.
            failures += 1
            print(f"Failed: {source}: {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
