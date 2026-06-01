# MCP server eval harness

A small task-based eval harness that drives a model through the
`shortcut-lib` MCP server and grades end-to-end task completion.

The harness is provider-agnostic: the same tasks and the same deterministic
graders run against both Anthropic (Messages API) and OpenAI (Responses API
tool-calling). Only the model conversation loop differs, behind a small
driver abstraction (`_drivers.py`); the MCP-call mechanics and grading
(`_grading.py`) are shared.

This is the agent-level half of the testing pyramid. Tool-level tests
(`tests/test_mcp_server.py`) cover JSON-RPC conformance and per-tool
behaviour. The harness here covers what the agent *does* with the tools.

## Layout

```
evals/mcp/
├── tasks/         # one JSON file per task, see schema below
├── results/       # output JSON per run (gitignored)
├── run_evals.py   # orchestrator: load tasks, fan out attempts, summarise
├── _drivers.py    # Anthropic + OpenAI agent loops behind one abstraction
├── _grading.py    # task model + deterministic graders
├── _stats.py      # bootstrap CI, pass@k estimator, pass^k (stdlib only)
├── report.py      # cross-provider markdown comparison + paired delta
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

Optional grader fields (backward-compatible, default to off):

| Field | Effect |
|-------|--------|
| `must_not_contain` | Attempt FAILS if any listed identifier is in the build |
| `expect_no_build` | Refuse-case: PASSES iff no `.shortcut` is produced; building anything FAILS, and the content checks are skipped |

## Running

```bash
export ANTHROPIC_API_KEY=...
uv run python evals/mcp/run_evals.py            # all tasks, pass@1
uv run python evals/mcp/run_evals.py --k 3      # pass@3 (3 attempts per task)
uv run python evals/mcp/run_evals.py --task clipboard-roundtrip
uv run python evals/mcp/run_evals.py --dry-run  # validate task files only, no API

export OPENAI_API_KEY=...
uv run python evals/mcp/run_evals.py --model gpt-5.5 --k 10  # OpenAI Responses
uv run python evals/mcp/run_evals.py --model X --provider openai  # force provider
```

Provider is inferred from the model name (`claude-*` -> anthropic, `gpt-*`
and o-series -> openai); `--provider` overrides. Results land in
`results/<utc-timestamp>.json` with per-task verdicts, aggregate pass@k, the
bootstrap CI, the unbiased pass@k estimator, pass^k, and a `git_commit` /
`git_dirty` stamp of the code the run executed against.

## Comparing runs

```bash
uv run python evals/mcp/report.py                          # latest run per model
uv run python evals/mcp/report.py --baseline claude-sonnet-4-6
```

`report.py` keeps the latest run per (provider, model), prints a markdown
table, and recomputes the unbiased pass@k at a common floor k (default 3) so
an OpenAI k=10 run is comparable to an Anthropic k=3 run. It also prints a
paired bootstrap delta of each non-baseline model against the baseline.

## What gets measured

| Metric | Why |
|--------|-----|
| `pass@1` + 95% CI | Headline rate with a task-level bootstrap interval |
| `pass@k` (unbiased) | HumanEval estimator: consistency under repetition |
| `pass^k` | Reliability: probability all k attempts pass |
| `tool_calls_per_task` | Efficiency: fewer calls = better tool design |
| `tokens_per_task` | Whether response payloads are bloating context |
| `recovery_rate` | When an error surfaces, does the agent self-correct? |

The harness uses the provider's tool-use loop with the FastMCP server hosted
in-process: same code path as the stdio server, no transport noise.
