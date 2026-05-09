# V1.5 autonomous batches — summary for return

**Session:** 2026-05-09 autonomous run while user was out.
**Branches under `v15/`:** 19 unmerged.
**Reviews under `docs/architecture-review/v15-reviews/`:** 16 per-branch sonnet reviews + 3 opus deep reviews under `docs/architecture-review/v15-deep-review/`.

## How to read this

Every branch under `v15/*` is a self-contained PR-equivalent. For each, the matching review file in `docs/architecture-review/v15-reviews/` summarises verdict, test result, what landed, sample-grounding, issues, and a merge recommendation.

Three **deep reviews** (Section A: action coverage, Section B: schema infrastructure, Section C: examples + skills + docs) cover cross-cutting findings the per-branch reviews couldn't see — see `docs/architecture-review/v15-deep-review/`. The deep-review action pass that followed pushed fixes onto existing branches and created three new branches.

## Branch table

### Batch 1 — V1.5 polish, FU follow-ups

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/fu10-downloadurl-factories` | `d0c0706` | `fu10.md` | GREEN; docstring "three"→"four" inline fix per deep review |
| `v15/fu12-validate-workflow` | `df8d27d` | `fu12.md` | YELLOW→GREEN. Original review fixed inline (line trim + forward-uuid test). Deep review B raised use-before-set + hardcoded magic vars + missing re-export — all fixed inline (commit `df8d27d`). |
| `v15/fu13-textsplit-showtext` | `f1d9e2d` | `fu13.md` | GREEN |
| `v15/readme-release-notes` | `0e3c3e9` | `readme-release-notes.md` | GREEN. Deep review C raised three fixes (`.claude/` gitignore restored, line 61 wording, note_to_github example listing) — all fixed inline (commit `0e3c3e9`). |

### Batch 2 — action coverage growth + example modernization

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-file-rename` | `65412bc` | `file-rename.md` | GREEN |
| `v15/model-text-combine` | `a3be634` | `text-combine.md` | GREEN |
| `v15/model-addnewreminder` | `7a55c54` | `addnewreminder.md` | GREEN; `alert_enabled: bool` and `Quantity` for radius flagged as V1.5 polish in followups |
| `v15/note-to-github-modernize` | `0ec729a` | `note-to-github-modernize.md` | GREEN |

### Batch 3 — more high-frequency actions + inventory doc

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-sendmessage` | `2453ab2` | `sendmessage.md` | GREEN |
| `v15/model-previewdocument` | `afb0f68` | `previewdocument.md` | GREEN |
| `v15/model-filter-calendarevents` | `0a173a3` | `filter-calendarevents.md` | GREEN |
| `v15/schema-gaps-inventory` | `25915ba` | `schema-gaps-inventory.md` | YELLOW→GREEN. Deep review B caught 4 factual errors (duplicate identifier, sample count, 4 per-action key counts) + missing freshness anchor — all fixed inline (commit `25915ba`). |

### Batch 4 — small actions from gaps inventory

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-showresult` | `ddc52b6` | `showresult.md` | GREEN |
| `v15/model-choosefromlist` | `925054d` | `choosefromlist.md` | GREEN |
| `v15/model-list-helpers` | `ecbea30` | `list-helpers.md` | GREEN |
| `v15/model-alert` | `a43e528` | `alert.md` | GREEN |

### Batch 5 — deep-review action pass (new branches off `main`)

| Branch | Latest head | Source | Verdict |
|---|---|---|---|
| `v15/test-helpers-extract` | `f116673` | Deep review A: test-helper duplication finding | Forward-looking refactor; on `main` only 1 file held duplicates; the V1.5 branches' test files can drop their copies after merge |
| `v15/v1-examples-typed-handles` | `6750f0f` | Deep review C headline: canonical example used "less typed" form | 40 NamedVar string-refs eliminated across the four V1 examples; helpers now return handles instead of being void |
| `v15/wire-format-quirks-doc` | `d731fc7` | Deep review A: no central wire-format-quirks inventory | New `docs/wire-format-quirks.md` cataloguing 17 bare-key actions, 23 wire-key/python-name mismatches, 5 envelope conventions |

## Suggested merge order

All 19 branches are independent of each other (one known small conflict on `docs/known_identifiers.md` regenerations: 4 branches have hash `1c2d9afe…` for that file, 5 have `ea99b712…` — see deep-review A for the merge-order constraint). They branched from `main` after `6f499a9` (V1 closeout) + `589e500` (.gitignore cleanup).

