# MCP server eval harness

A small task-based eval harness that drives Claude through the
`shortcut-lib` MCP server and grades end-to-end task completion.

This is the agent-level half of the testing pyramid. Tool-level tests
(`tests/test_mcp_server.py`) cover JSON-RPC conformance and per-tool
behaviour. The harness here covers what the agent *does* with the tools.

## Layout

```
evals/mcp/
├── tasks/         # one JSON file per task — see schema below
├── results/       # output JSON per run (gitignored)
├── run_evals.py   # driver
└── README.md
```

## Task schema

Each `tasks/<id>.json` is:

```jsonc
{
  "id": "clipboard-roundtrip",
  "prompt": "Build a shortcut that copies a fixed greeting to the clipboard and shows a notification.",
  "graders": {
    "min_actions": 2,
    "max_actions": 5,
    "must_contain": [
      "is.workflow.actions.setclipboard"
    ],
    "decode_succeeds": true
  }
}
```

The graders are deterministic: the harness decodes the produced
`.shortcut` file via the library and asserts the wire-format invariants.
No LLM-as-judge.

## Running

```bash
export ANTHROPIC_API_KEY=...
uv run python evals/mcp/run_evals.py            # all tasks, pass@1
uv run python evals/mcp/run_evals.py --k 3      # pass@3 (3 attempts per task)
uv run python evals/mcp/run_evals.py --task clipboard-roundtrip
uv run python evals/mcp/run_evals.py --dry-run  # validate task files only, no API
```

Results land in `results/<utc-timestamp>.json` with per-task verdicts and
aggregate pass@k.

## What gets measured

| Metric | Why |
|--------|-----|
| `pass@k` | Consistency under repetition — flaky tools fail here |
| `tool_calls_per_task` | Efficiency — fewer calls = better tool design |
| `tokens_per_task` | Whether response payloads are bloating context |
| `recovery_rate` | When an error surfaces, does the agent self-correct? |

The harness uses Anthropic's tool-use loop with the FastMCP server hosted
in-process — same code path as the stdio server, no transport noise.
