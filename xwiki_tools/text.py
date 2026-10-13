"""Deterministic search normalization for English and CJK text."""

from __future__ import annotations

import re
import unicodedata

MAX_QUERY_CHARS = 500


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def is_han(character: str) -> bool:
    return unicodedata.name(character, "").startswith(
        ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH")
    )


def script_runs(value: str) -> list[tuple[bool, str]]:
    """Split normalized letters and numbers at Han/non-Han boundaries."""

    result: list[tuple[bool, str]] = []
    current: list[str] = []
    current_han: bool | None = None
    for character in normalize(value):
        if unicodedata.category(character)[0] not in "LNM":
            if current:
                result.append((bool(current_han), "".join(current)))
                current = []
                current_han = None
            continue
        character_han = is_han(character)
        if current and character_han != current_han:
            result.append((bool(current_han), "".join(current)))
            current = []
        current_han = character_han
        current.append(character)
    if current:
        result.append((bool(current_han), "".join(current)))
    return result


def _encoded(prefix: str, value: str) -> str:
    return prefix + value.encode("utf-8").hex()


def search_tokens(value: str) -> list[str]:
    """Create safe FTS tokens with CJK unigram and contiguous bigram fallback."""

    tokens: list[str] = []
    for han, run in script_runs(value):
        if not han:
            tokens.append(run)
            continue
        tokens.extend(_encoded("xu", character) for character in run)
        tokens.extend(
            _encoded("xg", run[index : index + 2]) for index in range(len(run) - 1)
        )
    return list(dict.fromkeys(tokens))


def token_text(value: str) -> str:
    return " ".join(search_tokens(value))


def _quoted(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def match_expression(query: str) -> str:
    """Build an operator-free FTS5 expression from untrusted query text."""

    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"Search queries are limited to {MAX_QUERY_CHARS} characters.")
    clauses: list[str] = []
    for han, run in script_runs(query):
        if not han:
            clauses.append(_quoted(run))
            continue
        terms = (
            [_encoded("xu", run)]
            if len(run) == 1
            else [
                _encoded("xg", run[index : index + 2]) for index in range(len(run) - 1)
            ]
        )
        clauses.append("(" + " AND ".join(_quoted(term) for term in terms) + ")")
    if not clauses:
        raise ValueError("Provide at least one searchable letter or number.")
    return " AND ".join(dict.fromkeys(clauses))


def slug(value: str, *, fallback: str = "page", limit: int = 80) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", normalize(value)).strip("-")
    return (result or fallback)[:limit].rstrip("-")
