# V1.5 autonomous batches — summary for return

**Session:** 2026-05-09 autonomous run while user was out.
**Branches produced:** 16, all unmerged on `main`.
**Reviews produced:** 16, all in `docs/architecture-review/v15-reviews/` and committed to `main`.
**Stopping point:** sub-agent token budget exhausted. The list-helpers review was written by the agent but the agent hit the limit on its follow-up report; I confirmed the review file is complete (167 lines) and committed it.

## How to read this

Every branch under `v15/*` is a self-contained PR-equivalent. For each, the matching review file in `docs/architecture-review/v15-reviews/` summarises verdict, test result, what landed, sample-grounding, issues, and a merge recommendation. The reviewer was a sonnet sub-agent with no context other than the branch + brief; reviews are independent.

## Branch table

Sorted by batch / verdict.

### Batch 1 — V1.5 polish, FU follow-ups

| Branch | Head | Review | Verdict |
|---|---|---|---|
| `v15/fu10-downloadurl-factories` | `92157ba` | `fu10.md` | GREEN |
| `v15/fu12-validate-workflow` | `be92ca1` | `fu12.md` | YELLOW originally; fixes pushed (validate.py trimmed, forward-uuid test added). Now GREEN. Use-before-set in `variable-not-set` is a documented V1.5 backlog gap. |
| `v15/fu13-textsplit-showtext` | `f1d9e2d` | `fu13.md` | GREEN |
| `v15/readme-release-notes` | `1f8ccd9` | `readme-release-notes.md` | GREEN; one count typo fixed inline (365→369 unmodelled identifiers) |

### Batch 2 — action coverage growth + example modernization

| Branch | Head | Review | Verdict |
|---|---|---|---|
| `v15/model-file-rename` | `65412bc` | `file-rename.md` | GREEN |
| `v15/model-text-combine` | `a3be634` | `text-combine.md` | GREEN. Jellycore-vs-corpus divergence independently verified (corpus right, jellycore stale on `combine` parameter key) |
| `v15/model-addnewreminder` | `7a55c54` | `addnewreminder.md` | GREEN. `alert_enabled` bool→string mapping flagged as V1.5 design opportunity; `"When I Leave"` Literal value is speculative |
| `v15/note-to-github-modernize` | `0ec729a` | `note-to-github-modernize.md` | GREEN. One minor unconverted `NamedVar` noted, non-blocking |

### Batch 3 — more high-frequency actions + inventory doc

| Branch | Head | Review | Verdict |
|---|---|---|---|
| `v15/model-sendmessage` | `2453ab2` | `sendmessage.md` | GREEN. Recipient envelope as raw pass-through (V1.5 deliberate scope); `IntentAppDefinition` exclusion correct but docstring says "runtime" should say "authoring time" |
| `v15/model-previewdocument` | `afb0f68` | `previewdocument.md` | GREEN — single-param action, no issues |
| `v15/model-filter-calendarevents` | `0a173a3` | `filter-calendarevents.md` | GREEN. Path B (raw dict pass-through for `WFContentItemFilter` predicate) was the right V1.5 call; shared `FilterPredicate` type belongs in V2. Two nice-to-haves: dict-type guard on `content_item_filter` input + `properties.calendarevents` companion-action TODO |
| `v15/schema-gaps-inventory` | `63fca34` | `schema-gaps-inventory.md` | GREEN. Recommend a `main @ <hash>` anchor postscript on merge so Section 5 counts don't go stale |

### Batch 4 — small actions from the gaps inventory's tier-1

| Branch | Head | Review | Verdict |
|---|---|---|---|
| `v15/model-showresult` | `ddc52b6` | `showresult.md` | GREEN. Confirmed unusual `Text` (not WF-prefixed) wire key — corpus-cited |
| `v15/model-choosefromlist` | `925054d` | `choosefromlist.md` | GREEN with two observations: branch carries a clean `docs/known_identifiers.md` corpus regeneration; reviewer noted earlier review files appear "deleted from branch" — this is benign (branch was created before those reviews were committed to main; merge will preserve them) |
| `v15/model-list-helpers` | `ecbea30` | `list-helpers.md` | GREEN. `Count` confirmed using bare `Input` (not `WFInput`) — sample-grounded. `WFItemIndex` co-emission quirk: the schema emits `WFItemSpecifier="Item At Index"` alongside `WFItemIndex` while one corpus sample has `WFItemIndex` with NO specifier — non-blocking but a fresh-sample check is queued |
| `v15/model-alert` | `a43e528` | `alert.md` | GREEN. Empty-message-key omission divergence from Apple's emission documented in three places |

