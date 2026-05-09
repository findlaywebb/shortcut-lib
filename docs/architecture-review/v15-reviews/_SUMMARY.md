# V1.5 autonomous batches — summary for return

**Session:** 2026-05-09 autonomous run while user was out.
**Branches under `v15/`:** 27 unmerged.
**Reviews under `docs/architecture-review/v15-reviews/`:** 26 per-branch sonnet reviews + 3 opus deep reviews under `docs/architecture-review/v15-deep-review/`.

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

### Batch 6 — more high-frequency action coverage

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-share` | `9af2dd3` | `share.md` | GREEN |
| `v15/model-sendemail` | `7459b8b` | `sendemail.md` | GREEN |
| `v15/model-round` | `b5fa038` | `round.md` | GREEN; Literal speculation honestly documented (1/3 mode + 0/11 place sample-confirmed) |
| `v15/model-photo-getters` | `50b26bc` | `photo-getters.md` | GREEN; both `getlastphoto` and `getlastscreenshot` share the same `WFGetLatestPhotoCount` wire key |

### Batch 7 — tier-2 action coverage + SKILL refresh

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-gettraveltime` | `aae1eeb` | `gettraveltime.md` | GREEN; the brief speculated `coerce_text_field` for `WFDestination` but the agent correctly used `coerce_value` per corpus |
| `v15/model-readinglist` | `b7e4a45` | `readinglist.md` | GREEN; `WFURL` here is `WFTextTokenAttachment` (NOT `WFTextTokenString` like `DownloadURL.WFURL`) — a useful distinction documented in the review |
| `v15/model-resizewindow` | `5b375f7` | `resizewindow.md` | GREEN; 2/11 Literal values sample-confirmed, 9 from Apple surface honestly documented |
| `v15/skill-refresh-make-shortcut` | `571bd66` | `skill-refresh-make-shortcut.md` | APPROVE with **merge-order constraint**: must merge AFTER `v15/v1-examples-typed-handles` because the SKILL cross-references `examples/vault_note_to_git.py` and teaches the new typed-handle pattern that `v1-examples-typed-handles` puts in that file |

## Suggested merge order

All 27 branches are independent of each other except for one **hard constraint** and one **soft constraint**:

- **HARD: `v15/v1-examples-typed-handles` must merge BEFORE `v15/skill-refresh-make-shortcut`.** The SKILL teaches the typed-handle pattern and cross-references `examples/vault_note_to_git.py`; on `main` that file uses the OLD pattern, but `v1-examples-typed-handles` migrates it. If skill-refresh merges first, the cross-reference points at code that contradicts what the SKILL teaches.
- **SOFT: divergent `docs/known_identifiers.md` regenerations** across batch-1 vs batch-A branches (4 with hash `1c2d9afe…`, 5 with `ea99b712…`). Resolves by merge order; not a correctness issue.

Recommended tiered order:

1. **Foundational (no deps, smallest blast radius first):**
   - `v15/fu10-downloadurl-factories`
   - `v15/fu13-textsplit-showtext`
   - `v15/wire-format-quirks-doc`
   - `v15/test-helpers-extract`
2. **Schema infrastructure:**
   - `v15/fu12-validate-workflow`
3. **Action coverage (bulk; order doesn't matter within tier):**
   - Batch 2: `v15/model-file-rename`, `v15/model-text-combine`, `v15/model-addnewreminder`
   - Batch 3: `v15/model-sendmessage`, `v15/model-previewdocument`, `v15/model-filter-calendarevents`
   - Batch 4: `v15/model-showresult`, `v15/model-choosefromlist`, `v15/model-list-helpers`, `v15/model-alert`
   - Batch 6: `v15/model-share`, `v15/model-sendemail`, `v15/model-round`, `v15/model-photo-getters`
   - Batch 7: `v15/model-gettraveltime`, `v15/model-readinglist`, `v15/model-resizewindow`
4. **Examples (after action coverage):**
   - `v15/v1-examples-typed-handles` ← **must precede the SKILL refresh**
   - `v15/note-to-github-modernize`
5. **Docs / SKILLs / discoverability (last):**
   - `v15/skill-refresh-make-shortcut` ← gated on (4) above
   - `v15/schema-gaps-inventory`
   - `v15/readme-release-notes`

Within each tier (excepting the HARD constraint above), merge order doesn't matter for correctness.

After merging all 27, run `prek run --all-files` and `uv run pytest -q` to confirm. Test count should land somewhere around **450+ passing** (started at 336; ~150+ new tests across action branches + envelope oracle + factory methods + Var[T] + FU-12 fixes).

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
