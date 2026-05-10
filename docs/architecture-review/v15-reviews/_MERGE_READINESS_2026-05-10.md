# 2026-05-10 Merge-readiness pass — master summary

Driver: user requested a sonnet sub-agent merge-review per branch (45 `v15/*` branches outstanding) since they had no capacity to review manually. Eight batches of six (final batch three) dispatched sequentially, each agent doing a dry-run merge against current `main` plus pytest on the merged state. Per-branch findings appended to existing `docs/architecture-review/v15-reviews/<name>.md` files under a `## 2026-05-10 merge-readiness pass` heading.

## Verdict tally

- **44 Pass** (10 with minor inline corrections).
- **1 Request-Human**: `v15/model-list-helpers` — collides with `v15/model-getitemfromlist` on `src/shortcut_lib/schema/actions/get_item_from_list.py`. Both branches introduce the file with diverging schemas. Per the Batch 4 review, `model-getitemfromlist`'s implementation is the more corpus-faithful one.

No `Fail-Opus` or `Request-Opus-Review` outcomes. Every speculative-Literal candidate (`model-round`, `model-math` scientific mode, `model-resizewindow`, `model-number-formatting` style modes) was deemed adequately disclaimed and merge-ready by its sonnet reviewer.

## Inline corrections applied (sonnet, on the v15 branch)

| Branch | Commit | Fix |
|---|---|---|
| `v15/model-sendmessage` | `b8f5eb1` | imprecise IntentAppDefinition test comment |
| `v15/model-choosefromlist` | `db270b3` | jellycore-only comment on `select_all_initially` |
| `v15/model-gettraveltime` | `0d9718f` | corpus-unverified annotations on `WFFromAddress` |
| `v15/model-resizewindow` | `69a33ce` | jellycore-only provenance caveat on `bring_to_front` |
| `v15/model-sendemail` | `34dc081` | deferred-import nit |
| `v15/model-list` | `9d41c5b` | NumPy → Google docstring style + type annotation |
| `v15/model-addnewreminder` | `7e1bc0c` | "(inferred by symmetry)" on speculative `WFAlertCondition` |
| `v15/model-calculateexpression` | `24f46b5` | line-citation off-by-2 fix (396→394) |
| `v15/model-math` | `67314bd` | minimum-host attribution to jellycore iOS14 |
| `v15/skill-refresh-edit-shortcut` | `ecd0ce5` | "duplicate on re-emit" → "silently overwrite" |

Three branches (`v15/model-round`, `v15/usemodel-empty-prompt-guard`, `v15/test-empty-string-coverage`) had no per-branch review file in their worktree (the file lives on main). Each agent (or the main thread, for the empty-string branch where the sub-agent's merge dry-run was permission-blocked) back-filled the review file from main and appended the merge-readiness section. Commits: `74708a2`, `c0e860a`, `0fbab87` respectively.

## Pre-existing main issues surfaced during review (out of scope, file separately)

- **Flaky test on main** — flagged by `v15/model-output-action` reviewer; 1 unrelated test occasionally fails. Worth filing under `docs/issues/` if not already tracked.
- **Ruff FURB110 in `src/shortcut_lib/builder.py`** — flagged by `v15/fu12-validate-workflow` reviewer; pre-exists on main.
- Both observed across multiple batches; not introduced by any of the reviewed branches.

## Hard merge-order constraints (unchanged from `_SUMMARY.md`, re-confirmed)

1. **`v15/usemodel-empty-prompt-guard` BEFORE `v15/test-empty-string-coverage`** — the latter has `test_use_model_empty_prompt_emits_empty_string` which documents the OLD buggy behaviour and is intended to be dropped at merge time (superseded by `test_use_model_empty_prompt_raises` on the guard-fix branch).
2. **`v15/v1-examples-typed-handles` BEFORE `v15/skill-refresh-make-shortcut`** — the SKILL teaches the typed-handle pattern that the example branch puts into `examples/vault_note_to_git.py`.
3. **`v15/model-list-helpers` ↔ `v15/model-getitemfromlist`** — file-level collision on `get_item_from_list.py`. User must pick which schema wins. Per Batch 4 review, `model-getitemfromlist` is the more corpus-faithful implementation; `model-list-helpers` should likely have its `get_item_from_list.py` dropped (its `count.py` is independent and merge-safe).

## Soft conflicts (auto-resolvable on merge)

- **`docs/known_identifiers.md`** — regenerated divergently across batches; resolution is to take main's regenerated version (deterministic; the branch's contribution gets re-emitted by the regen tool post-merge). Some reviewers resolved this in their dry-run; others noted it.
- **`pyproject.toml` ruff RUF001/RUF002 suppressions** — flagged once by `v15/model-math` reviewer; resolves trivially by accepting main's version (suppressions proven unnecessary).
- **`.gitignore`** — flagged once by `v15/readme-release-notes` reviewer; resolution is to take main's more precise `.claude/*` + `!.claude/rules/` form.

## Post-merge follow-ups surfaced by reviewers (for `docs/wire-format-quirks.md`)

- **`dnd.set` dual-envelope same-UUID example** from `start_pomodoro.xml` — flagged by `v15/model-system-controls` reviewer. Demonstrates "envelope shape determined by slot semantics, not value type."
- **Map-family wire-key inconsistency table** — flagged by `v15/model-maps` reviewer. The four map actions use three different wire keys for conceptually the same destination slot.
- **`v15/wire-format-quirks-doc` reviewer** noted both of the above as additions to make on top of that branch post-merge.

## V1.5 polish follow-ups (not merge blockers; carry forward)

These were re-confirmed by individual reviews; tracked in main's `docs/handoff.md` or `_SUMMARY.md`:

- `alert_enabled: bool` translator for `AddNewReminder`
- `Quantity`-typed `alert_location_radius` on `AddNewReminder`
- `content_item_filter` dict-type guard on `FilterCalendarEvents`
- `picker_value` override field on `AdjustDate`
- 3 V1 xfails (`RepeatCount` configured-count, `ChooseFromMenu` fresh sample)
- TextCombine cross-field check moved to `__post_init__`
- 3 actions missing `__post_init__` (deep review A)
- `_SUMMARY.md` is missing entries for some recently-added branches (`v15/model-statistics` second/third commits, `v15/usemodel-empty-prompt-guard`)

## Recommended human-review queue (in order)

1. **Decide `model-list-helpers` ↔ `model-getitemfromlist` collision.** Likely action: accept `model-getitemfromlist`'s `get_item_from_list.py`; on `model-list-helpers` merge, drop the duplicate file (keep its `count.py`).
   1. Decision: Go with `model-getitemfromlist`
2. **Merge in the order suggested in `_SUMMARY.md`** — foundational/fu* first, then schema infra (with the `usemodel-empty-prompt-guard` → `test-empty-string-coverage` ordering enforced), then bulk action coverage, then examples, then SKILLs/docs.
   1. Decision: Follow the suggested order.
3. **Drop the stale test** on merging `v15/test-empty-string-coverage`: `test_use_model_empty_prompt_emits_empty_string` (replaced by `test_use_model_empty_prompt_raises` from the guard branch).
   1. Decision - yes
4. After all merges, file separate issues for the two pre-existing main concerns (flaky test, FURB110).
   1. Decision - No, just address them in a new commit directly on main.
5. Human additions:
   1. Address Post-merge follow-ups as a commit on main.
   2. Either create issues for downstream to address V1.5 polish follow-ups, or for simple actions, just fix them in a commit on main.
