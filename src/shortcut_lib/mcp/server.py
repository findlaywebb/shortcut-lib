"""FastMCP server exposing shortcut-lib as five MCP tools.

The agent's workflow is roughly:

1. ``shortcut_list_actions`` — discover what's available (paginated).
2. ``shortcut_get_action_schema`` — inspect one action's parameters.
3. ``shortcut_validate_spec`` — dry-run a draft spec; iterate until ``valid``.
4. ``shortcut_build`` — compile, sign, and write the ``.shortcut`` file.
5. ``shortcut_decode`` — read an existing ``.shortcut`` and summarise it.

Tool docstrings are written as instructions to the LLM: when to use, what
shape the input takes, what comes back. Errors are recovery prompts, never
tracebacks; outputs are minimised — no nested data dumps.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

import shortcut_lib.schema  # noqa: F401 — populate action registry
from shortcut_lib.decode import DecodeError, decode_file
from shortcut_lib.mcp.build import SpecCompileError, build_shortcut, compile_spec
from shortcut_lib.mcp.spec import ShortcutSpec
from shortcut_lib.schema.registry import describe_action, list_actions

_DEFAULT_OUTPUT_DIR_ENV = "SHORTCUT_LIB_MCP_OUTPUT_DIR"
_FALLBACK_OUTPUT_DIR = Path.home() / "Downloads"


def _resolve_output_dir(arg: str | None) -> Path:
    """Pick the output directory: explicit arg → env var → ``~/Downloads``."""
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get(_DEFAULT_OUTPUT_DIR_ENV)
    if env:
        return Path(env).expanduser().resolve()
    return _FALLBACK_OUTPUT_DIR


def build_server() -> FastMCP:
    """Construct and return the FastMCP server (uninitialised).

    Kept as a factory so tests can spin up a fresh server per case and
    drive it through an in-memory ``fastmcp.Client``.
    """
    mcp: FastMCP = FastMCP(
        name="shortcut-lib",
        instructions=(
            "Author Apple Shortcuts from a JSON spec. Workflow: "
            "shortcut_list_actions to discover, shortcut_get_action_schema "
            "to inspect one, shortcut_validate_spec to dry-run, "
            "shortcut_build to write the signed .shortcut file. "
            "Use shortcut_decode to inspect an existing .shortcut."
        ),
    )

    @mcp.tool
    def shortcut_list_actions(
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Substring filter (case-insensitive) matched against "
                    "the action's class name, identifier, and one-line "
                    "summary. Omit to list everything."
                ),
                max_length=120,
            ),
        ] = None,
        limit: Annotated[int, Field(ge=1, le=200)] = 50,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List registered shortcut actions with one-line summaries.

        Start here when authoring: skim the catalogue to find the right
        action class for what the user wants. Use ``query`` to narrow the
        list (e.g. ``"clipboard"``, ``"notification"``, ``"date"``). The
        result paginates with ``limit`` / ``offset`` and reports
        ``total_count`` plus ``has_more``.

        Returns:
            ``{actions: [{name, identifier, doc}], total_count, has_more,
            next_offset}``. ``name`` is the Python class (use it as the
            ``type`` field in a ShortcutSpec); ``identifier`` is the
            Apple-side string. Either works as ``type``.
        """
        rows = list_actions()
        if query:
            q = query.lower()
            rows = [
                r
                for r in rows
                if q in r["name"].lower()
                or q in r["identifier"].lower()
                or q in r["doc"].lower()
            ]
        total = len(rows)
        page = rows[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "actions": page,
            "total_count": total,
            "has_more": next_offset < total,
            "next_offset": next_offset if next_offset < total else None,
        }

    @mcp.tool
    def shortcut_get_action_schema(
        name_or_identifier: Annotated[
            str,
            Field(
                description=(
                    "Action class name (e.g. 'DictateText') or full Apple "
                    "identifier (e.g. 'is.workflow.actions.dictate.text')."
                ),
                min_length=1,
                max_length=120,
            ),
        ],
    ) -> dict[str, Any]:
        """Return the parameter signature and docstring for one action.

        Call this whenever you're about to write an ActionSpec and need to
        know the exact field names and types. The ``doc`` field is the
        action's full Google-style docstring — read it: each parameter is
        documented with source-confidence labels (corpus-confirmed vs
        jellycore-listed vs UI-inferred) you should respect.

        Returns:
            ``{name, identifier, doc, default_output_name, parameters:
            [{name, type, has_default}]}``. ``type`` is a readable string
            like ``"str | None"``; ``has_default`` means the field is
            optional in the dataclass __init__.
        """
        try:
            return describe_action(name_or_identifier)
        except KeyError:
            raise ValueError(
                f"Unknown action {name_or_identifier!r}. "
                f"Call shortcut_list_actions(query={name_or_identifier[:16]!r}) "
                f"to find candidates."
            ) from None

    @mcp.tool
    def shortcut_validate_spec(
        spec: ShortcutSpec,
    ) -> dict[str, Any]:
        """Dry-run a shortcut spec — compile only, do not sign or write.

        Use this iteratively while drafting: catches unknown action types,
        bad parameter names, dangling ``${ref}`` references, and invalid
        Pydantic shapes without touching the filesystem or invoking
        ``shortcuts sign``. When ``valid: true``, the spec is ready to
        hand to ``shortcut_build``.

        Returns:
            ``{valid: bool, error: str | None, action_count: int | None}``.
            On failure ``error`` is an agent-recoverable message naming
            the offending action and the next tool to call.
        """
        try:
            shortcut = compile_spec(spec)
        except SpecCompileError as exc:
            return {"valid": False, "error": str(exc), "action_count": None}
        return {
            "valid": True,
            "error": None,
            "action_count": len(shortcut.actions),
        }

    @mcp.tool
    def shortcut_build(
        spec: ShortcutSpec,
        output_dir: Annotated[
            str | None,
            Field(
                description=(
                    "Absolute path of the directory to write the .shortcut "
                    "file into. Created if missing. Defaults to "
                    "$SHORTCUT_LIB_MCP_OUTPUT_DIR, then to ~/Downloads."
                ),
                max_length=4096,
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Compile, sign, and write a shortcut spec to disk.

        Wraps ``shortcuts sign`` (the macOS CLI). The user can then
        double-click or drag the resulting file into Shortcuts.app.

        Returns:
            ``{path, name, action_count, identifier, size_bytes}``.
            ``identifier`` is the workflow's stable UUID (derived from
            ``name``), useful for cross-shortcut references via
            RunWorkflow. The signed file is the deliverable; surface the
            ``path`` to the user.

        Errors:
            On a spec problem, raises with an agent-recoverable message
            (which validation tool to call, what to inspect). On signing
            failure the underlying ``shortcuts`` CLI message is surfaced.
        """
        target = _resolve_output_dir(output_dir)
        try:
            return build_shortcut(spec, target)
        except SpecCompileError as exc:
            raise ValueError(str(exc)) from exc

    @mcp.tool
    def shortcut_decode(
        path: Annotated[
            str,
            Field(
                description="Absolute path to a signed .shortcut file.",
                min_length=1,
                max_length=4096,
            ),
        ],
    ) -> dict[str, Any]:
        """Read an existing .shortcut file and return a structural summary.

        Useful for inspecting an existing shortcut before editing, or for
        confirming what ``shortcut_build`` just produced. Returns the
        action list with identifiers and a few headline fields — not the
        full parameter blobs (those bloat context for no benefit; if you
        need the raw workflow dict, use the library directly).

        Returns:
            ``{name, signing_subject, action_count, surfaces,
            actions: [{index, identifier, output_uuid}]}``.
        """
        target = Path(path).expanduser()
        if not target.exists():
            raise ValueError(
                f"No file at {target}. Pass the absolute path returned "
                f"by shortcut_build, or a .shortcut file on disk."
            )
        try:
            decoded = decode_file(target)
        except DecodeError as exc:
            raise ValueError(
                f"Could not decode {target.name}: {exc}. "
                f"Confirm the file is a signed Apple Shortcuts archive."
            ) from exc

        workflow = decoded.workflow
        actions = workflow.get("WFWorkflowActions") or []
        action_summaries: list[dict[str, Any]] = []
        for i, action in enumerate(actions):
            params = action.get("WFWorkflowActionParameters") or {}
            action_summaries.append(
                {
                    "index": i,
                    "identifier": action.get("WFWorkflowActionIdentifier", ""),
                    "output_uuid": params.get("UUID", ""),
                }
            )
        return {
            "name": target.stem,
            "signing_subject": decoded.signing_subject,
            "action_count": len(actions),
            "surfaces": list(workflow.get("WFWorkflowTypes") or []),
            "actions": action_summaries,
        }

    return mcp
