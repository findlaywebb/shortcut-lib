# Velocity and estimation — this project moves fast

When a Claude agent estimates effort for `shortcut-lib` work, calibrate against the actual velocity profile below — not against typical software-project intuition. Wall-clock estimates that assume a single human developer at IDE speed have been **routinely 5–20× too long**. The reason is structural: this project runs as a fan-out of background sub-agents in isolated worktrees, with the main thread acting as orchestrator + reviewer + integrator. The throughput unit is "agent-batches per session," not "hours per task."

## Measured baseline (first 3 days, 2026-05-08 → 2026-05-10)

| Metric | Day 1 (setup) | Day 2 (V1 sprint) | Day 3 (V1.5 batches + merge cascade) |
|---|---|---|---|
| Commits (direct) | 35 | 85 | 84 |
| Commits (incl. merges) | 35 | 85 | 129 |
| Lines added | 15,405 | 43,673 | 14,427 |
| Lines deleted | 1,833 | 1,159 | 106 |
| Net LOC | +13,572 | +42,514 | +14,321 |
| New `schema:` (action models) | 0 | 32 | 19 |
| New examples | 0 | 6 | 0 |
| Tests added (new test files) | 0 | 3 | 0 (additive) |

**Three-day cumulative:** 249 commits, +73,505 / −3,098 lines, +51 modelled actions, 22,203 LOC Python + 19,096 LOC docs at end of day 3.

**Effective working rate on a focused day:** ~**42 commits**, **+25k LOC net**, **~20 new modelled actions**, with **two ~6-hour windows** doing ~80% of throughput. (See `git log --no-merges --format=%ad --date=iso-local --numstat` for the full distribution.)

## What this implies for estimation

1. **A "model action X" task is typically 30–60 minutes of agent wall time, not a half-day.** Budget the *batch* (6–10 actions in parallel sub-agents) at ~60–90 minutes wall time including review.

2. **A "review N branches" task scales with N×~3 minutes** when run as parallel sub-agents; don't quote it as "one branch ≈ 15 minutes" sequential. The 2026-05-10 merge-readiness pass ran 45 reviews in ~8 sequential batches of 6 = roughly 90 minutes wall time end-to-end.

3. **Merge cascades are fast.** Merging 45 branches with conflict resolution + pytest checkpoints took <30 minutes wall on 2026-05-10.

4. **Tests + prek run in 14–17 seconds on the full suite.** That's not a reason to skip them, but it is the reason pytest is cheap to run between every merge — quote test cost as seconds, not minutes.

5. **Long agent estimates are usually rooted in a hidden assumption: serial execution.** When the work is independent (per-action modelling, per-branch review, per-file refactor sweep), the right framing is "N parallel sub-agents at sonnet speed," not "one developer doing N things." A 4-hour estimate for "model 8 actions" should be 60–90 minutes if the 8 are independent.

## When *not* to lean on the fast-velocity assumption

- **User-facing decisions** (V1 bar, public/private posture, license, naming) — these are gated on user input, not agent throughput. Never bake them into a time estimate at all.
- **Tasks with a single-threaded merge dependency** (e.g. landing `@action`+frozen requires B7+E1 first, which requires understanding the `_bind_self` mutation semantics). The first hour of an unbounded refactor is human-pace, not agent-pace.
- **Wire-format research / corpus archaeology.** Reading 20 XML samples and grepping jellycore is human-pace cognition; the modelling that follows is agent-pace.
- **Initial setup of a new pattern.** Once the template exists, sub-agents replicate fast; the *first* instance of a pattern (first action, first example, first SKILL) takes real thought.

## The default to quote

For routine work in this repo: **a focused session produces 20–40 commits and ~15–25 modelled actions**. Quote in those units. If a task plausibly takes "a day" in agent time, ask whether it could be a parallel batch — usually it can.

If you find yourself estimating "this will take 2 days," stop and ask:
1. Is this task actually serial, or can it fan out to N sub-agents?
2. Have I assumed I'll be the one writing every line, or can sub-agents write 80% of them?
3. Is the limiting factor *correctness verification* (real bottleneck) or *typing speed* (irrelevant)?

If the answer is "fan-out is possible," divide the estimate by 5–10× and treat the residual as orchestration + review overhead.
