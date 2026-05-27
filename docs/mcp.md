# MCP server

`shortcut-lib` exposes its authoring surface as an
[MCP](https://modelcontextprotocol.io) server so any MCP host — Claude
Code, Claude Desktop, Cursor, ChatGPT (with the Apps SDK) — can build
Apple Shortcuts directly via tool calls.

The server is local-only (stdio transport), built on
[FastMCP 3.x](https://github.com/jlowin/fastmcp). The agent's surface is
five tools; the underlying registry, builder, and decoder are unchanged.

## Install

The MCP surface is an optional extra so the base library stays
dependency-free:

```sh
uv pip install -e '.[mcp]'
```

Two equivalent entrypoints are installed:

```sh
shortcut-mcp                 # console script
python -m shortcut_lib.mcp   # module entrypoint
```

## Wire into Claude Code

```sh
claude mcp add shortcut-lib -- shortcut-mcp
```

…or add manually to `~/.claude.json`:

```jsonc
{
  "mcpServers": {
    "shortcut-lib": {
      "command": "shortcut-mcp",
      "env": {
        "SHORTCUT_LIB_MCP_OUTPUT_DIR": "/Users/you/Downloads/shortcuts"
      }
    }
  }
}
```

Built files default to `~/Downloads`. Override with
`SHORTCUT_LIB_MCP_OUTPUT_DIR` (env) or the `output_dir` tool argument
(per-call).

## Inspector (recommended for first use)

```sh
npx @modelcontextprotocol/inspector shortcut-mcp
```

Opens at `http://localhost:6274`. Drive each tool from the form UI,
inspect JSON-RPC traffic, watch responses. Use it once before pointing a
real client at the server.

## The five tools

| Tool | What it does |
|------|--------------|
| `shortcut_list_actions(query?, limit, offset)` | Paginated discovery of registered actions. Returns `{actions, total_count, has_more, next_offset}`. |
| `shortcut_get_action_schema(name_or_identifier)` | Parameter signature + full docstring for one action. |
| `shortcut_validate_spec(spec)` | Dry-run a `ShortcutSpec` — compile only; no signing, no filesystem. Returns `{valid, error, action_count}`. |
| `shortcut_build(spec, output_dir?)` | Compile, sign via `shortcuts sign`, write. Returns `{path, name, action_count, identifier, size_bytes}`. |
| `shortcut_decode(path)` | Structural summary of an existing signed `.shortcut`. |

Errors from each tool are written as recovery prompts to the agent
("unknown action 'FrobnicateWidget' — call `shortcut_list_actions(query='frob')`"),
not as stack traces. Responses are minimised; no nested wire-format dumps.

## ShortcutSpec JSON

The authoring tool accepts a Pydantic-validated JSON document:

```json
{
  "name": "Voice Note To Clipboard",
  "surfaces": ["share"],
  "actions": [
    {"type": "DictateText", "ref": "spoken", "params": {}},
    {"type": "GetText", "ref": "msg",
     "params": {"text": "Note: ${spoken}"}},
    {"type": "SetClipboard", "params": {"input": "${msg}"}}
  ]
}
```

Rules:

- `type` is either the action's Python class name (`"DictateText"`) or
  the full Apple identifier (`"is.workflow.actions.dictate.text"`).
- `ref` is an optional alias for an action's output. Must be a valid
  Python identifier and unique within the spec.
- `"${ref}"` in any string parameter resolves to a variable reference.
  - Pure `"${ref}"` (whole string) → single-attachment
    `WFTextTokenAttachment` envelope.
  - Interleaved `"hello ${ref}!"` → templated
    `WFTextTokenString` envelope (the placeholder lands at the correct
    UTF-16 offset).
- `surfaces` accepts `"watch"`, `"widget"`, `"share"`, `"menubar"`,
  `"quick-action"`, `"sleep"` — or raw Apple strings (`"ActionExtension"`
  etc.).

## Suggested agent workflow

1. `shortcut_list_actions(query=...)` to discover candidates.
2. `shortcut_get_action_schema(...)` for any action you'll instantiate —
   read the docstring; parameter provenance (corpus / jellycore /
   inferred) is documented inline.
3. Draft the spec, then `shortcut_validate_spec(spec)`.
4. Iterate on validation errors (each one names the next tool to call).
5. `shortcut_build(spec)` to land the signed file.
6. `shortcut_decode(path)` if you need to confirm what got built.

The same flow underpins the eval harness in `evals/mcp/`.

## Testing

Unit tests use FastMCP's in-memory `Client` — no subprocess, no
transport, full coverage of the JSON-RPC surface:

```sh
uv run pytest tests/test_mcp_server.py
```

19 tests covering: handshake, every tool happy path, unknown-action /
dangling-ref / unsafe-filename error paths, and a full build → decode
round-trip.

## Eval harness

Tool-level tests show each tool works in isolation. The eval harness
under `evals/mcp/` measures what an agent can actually *achieve* with
them — 12 tasks (clipboard, dictation, base64, ask-and-echo, math,
choose-from-list, share-sheet, statistics, plus an explicit
recovery-from-error task), graded deterministically by decoding the
emitted `.shortcut` file.

```sh
export ANTHROPIC_API_KEY=...
uv run python evals/mcp/run_evals.py --dry-run  # validate tasks; no API
uv run python evals/mcp/run_evals.py            # pass@1
uv run python evals/mcp/run_evals.py --k 3      # pass@3 (consistency)
```

Each run reports pass@k, total tool calls, and token usage. Results land
in `evals/mcp/results/<timestamp>.json` (gitignored).

The harness hosts the FastMCP server in-process and routes Anthropic
`tool_use` blocks straight into `fastmcp.Client.call_tool` — the same
code path as the stdio entrypoint, no transport noise to debug.

## What's not here

By design, this server is local-only stdio with no auth. The following
are deliberately out of scope until there's a real reason to ship them:

- Streamable HTTP transport / remote multi-tenant operation.
- OAuth 2.1 / token-scoped tools.
- ChatGPT Apps `search` / `fetch` tool conventions.
- The code-execution / filesystem-module-tree pattern from
  Anthropic's [token-efficiency post](https://www.anthropic.com/engineering/code-execution-with-mcp)
  — useful at >10 tools with large outputs; this server has five tools
  with tight responses.

If a future use case needs any of these, add them — don't pre-build.

## Source-confidence ladder

The library's wire-format research follows a discipline (corpus >
jellycore > UI > inference). Action docstrings — surfaced verbatim by
`shortcut_get_action_schema` — label each parameter's rung. Trust those
labels over your prior; corpus is authoritative for wire spelling, and
the same field can take different envelopes depending on slot semantics.
See `CLAUDE.md` and `.claude/rules/action-modelling.md` for the full
rules if you're adding new actions.
