"""Provider-specific agent loops for the MCP eval harness.

The grading layer and the per-tool-call mechanics are provider-neutral; only
the model conversation loop differs between vendors. Each driver
(:class:`AnthropicDriver`, :class:`OpenAIDriver`) runs the agent loop for one
attempt and returns a :class:`DriverState` carrying the same fields every
provider reports. The shared per-tool-call mechanics live in
:func:`execute_tool_call` so that logic is written once.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from fastmcp import Client

_MAX_AGENT_TURNS = 16
# Anthropic SDK default is 2 retries; for a bursty parallel harness that
# isn't enough: the same rate-limit window persists across all retries.
# 8 retries with the SDK's exponential backoff + retry-after honouring
# gives ~5 minutes of grace, comfortably past the 1-minute reset.
_SDK_MAX_RETRIES = 8
# OpenAI's SDK defaults to 2 retries too; match the Anthropic path's grace
# so a bursty parallel harness rides out rate-limit windows the same way.
_OPENAI_MAX_RETRIES = 8
# Reasoning-effort levels the OpenAI Responses API accepts under
# ``reasoning.effort``. "none" (the harness default) sends no reasoning
# parameter, leaving the model on its own default.
_OPENAI_EFFORTS = frozenset({"minimal", "low", "medium", "high"})
_SYSTEM_PROMPT = (
    "You are an Apple Shortcuts author. Your only goal in this session is to "
    "produce one signed .shortcut file that satisfies the user's request, "
    "using the tools provided. "
    "Always start by inspecting the registry (shortcut_list_actions) and the "
    "action schemas (shortcut_get_action_schema) before constructing a spec. "
    "Use shortcut_validate_spec before shortcut_build so a bad spec costs "
    "nothing. Stop after a successful shortcut_build call, do not chat. "
    "If no available action can satisfy the request, briefly say so instead "
    "of building an incorrect shortcut, and do not invent action identifiers."
)


class TaskLike(Protocol):
    """The slice of a task a driver needs: the user prompt."""

    @property
    def prompt(self) -> str: ...


# ── Tool schema translation ──────────────────────────────────────────


async def _list_anthropic_tools(client: Client) -> list[dict[str, Any]]:
    """Translate the FastMCP server's tools/list into Anthropic's tool schema."""
    tools = await client.list_tools()
    out: list[dict[str, Any]] = [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema or {"type": "object", "properties": {}},
        }
        for t in tools
    ]
    # Cache the tools array so the ~2k-token JSON Schema isn't re-billed
    # every turn. The breakpoint goes on the LAST tool: it covers everything
    # up to and including that block. Cache write costs 1.25x input on the
    # first turn; hits on every subsequent turn cost 0.1x.
    if out:
        out[-1]["cache_control"] = {"type": "ephemeral"}
    return out


async def _list_openai_tools(client: Client) -> list[dict[str, Any]]:
    """Translate the FastMCP server's tools/list into OpenAI's tool schema.

    The Responses API uses a flat function-tool shape (``type``/``name``/
    ``description``/``parameters`` at the top level), unlike Chat Completions
    which nests them under a ``function`` key. OpenAI prompt caching is
    automatic, so there's no per-tool cache breakpoint to set.
    """
    tools = await client.list_tools()
    return [
        {
            "type": "function",
            "name": t.name,
            "description": t.description or "",
            "parameters": t.inputSchema or {"type": "object", "properties": {}},
        }
        for t in tools
    ]


def _tool_result_text(content: list[Any]) -> str:
    """Render an MCP tool result's content blocks as a single string."""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts) if parts else json.dumps(None)


# ── Shared per-tool-call mechanics ───────────────────────────────────


@dataclass
class DriverState:
    """Mutable accumulator shared by both provider drivers.

    Holds the cross-provider bookkeeping a tool call mutates (built_path,
    saw_recovery, tool_calls) plus per-turn token tallies, so the loop logic
    is written once and the result fields are identical across providers.
    """

    tool_calls: int = 0
    saw_recovery: bool = False
    built_path: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


