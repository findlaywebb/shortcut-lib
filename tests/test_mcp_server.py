"""Tests for the FastMCP server.

Drives the server through an in-memory ``fastmcp.Client`` — no subprocess,
no transport, so each test is a few ms. Covers the JSON-RPC surface
(``tools/list``, ``tools/call``), the spec compiler, and a full
build → decode round-trip.

The ``[mcp]`` extra is optional; tests are skipped cleanly when fastmcp
isn't installed so the base library's CI doesn't need it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastmcp", reason="optional [mcp] extra not installed")

from fastmcp import Client

from shortcut_lib.mcp.build import SpecCompileError, compile_spec
from shortcut_lib.mcp.server import build_server
from shortcut_lib.mcp.spec import ShortcutSpec, pure_ref

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def client() -> Client:
    """Fresh in-memory client per test — no shared server state."""
    return Client(build_server())


def _structured(result: Any) -> dict[str, Any]:
    """Extract structured content from a CallToolResult, asserting it's there."""
    assert result.structured_content is not None, (
        "expected structured_content; FastMCP returns it for any tool with a "
        "non-trivial return type"
    )
    return result.structured_content


# ── Lifecycle / handshake ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_server_lists_five_tools(client: Client) -> None:
    async with client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "shortcut_list_actions",
        "shortcut_get_action_schema",
        "shortcut_validate_spec",
        "shortcut_build",
        "shortcut_decode",
    }


# ── shortcut_list_actions ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_actions_unfiltered_paginates(client: Client) -> None:
    async with client:
        result = await client.call_tool(
            "shortcut_list_actions", {"limit": 10, "offset": 0}
        )
    payload = _structured(result)
    assert len(payload["actions"]) == 10
    assert payload["total_count"] >= 50
    assert payload["has_more"] is True
    assert payload["next_offset"] == 10


@pytest.mark.asyncio
async def test_list_actions_query_filters(client: Client) -> None:
    async with client:
        result = await client.call_tool("shortcut_list_actions", {"query": "clipboard"})
    payload = _structured(result)
    names = [a["name"] for a in payload["actions"]]
    assert "GetClipboard" in names
    assert "SetClipboard" in names
    assert payload["has_more"] is False


# ── shortcut_get_action_schema ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_action_schema_by_class_name(client: Client) -> None:
    async with client:
        result = await client.call_tool(
            "shortcut_get_action_schema", {"name_or_identifier": "GetText"}
        )
    payload = _structured(result)
    assert payload["name"] == "GetText"
    assert payload["identifier"] == "is.workflow.actions.gettext"
    param_names = {p["name"] for p in payload["parameters"]}
    assert "text" in param_names


@pytest.mark.asyncio
async def test_get_action_schema_by_identifier(client: Client) -> None:
    async with client:
        result = await client.call_tool(
            "shortcut_get_action_schema",
            {"name_or_identifier": "is.workflow.actions.setclipboard"},
        )
    payload = _structured(result)
    assert payload["name"] == "SetClipboard"


@pytest.mark.asyncio
async def test_get_action_schema_unknown_action_returns_recovery_prompt(
    client: Client,
) -> None:
    """Unknown action raises an error whose message names the next tool to call."""
    async with client:
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "shortcut_get_action_schema",
                {"name_or_identifier": "FrobnicateWidget"},
            )
    msg = str(exc_info.value)
    assert "FrobnicateWidget" in msg
    assert "shortcut_list_actions" in msg, (
        "error must point the agent at the discovery tool"
    )


# ── shortcut_validate_spec ───────────────────────────────────────────


