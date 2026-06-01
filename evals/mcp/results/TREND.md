# MCP eval results and trend

This file tracks what the agent-level MCP eval harness (`evals/mcp/`) has
measured over time, and pins each result to the commit it ran against so a
change in the numbers can be traced to a change in the code or the suite.

Regenerate the comparison table at any time with:

```sh
uv run python evals/mcp/report.py            # latest run per (provider, model, effort)
uv run python evals/mcp/report.py --baseline claude-sonnet-4-6
```

Raw per-run summaries live alongside this file as `*.json`; the v1 baseline
runs are under `archive/`.

## What the harness measures

Each task gives the model a natural-language request; the model drives the
five MCP tools and the emitted `.shortcut` is graded **deterministically**
(decode + structural assertions, no LLM-as-judge). Metrics:

- **pass@1** — first-attempt success rate, with a 95% bootstrap CI resampled
  at the task level. Comparable across any `k`.
- **pass@3 (est)** — unbiased HumanEval estimator `1 - C(n-c,k)/C(n,k)`
  recomputed at a common floor of k=3 so a k=10 run is comparable to a k=3 run.
- **pass^3** — reliability: probability of succeeding on *every* one of 3
  attempts (`p**3`). This is the production-relevant number; a high pass@k with
  a low pass^k means "capable but not reliable" (the tau-bench pattern).
- **tokens/attempt, calls/attempt** — cost, normalised per attempt (not per
  task) so runs at different `k` compare honestly.

## Scored matrix — v2 suite (20 tasks)

Run 2026-06-01. Anthropic at k=3, OpenAI at k=10 (the OpenAI budget is cheap
per-token relative to the limited Anthropic budget, so it buys tighter
intervals for free; pass@1 and the floor-k pass@3 stay comparable). OpenAI
also swept `reasoning.effort`. gpt-5.5 was capped at low+medium effort on a
cost decision (the $5/1M-input flagship at k=10 is ~$10/run).

| model | provider | effort | k | n | pass@1 [95% CI] | pass@3 (est) | pass^3 | tokens/attempt | calls/attempt | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-sonnet-4-6 | anthropic | none | 3 | 20 | 95% [85%, 100%] | 95% | **0.86** | **5,362** | 7.6 | 098f0d4 |
| claude-haiku-4-5 | anthropic | none | 3 | 20 | 95% [80%, 100%] | 95% | 0.77 | 18,438 | 7.8 | 098f0d4 |
| gpt-5.5 | openai | low | 10 | 20 | 95% [79%, 100%] | 94% | 0.43 | 19,833 | 7.0 | 31bff9e |
| gpt-5.5 | openai | medium | 10 | 20 | 85% [80%, 100%] | 95% | 0.46 | 20,616 | 7.3 | 31bff9e |
| gpt-5-mini | openai | low | 10 | 20 | 80% [74%, 95%] | 95% | 0.23 | 26,107 | 6.7 | 31bff9e |
| gpt-5-mini | openai | medium | 10 | 20 | 85% [80%, 98%] | 95% | 0.39 | 27,514 | 6.8 | 31bff9e |
| gpt-5-mini | openai | high | 10 | 20 | 90% [80%, 99%] | 95% | 0.41 | 32,156 | 7.0 | 31bff9e |

Paired bootstrap vs claude-sonnet-4-6 (same tasks, per-task pass-rate deltas):
only **gpt-5-mini at low (-8%, CI [-15%, -3%]) and medium (-4%, [-8%, -0%])**
are significantly worse; every other model is statistically tied with Sonnet
on pass@1.

### Findings

- **Every model clears pass@3 ~95%.** The suite is solvable-with-retries
  across the board; the ceiling is two tasks no model reliably hits (see below).
- **Reliability separates them, not capability.** pass^3 ranks
  Sonnet (0.86) > Haiku (0.77) >> OpenAI (0.23-0.46). The OpenAI models get the
  right answer *eventually* far more often than they get it *every* time.
- **Sonnet is the token-efficiency standout** at ~5.4k tokens/attempt, ~3.4x
  leaner than Haiku and ~4x leaner than the OpenAI models, at equal tool-call
  counts (~7). The MCP server's output-minimisation plus Anthropic prompt
  caching is visible here.
- **Reasoning effort helps the small model** (gpt-5-mini pass^3
  0.23 -> 0.39 -> 0.41 across low/medium/high) but is within noise on gpt-5.5.
- **Two persistent misses** across providers: `02-dictate-to-clipboard` (models
  avoid the `dictate.text` action) and, before it was fixed, the over-strict
  task 18 grader (see methodology).

## Methodology: pilot -> error-analysis -> scored run

The first 2026-06-01 OpenAI sweep was a **pilot**, not scored. It surfaced two
issues, which is what a pilot is for:

1. **An over-strict grader.** Task 18 ("read clipboard, add a prefix, notify")
   mandated a `text.combine` action and `min_actions>=3`, but the task is
   correctly solvable in two actions (a notification whose body interpolates the
   clipboard variable inline). Fixed in `098f0d4` to require only the two
   endpoints.
2. **A harness robustness gap.** Under signing contention at concurrency 30, a
   corrupt signed file made the decoder raise mid-grade, and that exception was
   not isolated per attempt, so it aborted a whole run. Fixed in `31bff9e`
   (per-attempt failures are now caught) and the scored OpenAI runs use
   concurrency 12.

The pilot results were discarded and the scored matrix above was run clean.
(Lesson, now folded into the build-evals skill: pilot a new harness on the
cheapest capable model; a grader bug found on a $5/1M flagship costs ~20x the
same bug found on a mini.)

### Commit attribution note

Anthropic runs are stamped `098f0d4`, OpenAI runs `31bff9e`. The only
difference between those commits is the per-attempt crash-isolation fix, which
is behaviourally inert for runs that did not crash (the Anthropic runs at
concurrency 2 never hit the contention path). The numbers are comparable.

## Archived v1 baseline — 12-task suite

Five runs from 2026-05-27, under `archive/`. This was a smaller 12-task suite
with the pre-refusal system prompt, so it is **not** directly comparable to the
v2 matrix; it is kept for history. Commits are inferred from the run timestamp
(the harness did not stamp commits yet), flagged `git_commit_inferred` in each
file.

| run (UTC) | model | k | pass@1 | inferred commit |
|---|---|---|---|---|
| 14:51 | sonnet | 1 | 67% (8/12) | `50468ec` (prompt caching + task-12 fix) |
| 15:20 | sonnet | 1 | **92% (11/12)** | `4f2588f` (includes `0df01af`) |
| 14:15 | haiku | 2 | 100% | `147736f` |
| 14:30 | haiku | 1 | 67% | `611961d` |
| 14:40 | haiku | 1 | 100% | `611961d` |

The Sonnet 67% -> 92% jump is attributable to **`0df01af`**
("must_contain_any grader and relax three over-strict tasks"): the improvement
was a grader correction, not a model change. This is the same class of
over-strict-grader fix as task 18 above.