async def execute_tool_call(
    mcp_client: Client,
    name: str,
    raw_args: dict[str, Any],
    output_dir: Path,
    state: DriverState,
) -> tuple[str, bool]:
    """Run one MCP tool call and update shared state. Returns ``(text, is_error)``.

    This is the single place the provider-neutral mechanics live: inject the
    per-attempt ``output_dir`` into ``shortcut_build`` (so concurrent attempts
    land in disjoint directories), extract ``built_path`` from the structured
    result, and flip ``saw_recovery`` on any error. Both drivers call it so the
    logic is never duplicated.
    """
    state.tool_calls += 1
    args = dict(raw_args)
    if name == "shortcut_build":
        args["output_dir"] = str(output_dir)
    try:
        call_result = await mcp_client.call_tool(name, args)
        text = _tool_result_text(call_result.content)
        is_error = bool(call_result.is_error)
        if name == "shortcut_build" and not is_error:
            sc = call_result.structured_content or {}
            path_val = sc.get("path")
            if isinstance(path_val, str):
                state.built_path = path_val
    except Exception as exc:
        text = f"tool {name} raised: {exc}"
        is_error = True
    if is_error:
        state.saw_recovery = True
    return text, is_error


def _parse_openai_args(arguments: str) -> dict[str, Any]:
    """Decode an OpenAI function call's JSON argument string to a dict.

    A malformed payload yields an empty dict; the tool then surfaces its own
    validation error, which the model can recover from.
    """
    try:
        parsed = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


# ── Provider drivers ─────────────────────────────────────────────────


class ModelDriver(Protocol):
    """A provider-specific agent loop.

    Given a task, an MCP client, and the per-attempt output directory, run the
    model's tool-use loop and return the same fields every provider reports.
    """

    async def run(
        self, task: TaskLike, mcp_client: Client, output_dir: Path
    ) -> DriverState: ...


class AnthropicDriver:
    """Anthropic Messages API agent loop with prompt caching intact."""

    def __init__(self, client: AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model

    async def run(
        self, task: TaskLike, mcp_client: Client, output_dir: Path
    ) -> DriverState:
        state = DriverState()
        tools = await _list_anthropic_tools(mcp_client)
        messages: list[dict[str, Any]] = [{"role": "user", "content": task.prompt}]

        for _ in range(_MAX_AGENT_TURNS):
            # Anthropic SDK types `tools` / `messages` as TypedDict unions; the
            # plain dicts we build are structurally identical but ty rejects
            # them. The dicts are right at runtime, so silence the false
            # positive rather than threading TypedDicts through every helper.
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=tools,  # ty: ignore[invalid-argument-type]
                messages=messages,  # ty: ignore[invalid-argument-type]
            )
            state.input_tokens += response.usage.input_tokens
            state.output_tokens += response.usage.output_tokens
            state.cache_read_tokens += response.usage.cache_read_input_tokens or 0
            state.cache_write_tokens += response.usage.cache_creation_input_tokens or 0

            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_results: list[dict[str, Any]] = []
            for use in tool_uses:
                text, is_error = await execute_tool_call(
                    mcp_client, use.name, dict(use.input or {}), output_dir, state
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.id,
                        "content": text,
                        "is_error": is_error,
                    }
                )
            messages.append({"role": "user", "content": tool_results})
        return state