def _minimal_spec(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "Test",
        "actions": [
            {"type": "GetText", "ref": "g", "params": {"text": "Hello"}},
            {"type": "SetClipboard", "params": {"input": "${g}"}},
        ],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_validate_happy_path(client: Client) -> None:
    async with client:
        result = await client.call_tool(
            "shortcut_validate_spec", {"spec": _minimal_spec()}
        )
    payload = _structured(result)
    assert payload == {"valid": True, "error": None, "action_count": 2}


@pytest.mark.asyncio
async def test_validate_unknown_action_returns_error(client: Client) -> None:
    spec = _minimal_spec(actions=[{"type": "FrobnicateWidget", "params": {}}])
    async with client:
        result = await client.call_tool("shortcut_validate_spec", {"spec": spec})
    payload = _structured(result)
    assert payload["valid"] is False
    assert "FrobnicateWidget" in payload["error"]
    assert "shortcut_list_actions" in payload["error"]


@pytest.mark.asyncio
async def test_validate_dangling_ref_returns_error(client: Client) -> None:
    spec = _minimal_spec(
        actions=[{"type": "SetClipboard", "params": {"input": "${ghost}"}}]
    )
    async with client:
        result = await client.call_tool("shortcut_validate_spec", {"spec": spec})
    payload = _structured(result)
    assert payload["valid"] is False
    assert "ghost" in payload["error"]


# ── shortcut_build + shortcut_decode (round-trip) ────────────────────


@pytest.mark.asyncio
async def test_build_and_decode_round_trip(client: Client, tmp_path: Path) -> None:
    spec = {
        "name": "Round Trip",
        "surfaces": ["share"],
        "actions": [
            {"type": "GetText", "ref": "g", "params": {"text": "Hi"}},
            {"type": "SetClipboard", "params": {"input": "${g}"}},
            {
                "type": "ShowNotification",
                "params": {"title": "Done", "body": "Copied: ${g}"},
            },
        ],
    }
    async with client:
        built = _structured(
            await client.call_tool(
                "shortcut_build",
                {"spec": spec, "output_dir": str(tmp_path)},
            )
        )
        assert built["action_count"] == 3
        assert built["name"] == "Round Trip"
        path = Path(built["path"])
        assert path.exists()
        assert path.suffix == ".shortcut"
        assert built["size_bytes"] > 0

        decoded = _structured(
            await client.call_tool("shortcut_decode", {"path": built["path"]})
        )
        identifiers = [a["identifier"] for a in decoded["actions"]]
        assert identifiers == [
            "is.workflow.actions.gettext",
            "is.workflow.actions.setclipboard",
            "is.workflow.actions.notification",
        ]
        assert decoded["surfaces"] == ["ActionExtension"]  # "share" surface


@pytest.mark.asyncio
async def test_build_unsafe_name_is_sanitised(client: Client, tmp_path: Path) -> None:
    """A name with path-traversal chars produces a safe filename, never escapes."""
    spec = {
        "name": "../../etc/passwd",
        "actions": [{"type": "GetText", "params": {"text": "x"}}],
    }
    async with client:
        built = _structured(
            await client.call_tool(
                "shortcut_build", {"spec": spec, "output_dir": str(tmp_path)}
            )
        )
    path = Path(built["path"])
    assert path.parent == tmp_path.resolve()
    assert path.name.endswith(".shortcut")
    assert ".." not in path.name


@pytest.mark.asyncio
async def test_decode_missing_path_returns_recovery_prompt(client: Client) -> None:
    async with client:
        with pytest.raises(Exception) as exc_info:
            await client.call_tool(
                "shortcut_decode", {"path": "/no/such/file.shortcut"}
            )
    msg = str(exc_info.value)
    assert "No file" in msg or "no such" in msg.lower()


# ── Spec model + compiler unit tests ─────────────────────────────────


def test_pure_ref_detects_exact_match() -> None:
    assert pure_ref("${g}") == "g"
    assert pure_ref("  ${greeting}  ") == "greeting"
    assert pure_ref("Hi ${g}") is None
    assert pure_ref("${a} ${b}") is None
    assert pure_ref("no refs here") is None


def test_compile_pure_ref_resolves_to_action_handle() -> None:
    """A pure ${ref} string in a string param becomes a single-attachment ref."""
    spec = ShortcutSpec.model_validate(
        {
            "name": "t",
            "actions": [
                {"type": "GetText", "ref": "g", "params": {"text": "Hi"}},
                {"type": "SetClipboard", "params": {"input": "${g}"}},
            ],
        }
    )
    shortcut = compile_spec(spec)
    wf = shortcut.to_workflow()
    clip = wf["WFWorkflowActions"][1]["WFWorkflowActionParameters"]["WFInput"]
    assert clip["WFSerializationType"] == "WFTextTokenAttachment"
    assert clip["Value"]["Type"] == "ActionOutput"


def test_compile_interleaved_ref_becomes_text_token_string() -> None:
    spec = ShortcutSpec.model_validate(
        {
            "name": "t",
            "actions": [
                {"type": "GetText", "ref": "name", "params": {"text": "Alex"}},
                {
                    "type": "ShowNotification",
                    "params": {"title": "Hi", "body": "Hello, ${name}!"},
                },
            ],
        }
    )
    shortcut = compile_spec(spec)
    wf = shortcut.to_workflow()
    body = wf["WFWorkflowActions"][1]["WFWorkflowActionParameters"][
        "WFNotificationActionBody"
    ]
    assert body["WFSerializationType"] == "WFTextTokenString"
    # "Hello, " is 7 UTF-16 code units; the attachment lives at offset 7.
    assert "{7, 1}" in body["Value"]["attachmentsByRange"]


def test_compile_duplicate_ref_raises() -> None:
    spec = ShortcutSpec.model_validate(
        {
            "name": "t",
            "actions": [
                {"type": "GetText", "ref": "x", "params": {"text": "a"}},
                {"type": "GetText", "ref": "x", "params": {"text": "b"}},
            ],
        }
    )
    with pytest.raises(SpecCompileError, match="duplicate ref"):
        compile_spec(spec)


def test_spec_rejects_invalid_ref_identifier() -> None:
    """Pydantic catches refs that aren't valid identifiers up-front."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ShortcutSpec.model_validate(
            {
                "name": "t",
                "actions": [
                    {"type": "GetText", "ref": "1bad", "params": {"text": "a"}}
                ],
            }
        )


def test_spec_rejects_unknown_top_level_field() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        ShortcutSpec.model_validate(
            {
                "name": "t",
                "actions": [{"type": "GetText", "params": {"text": "a"}}],
                "bogus": True,
            }
        )


def test_spec_serialisation_round_trips() -> None:
    """Spec ↔ JSON round-trip preserves every field — useful for eval task storage."""
    spec = ShortcutSpec.model_validate(_minimal_spec())
    raw = json.loads(spec.model_dump_json())
    again = ShortcutSpec.model_validate(raw)
    assert again == spec