Recommended order:

1. **Foundational (no deps, smallest blast radius first):**
   - `v15/fu10-downloadurl-factories`
   - `v15/fu13-textsplit-showtext`
   - `v15/wire-format-quirks-doc`
   - `v15/test-helpers-extract`
2. **Schema infrastructure:**
   - `v15/fu12-validate-workflow`
3. **Action coverage (bulk):**
   - `v15/model-file-rename`, `v15/model-text-combine`, `v15/model-addnewreminder`, `v15/model-sendmessage`, `v15/model-previewdocument`, `v15/model-filter-calendarevents`, `v15/model-showresult`, `v15/model-choosefromlist`, `v15/model-list-helpers`, `v15/model-alert`
4. **Examples + docs (after action coverage so the modernized examples can reference all the new actions):**
   - `v15/v1-examples-typed-handles`
   - `v15/note-to-github-modernize`
5. **Docs / discoverability (last so counts and tables reflect the merged state):**
   - `v15/schema-gaps-inventory`
   - `v15/readme-release-notes`

Within each tier, merge order doesn't matter for correctness. Whatever's easiest in your GUI.

After merging all 19, run `prek run --all-files` and `uv run pytest -q` to confirm. Test count should land somewhere around **400+ passing** (started at 336; ~75 new tests across the action branches; ~5 from FU-12 fixes; small additions from extract / quirks).

## What landed without a branch (committed directly to `main`)

- **`589e500`** — gitignore `.claude/`
- **`3c6db55`** — committed the 20 public decoded sample XMLs (`samples/decoded/*.xml`); kept `samples/decoded/private/` ignored. Per deep review C: makes the 28 wire-format equivalence tests run on fresh clones instead of skipping. Test count on a clean clone now matches the development environment.

## Open V1.5 follow-ups (carried forward from reviews)

These were flagged across the reviews + deep reviews but deliberately NOT actioned in the autonomous batches. Each has a clear home (existing handoff entry or new):

- **`alert_enabled: bool` translator for `AddNewReminder`** — V1.5 polish (deep review A); convert string `"Alert"`/`"No Alert"` to a boolean Python field.
- **`Quantity`-typed field for `AddNewReminder.alert_location_radius`** — currently raw dict pass-through.
- **`content_item_filter` dict-type guard on `FilterCalendarEvents`** — two-line defensive check.
- **`properties.calendarevents` companion action** — surfaced in `dictionary.xml`; not modelled.
- **`WFItemIndex` without `WFItemSpecifier` Apple quirk** on `GetItemFromList` — needs a fresh sample to confirm.
- **The 3 V1 xfails:** `RepeatCount` configured-count sample, `ChooseFromMenu` fresh sample (fixed in the V1 sweep: `TextSplit` Show-text); the first two remain.
- **TextCombine cross-field check** moved from `_params` to `__post_init__` (pattern-outliers cleanup, deep review A).
- **Three actions missing `__post_init__`** (deep review A; identify which during cleanup).
- **Skill refresh:** `make-shortcut/SKILL.md` should show `s.set` typed handles, `ask_text_on_import`, and factory methods. `edit-shortcut/SKILL.md` doesn't mention `Shortcut.from_file` or `_extra` round-trip.
- **`docs/handoff.md`** needs status-flips for closed FUs after each batch merges (FU-10 done, FU-12 done, FU-9 done, FU-13 done).
- **Doc sweep checklist post-V1.5-merge** (deep review C): ~15 docs need updates.
- **Schema-gaps Batch B onwards** (per `docs/schema-gaps.md`): list/selection actions beyond what was modelled here, then filter family (V2), then surface integrations.
- **More tier-2 action models:** `share` (3), `sendemail` (3), `gettraveltime` (3), `getlastphoto`/`getlastscreenshot` (3 each), `round` (3), etc.

## What this session deliberately did NOT do

- **No merges.** All 19 branches remain unmerged. Auto-mode said "don't take overly destructive actions"; merging into `main` is your call.
- **No `v1.0` tag.** Still your call.
- **No remote operations.** Repo is local-only per the user's posture (private until `v1.0+`).

## State integrity check

All branches and reviews land on `main`'s git database (worktrees share `.git/`). The worktrees themselves live under `.claude/worktrees/agent-<id>/` and are gitignored. To clean up after merging:

```sh
git worktree list                                             # see all worktrees
git worktree remove .claude/worktrees/agent-<id> --force      # per worktree
```

Or wait — the worktrees auto-clean after their branches merge.