class OpenAIDriver:
    """OpenAI Responses API agent loop.

    Uses ``client.responses.create`` with flat function tools. Function calls
    arrive as ``output`` items of type ``function_call``; outputs go back as
    ``function_call_output`` items appended to the running input list. Prompt
    caching is automatic and free, so ``cache_write_tokens`` stays zero and
    ``cache_read_tokens`` reads ``input_tokens_details.cached_tokens``.
    """

    def __init__(self, client: Any, model: str, reasoning_effort: str = "none") -> None:
        self._client = client
        self._model = model
        # "none" means do not send a reasoning parameter at all (the model
        # uses its own default); a real effort level is passed through as
        # ``reasoning.effort`` on every Responses call so the whole loop runs
        # at one effort.
        self._reasoning = (
            {"effort": reasoning_effort}
            if reasoning_effort in _OPENAI_EFFORTS
            else None
        )

    async def run(
        self, task: TaskLike, mcp_client: Client, output_dir: Path
    ) -> DriverState:
        state = DriverState()
        tools = await _list_openai_tools(mcp_client)
        extra: dict[str, Any] = (
            {"reasoning": self._reasoning} if self._reasoning else {}
        )
        # The first turn sends the user prompt; every later turn sends only the
        # new tool outputs and chains via ``previous_response_id``, so the
        # server holds conversation state. Round-tripping the model's own output
        # items by value does not work: the input schema rejects their
        # output-only fields (e.g. ``status``), and reasoning items carry extra
        # constraints. Chaining server-side sidesteps both.
        pending_input: list[dict[str, Any]] = [{"role": "user", "content": task.prompt}]
        previous_response_id: str | None = None

        for _ in range(_MAX_AGENT_TURNS):
            response = await self._client.responses.create(
                model=self._model,
                instructions=_SYSTEM_PROMPT,
                input=pending_input,
                tools=tools,
                previous_response_id=previous_response_id,
                **extra,
            )
            usage = response.usage
            if usage is not None:
                state.input_tokens += usage.input_tokens
                state.output_tokens += usage.output_tokens
                details = getattr(usage, "input_tokens_details", None)
                state.cache_read_tokens += getattr(details, "cached_tokens", 0) or 0

            previous_response_id = response.id
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break

            pending_input = []
            for call in calls:
                raw_args = _parse_openai_args(call.arguments)
                text, _is_error = await execute_tool_call(
                    mcp_client, call.name, raw_args, output_dir, state
                )
                pending_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": text,
                    }
                )
        return state


# ── Provider selection ───────────────────────────────────────────────


def provider_for(model: str) -> str:
    """Infer the provider from a model name.

    ``claude-*`` routes to Anthropic; ``gpt-*`` and o-series (``o1``, ``o3``,
    ``o4`` ...) route to OpenAI. Unknown names raise so a typo never silently
    bills the wrong vendor.
    """
    lower = model.lower()
    if lower.startswith("claude"):
        return "anthropic"
    if lower.startswith(("gpt", "o")):
        return "openai"
    raise SystemExit(
        f"Cannot infer provider for model {model!r}; pass --provider explicitly."
    )


class _NeverRaisedError(Exception):
    """Sentinel exception type that is never raised: an empty except clause."""


def provider_api_error() -> type[BaseException]:
    """Return OpenAI's base API error class, or a never-matching sentinel.

    The OpenAI loop can raise ``openai.APIError``; an Anthropic-only install
    won't have the package. Returning a sentinel keeps the except clause valid
    without importing openai eagerly.
    """
    try:
        from openai import APIError  # ty: ignore[unresolved-import]
    except ImportError:
        return _NeverRaisedError
    return APIError


def build_driver(
    provider: str, model: str, reasoning_effort: str = "none"
) -> ModelDriver:
    """Construct the driver for a provider, gating on the required API key.

    OpenAI is imported lazily so the harness still loads (and the Anthropic
    path and --dry-run still work) when the [evals] OpenAI extra is absent.
    ``reasoning_effort`` only affects the OpenAI driver; Anthropic ignores it
    (its equivalent, extended thinking, is not exercised by this harness).
    """
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit(
                "ANTHROPIC_API_KEY not set; pass --dry-run to validate tasks only."
            )
        return AnthropicDriver(AsyncAnthropic(max_retries=_SDK_MAX_RETRIES), model)
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise SystemExit(
                "OPENAI_API_KEY not set; pass --dry-run to validate tasks only."
            )
        try:
            from openai import AsyncOpenAI  # ty: ignore[unresolved-import]
        except ImportError as exc:
            raise SystemExit(
                "openai not installed; add it to the [evals] extra to run "
                "OpenAI models."
            ) from exc
        return OpenAIDriver(
            AsyncOpenAI(max_retries=_OPENAI_MAX_RETRIES), model, reasoning_effort
        )
    raise SystemExit(f"Unknown provider {provider!r}.")
