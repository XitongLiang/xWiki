#!/usr/bin/env python3
"""Discover and call an xWiki knowledge server over Streamable HTTP MCP."""

import argparse
import asyncio
import json
import logging
import math
import sys
from pathlib import Path
from urllib.parse import urlsplit

from mcp import Client

MAX_REQUEST_BYTES = 64 * 1024


class ClientInputError(ValueError):
    """A bounded CLI error that does not expose request or transport details."""


def validate_endpoint(url):
    try:
        parsed = urlsplit(url)
        valid = (
            parsed.scheme in ("http", "https")
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and not any(character.isspace() for character in url)
        )
        _ = parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ClientInputError(
            "Use an HTTP(S) MCP endpoint without credentials, query, or fragment."
        )


def load_request(path):
    try:
        if path == "-":
            content = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        else:
            with Path(path).open("rb") as handle:
                content = handle.read(MAX_REQUEST_BYTES + 1)
        if len(content) > MAX_REQUEST_BYTES:
            raise ClientInputError("The request must not exceed 64 KiB.")
        value = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ClientInputError(
            "Provide a readable UTF-8 JSON request file or use - for stdin."
        ) from None
    if (
        not isinstance(value, dict)
        or set(value) != {"requests"}
        or not isinstance(value["requests"], list)
        or not 1 <= len(value["requests"]) <= 10
    ):
        raise ClientInputError(
            "Provide one requests list containing one to ten independent actions."
        )
    return value


async def invoke(url, payload=None, *, timeout=30):
    """Return discovery or one tool result while preserving partial batches."""

    async with (
        asyncio.timeout(timeout),
        Client(url, read_timeout_seconds=timeout) as client,
    ):
        tools = (await client.list_tools()).tools
        tool = next(
            (candidate for candidate in tools if candidate.name == "knowledge"), None
        )
        if tool is None:
            raise ClientInputError(
                "The connected MCP server does not advertise knowledge."
            )
        if payload is None:
            return {
                "tools": [
                    tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                ]
            }, 0
        reply = await client.call_tool("knowledge", payload)
        value = reply.structured_content
        if value is None:
            for block in reply.content:
                if block.type != "text":
                    continue
                try:
                    value = json.loads(block.text)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    break
        if not isinstance(value, dict):
            raise ClientInputError(
                "The knowledge tool did not return a JSON result object."
            )
        output = {"isError": bool(reply.is_error), "structuredContent": value}
        return output, 1 if reply.is_error or value.get("failed", 0) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", required=True, help="Explicit Streamable HTTP MCP endpoint."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Overall timeout in seconds (default 30).",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--list-tools",
        action="store_true",
        help="Discover knowledge and its live input schema.",
    )
    action.add_argument(
        "--request",
        metavar="FILE",
        help="Read a knowledge batch from a UTF-8 JSON file or - for stdin.",
    )
    args = parser.parse_args(argv)

    # SDK transport logs can include raw response details; emit only bounded errors.
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        validate_endpoint(args.url)
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ClientInputError(
                "Timeout must be a finite positive number of seconds."
            )
        payload = load_request(args.request) if args.request is not None else None
        output, code = asyncio.run(invoke(args.url, payload, timeout=args.timeout))
    except ClientInputError as error:
        output, code = (
            {"error": {"code": "invalid_client_request", "detail": str(error)}},
            2,
        )
    except TimeoutError:
        output, code = (
            {
                "error": {
                    "code": "client_timeout",
                    "detail": "The MCP request timed out.",
                }
            },
            2,
        )
    except Exception:  # noqa: BLE001 - keep transport diagnostics out of CLI output.
        output, code = (
            {
                "error": {
                    "code": "mcp_unavailable",
                    "detail": "The MCP connection or request could not complete.",
                }
            },
            2,
        )
    finally:
        logging.disable(previous_logging)
    print(json.dumps(output, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
