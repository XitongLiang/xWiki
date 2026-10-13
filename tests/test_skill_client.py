"""Tests for the portable xWiki knowledge MCP skill client."""

import importlib.util
import io
import json
import logging
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "xwiki-knowledge-mcp"
    / "scripts"
    / "knowledge_mcp.py"
)
SPEC = importlib.util.spec_from_file_location("xwiki_knowledge_mcp_client", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the xWiki knowledge MCP client.")
knowledge_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(knowledge_mcp)


class ClientInputTests(unittest.TestCase):
    def run_main(self, args, content=b""):
        output, errors = io.StringIO(), io.StringIO()
        stdin = SimpleNamespace(buffer=io.BytesIO(content))
        with (
            patch.object(sys, "stdin", stdin),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            code = knowledge_mcp.main(args)
        return code, json.loads(output.getvalue()), errors.getvalue()

    def test_invalid_input_never_contacts_server(self):
        base = ["--url", "http://127.0.0.1:8765/mcp"]
        cases = [
            (["--url", "https://private:secret@example.test/mcp", "--list-tools"], b""),
            (["--url", "file:///private", "--list-tools"], b""),
            (["--url", "https://example.test/mcp?token=secret", "--list-tools"], b""),
            (base + ["--list-tools", "--timeout", "nan"], b""),
            (base + ["--request", "-"], b'{"requests": []}'),
            (base + ["--request", "-"], b'{"requests": [{}], "secret": "private"}'),
            (base + ["--request", "-"], b"private invalid JSON"),
            (
                base + ["--request", "-"],
                b" " * (knowledge_mcp.MAX_REQUEST_BYTES + 1),
            ),
        ]
        with patch.object(knowledge_mcp, "invoke", new_callable=AsyncMock) as invoke:
            for args, content in cases:
                with self.subTest(args=args, content_length=len(content)):
                    code, output, errors = self.run_main(args, content)
                    self.assertEqual(code, 2)
                    self.assertEqual(output["error"]["code"], "invalid_client_request")
                    self.assertNotIn("secret", json.dumps(output))
                    self.assertNotIn("private", json.dumps(output))
                    self.assertEqual(errors, "")
            invoke.assert_not_awaited()

    def test_transport_errors_are_bounded_and_logging_is_restored(self):
        async def fail(*args, **kwargs):
            logging.getLogger("mcp.client.streamable_http").error(
                "private transport response"
            )
            raise RuntimeError("private credentials")

        before = logging.root.manager.disable
        with patch.object(knowledge_mcp, "invoke", side_effect=fail):
            code, output, errors = self.run_main(
                ["--url", "http://localhost:8765/mcp", "--list-tools"]
            )
        self.assertEqual(code, 2)
        self.assertEqual(output["error"]["code"], "mcp_unavailable")
        self.assertNotIn("private", json.dumps(output) + errors)
        self.assertEqual(logging.root.manager.disable, before)


class ProtocolResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_partial_failure_is_preserved(self):
        payload = {"requests": [{"action": "browse"}]}
        evidence = {
            "total": 2,
            "succeeded": 1,
            "failed": 1,
            "results": [{"ok": True}, {"ok": False}],
        }
        reply = SimpleNamespace(
            structured_content=evidence,
            is_error=False,
            content=[SimpleNamespace(type="text", text='{"failed": 0}')],
        )
        client = AsyncMock()
        client.list_tools.return_value = SimpleNamespace(
            tools=[SimpleNamespace(name="knowledge")]
        )
        client.call_tool.return_value = reply
        with patch.object(knowledge_mcp, "Client") as factory:
            factory.return_value.__aenter__.return_value = client
            output, code = await knowledge_mcp.invoke("http://localhost/mcp", payload)
        self.assertEqual(code, 1)
        self.assertEqual(output, {"isError": False, "structuredContent": evidence})
        client.call_tool.assert_awaited_once_with("knowledge", payload)

    async def test_text_fallback_and_missing_tool_are_handled(self):
        evidence = {
            "total": 1,
            "succeeded": 0,
            "failed": 1,
            "results": [{"ok": False}],
        }
        client = AsyncMock()
        client.list_tools.return_value = SimpleNamespace(
            tools=[SimpleNamespace(name="knowledge")]
        )
        client.call_tool.return_value = SimpleNamespace(
            structured_content=None,
            is_error=True,
            content=[
                SimpleNamespace(type="text", text="not JSON"),
                SimpleNamespace(type="text", text=json.dumps(evidence)),
            ],
        )
        with patch.object(knowledge_mcp, "Client") as factory:
            factory.return_value.__aenter__.return_value = client
            output, code = await knowledge_mcp.invoke(
                "http://localhost/mcp", {"requests": [{"action": "browse"}]}
            )
        self.assertEqual((code, output["isError"]), (1, True))
        self.assertEqual(output["structuredContent"], evidence)

        missing = AsyncMock()
        missing.list_tools.return_value = SimpleNamespace(
            tools=[SimpleNamespace(name="unrelated")]
        )
        with patch.object(knowledge_mcp, "Client") as factory:
            factory.return_value.__aenter__.return_value = missing
            with self.assertRaises(knowledge_mcp.ClientInputError):
                await knowledge_mcp.invoke(
                    "http://localhost/mcp",
                    {"requests": [{"action": "browse"}]},
                )
        missing.call_tool.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