## Suggested merge order

All 16 branches are independent of each other — they branched from `main` after the V1 closeout commit (`6f499a9`) and the `.gitignore` cleanup (`589e500`). They don't conflict on the same files except for these incidental overlaps:

- All batch-2/3/4 action models add a new file under `src/shortcut_lib/schema/actions/`. No conflict.
- Several branches (`note-to-github-modernize`, examples touched in `fu10` test) modify or add example files. Shouldn't conflict.
- `v15/model-choosefromlist` carries a regenerated `docs/known_identifiers.md` (clean swap, not append) — if any other branch also touches that file, merge will need a manual reconcile. Prefer to merge `choosefromlist` last so you can regenerate with the merged set.

**Recommended order:**

1. **Batch 1 first** (FU-10, FU-12, FU-13, README) — core schema and docs.
2. **Batch 2 second** (file-rename, text-combine, addnewreminder, note-to-github-modernize) — action coverage + the example migration that depends on V1 patterns being established.
3. **Batch 3 third** (sendmessage, previewdocument, filter.calendarevents, schema-gaps).
4. **Batch 4 last** (showresult, choosefromlist, list-helpers, alert) — tier-2 small actions.

Within a batch, order doesn't matter for correctness. Whatever's easiest for you in a GUI.

After merging all 16, run `prek run --all-files` and `uv run pytest -q` to confirm. Test count should land somewhere around **400+ passing** (started at 336 + batches contributed ~75 new tests across the 16 branches).

## Open V1.5 follow-ups (carried forward from reviews)

These were flagged across the 16 reviews but deliberately NOT actioned in the autonomous batches:

- **`docs/handoff.md` updates:** Several follow-ups (FU-10, FU-12, FU-13, FU-9 status etc.) need handoff entries flipped from "open" to "done" once you merge the corresponding branch.
- **`alert_enabled: bool` translation layer for `AddNewReminder`** — V1.5 polish (review-flagged design opportunity).
- **`content_item_filter` dict-type guard on `FilterCalendarEvents`** — two-line defensive check.
- **`properties.calendarevents` (Get Event Detail)** — companion action surfaced in `dictionary.xml`; not modelled.
- **`WFItemIndex` without `WFItemSpecifier` Apple-quirk on `GetItemFromList`** — needs fresh sample to confirm whether the schema should match Apple's omission or keep the more explicit form.
- **The 3 V1 xfails** (RepeatCount configured-count, ChooseFromMenu fresh sample, TextSplit Show-text was fixed in this batch; the first two remain).
- **Schema-gaps Batch B onwards** (per `docs/schema-gaps.md`): list/selection actions beyond what was modelled here, then filter family (V2), then surface integrations.

## What this session deliberately did NOT do

- **No merges.** All 16 branches remain unmerged. Auto-mode said "don't take overly destructive actions"; merging into `main` is your call.
- **No `v1.0` tag.** Still your call.
- **No remote operations.** Repo is local-only per the user's posture (private until `v1.0+`).
- **No further action models** beyond the 16 — sub-agent budget exhausted at the time of stopping. Limit resets at 1:40pm Europe/London (per the agent error).

## State integrity check

All branches and reviews land on `main`'s git database (worktrees share `.git/`). The worktrees themselves live under `.claude/worktrees/agent-<id>/` and are gitignored — they exist on disk for git's worktree mechanism to function but aren't tracked content. To clean them up after merging:

```sh
git worktree list                                             # see all worktrees
git worktree remove .claude/worktrees/agent-<id> --force      # per worktree
```

Or wait — the worktrees auto-clean after their branches merge.
