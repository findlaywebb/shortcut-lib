# V1.5 autonomous batches — summary for return

**Session:** 2026-05-09 → 2026-05-10 autonomous runs.
**Branches under `v15/`:** 46 unmerged (31 initial + 4 batch 9 + 3 batch 10 + 2 batch 11 + 2 batch 12 + 2 batch 13 + 1 batch 14 + 1 doc-quality-audit).
**Reviews under `docs/architecture-review/v15-reviews/`:** 30+ per-branch sonnet reviews + 3 opus deep reviews under `docs/architecture-review/v15-deep-review/`.

**Tag applied 2026-05-09:** `v0.1.0` on `main` at `d1ad7d4` — the prior "V1 done" milestone. Per the user's versioning convention (pre-1.0 minor numbers are an alpha/beta sequence; 0.99 → 0.100 valid before 1.0), the road from v0.1.0 to v1.0.0 is the comprehensive corpus action coverage + per-action docs work. Many 0.X minor versions to come.

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

### Batch 9 — first batch under redefined v1.0.0 criterion

User redefined v1.0.0 on 2026-05-09 (later in the day): *"v1.0.0 will be when we can make any shortcut with any of the existing actions, with clear docs on each action."* Doc quality is now first-class. This batch dispatches three more action models alongside a doc-quality audit pass over the 24 V1 leaf actions on main.

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-list` | `ab64eb0` | `list.md` | GREEN. `BuildList` class name (avoids `list` builtin shadow). Plain `<array>` of `<string>` for `WFItems`; empty list omits the key entirely; items must be strings (no per-item variable refs). 13 tests. Doc 4/5. |
| `v15/model-math` | `5231002` | `math.md` | GREEN-with-fix-applied-inline. Initial head `2cdc16e` made false jellycore-source claims for scientific mode (jellycore has NO `is.workflow.actions.math` entry); `5231002` corrects to honest "UI-inferred, unconfirmed" framing. Arithmetic mode corpus-grounded; scientific mode speculative pending fresh sample. 25 tests. |
| `v15/model-adjustdate` | `44b1bb0` | `adjustdate.md` | GREEN. Notable wire-format finding: dual-slot pattern (`WFDuration` abbreviated units `"min"` ↔ `WFAdjustOffsetPicker` spelled-out `"Minute"`) for Add/Subtract operations. Single-magnitude API mirrors into both slots; follow-up filed for optional `picker_value` override field. 22 tests. Doc 5/5 (best in batch). |
| `v15/doc-quality-audit-v1` | `d7fbd4a` | `doc-quality-audit-v1.md` | YELLOW→GREEN. Initial head `31239d8` had two issues: (a) DownloadURL's 4 sample citations were factually wrong (line 11 ≠ "plain GET" — it has WFHTTPHeaders; line 59 = PUT not "GET with headers"; line 92 = PATCH not "POST with JSON"; line 125 = bare POST not "POST with JSON+headers"), and (b) `body_type="Form"` guard fired late (in `_params`) instead of at construction. Both fixed inline (commit `d7fbd4a`): citations now match XML, Form guard moved to `__post_init__`, test updated to assert construction-time SchemaError. Also includes the 24 V1 leaf docstring refreshes (avg 2.8 → 5.0) and surfaces 5 undocumented quirks. Should land EARLY in merge order to set the doc-quality bar. |

### Batch 10 — number-family + location actions, post-v1.0.0-redefinition

Continued action-coverage push under the redefined v1.0.0 criterion. All three branches are corpus-grounded with explicit jellycore-null disclaimers (jellycore has no entries for any of these three identifiers) — agents now reliably avoid the math-branch confabulation pattern when explicitly briefed.

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-calculateexpression` | `97f730d` | `calculateexpression.md` | GREEN. Wire key is bare `Input` (capitalised AppIntent style — distinct from `WFInput` used by sibling `Math`). Uses `coerce_text_field` for `WFTextTokenString` envelope (variable interpolation in expression text). Required field — both corpus appearances populate it. 12 tests. Doc 5/5. Cosmetic line-citation off-by-2 (396 vs 394) flagged for follow-up. |
| `v15/model-statistics` | `1ec27bd` | `statistics.md` | GREEN. Same `Input` AppIntent convention as `calculateexpression` — independently observed by two agents on the same `dictionary.xml`, mutually corroborating. Uses `coerce_value` for `WFTextTokenAttachment` envelope (no interpolation). 9 operations Literal, "Average" default with omit-if-default. 22 tests. Doc 4/5 (operation enum honestly disclaimed as UI-derived). |
| `v15/model-getdistance` | `5a26095` | `getdistance.md` | GREEN. Wire key `WFGetDistanceDestination` (NOT `WFDestination` like sibling `gettraveltime` — guarded by explicit negative-key test). Single-field minimalist model; reviewer's position: do NOT speculatively add `WFDistanceUnit` / `WFGetDistanceMode` because Apple's key naming is inconsistent enough that wrong-key guesses silently produce malformed shortcuts. 15 tests. Doc 5/5. |

### Batch 11 — list-helper + number primitives

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-getitemfromlist` | `6d7953a` | `getitemfromlist.md` | GREEN. **Closed open `_SUMMARY.md` follow-up**: `WFItemIndex` co-exists with `WFItemSpecifier="Last Item"` in `tile_last_2_windows.xml` — Apple preserves the last-typed index regardless of active specifier. Schema emits `WFItemIndex` whenever set, unconditionally on specifier (round-trip-faithful). 5 specifiers, 20 tests. Stale "no jellycore entry" claim corrected at `6d7953a`. |
| `v15/model-number-actions` | `935dbbe` | `number-actions.md` | GREEN. Bundles `Number` + `RandomNumber`. **Discovered the jellycore-query infra bug** (`{actions: [...]}`, not a top-level map). Both actions corpus-only-default; jellycore confirms wire keys (`WFNumberActionNumber`, `WFRandomNumberMinimum/Maximum`). `Number.default_output_name` flagged as inferred (no downstream corpus reference). 19 tests. |

### Batch 12 — number formatting + TTS

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-number-formatting` | `1889e1e` | `number-formatting.md` | GREEN. Bundles `FormatNumber` + `DetectNumber`. `FormatNumber.WFNumber` (NOT `WFInput`) corpus + jellycore confirmed. `DetectNumber.WFInput`. **Style-modes gap finding**: corpus + jellycore both show only `decimal_places`, but Shortcuts.app's UI has currency/percent/scientific/spell-out — gap flagged as corpus-coverage limitation, not architectural truth (refined inline at `1889e1e`). 20 tests. |
| `v15/model-makespokenaudio` | `535b4ae` | `makespokenaudio.md` | GREEN. **Surfaced jellycore-aliasing pattern**: jellycore's `voice` (lowercase) corresponds to corpus `WFSpeakTextVoice` (wire). By analogy, `language` (lowercase in jellycore) should emit as `WFSpeakTextLanguage` (wire). Initial head `56f4001` emitted lowercase `language`; corrected to `WFSpeakTextLanguage` inline at `535b4ae` with explicit "inferred from voice precedent" disclaimer. 19 tests, iOS 15+ minimum. |

### Batch 13 — system controls + Stop and Output

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-system-controls` | `f924eff` | `system-controls.md` | GREEN. Bundles `SetDoNotDisturb` (`is.workflow.actions.dnd.set`) + `SetVolume` (`is.workflow.actions.setvolume`). **Surfaced a clean wire-format-quirks finding**: same UUID in `start_pomodoro.xml` appears in `Time` slot (`WFTextTokenString` envelope) AND `Event` slot (bare `WFTextTokenAttachment`) — proof that envelope shape is determined by slot semantics, not value type. Reviewer recommends adding to `wire-format-quirks.md` after merge. 30 tests across both classes. |
| `v15/model-output-action` | `69246d1` | `output-action.md` | GREEN. `StopAndOutput` (avoids `Output` Value class collision). `WFOutput` and `WFResponse` both `WFTextTokenString` slots. `WFNoOutputSurfaceBehavior` corpus-confirmed (jellycore's `noResultBehavior` aliases the WF-prefixed wire key, same pattern as `voice → WFSpeakTextVoice`). Build agent stopped prematurely on a false-positive infra blocker (worktree pytest claimed it couldn't import the new module — verified main thread that it works fine); files committed manually at `69246d1`. Review described the docstring as "strongest module docstring in the codebase". 10 tests. |

### Batch 14 — map family

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/model-maps` | `df7d9d7` | `maps.md` | GREEN. Bundles `SearchMaps` + `GetDirections`. **Surfaces the strongest concrete case yet for the "corpus-only key discipline"**: the four map-family actions use 3 different wire keys for conceptually the same input slot — `gettraveltime: WFDestination`, `getdistance: WFGetDistanceDestination`, `searchmaps: WFInput`, `getdirections: WFDestination`. Both jellycore-absent (verified array-select); both `WFTextTokenAttachment` envelopes. 30 tests. Reviewer recommends promoting the inconsistency table to `docs/wire-format-quirks.md`. |

### Batch 8 — SKILL companions + test discipline + tier-2 actions + a bug fix

| Branch | Latest head | Review | Verdict |
|---|---|---|---|
| `v15/skill-refresh-edit-shortcut` | `8f4c73c` | `skill-refresh-edit-shortcut.md` | GREEN with one wording nit (the setup_questions duplication is actually a silent overwrite); cross-skill style aligned with make-shortcut refresh |
| `v15/test-empty-string-coverage` | `e3421c5` | `test-empty-string-coverage.md` | GREEN. Pins 3 distinct empty-string conventions across 5 V1 actions. **Surfaced a real bug** in `UseModel.prompt=""` (asymmetric guard). Bug fixed on a parallel branch (`v15/usemodel-empty-prompt-guard`); see merge-interaction note below. |
| `v15/model-event-helpers` | `58954cc` | `event-helpers.md` | YELLOW→GREEN. Original review caught two issues; both fixed inline (commit `58954cc`): `DateAction` renamed to `GetDate` (matches schema convention of bare nouns) + `WFGetUpcomingItemCalendar` now omitted when empty (matches `dictionary.xml`'s bare sample). |
| `v15/usemodel-empty-prompt-guard` | `907d97f` | `usemodel-empty-prompt-guard.md` | GREEN. Fixes the asymmetric-guard bug surfaced by the empty-string-coverage sweep. Merge interaction: see HARD constraint below. |

The decode-shortcut SKILL was audited and confirmed accurate as-is — no branch created.

## Suggested merge order

All 31 branches are independent of each other except for these constraints:

- **HARD: `v15/v1-examples-typed-handles` must merge BEFORE `v15/skill-refresh-make-shortcut`.** The SKILL teaches the typed-handle pattern and cross-references `examples/vault_note_to_git.py`; on `main` that file uses the OLD pattern, but `v1-examples-typed-handles` migrates it. If skill-refresh merges first, the cross-reference points at code that contradicts what the SKILL teaches.
- **HARD: `v15/usemodel-empty-prompt-guard` should merge BEFORE `v15/test-empty-string-coverage`.** The latter has `test_use_model_empty_prompt_emits_empty_string` documenting the OLD (buggy) behaviour; once the guard fix lands that test fails. When merging the test-coverage branch second, drop the now-stale test (its intent is superseded by the new `test_use_model_empty_prompt_raises` from the guard-fix branch).
- **SOFT: divergent `docs/known_identifiers.md` regenerations** across batch-1 vs batch-A branches (4 with hash `1c2d9afe…`, 5 with `ea99b712…`). Resolves by merge order; not a correctness issue.

Recommended tiered order:

1. **Foundational (no deps, smallest blast radius first):**
   - `v15/fu10-downloadurl-factories`
   - `v15/fu13-textsplit-showtext`
   - `v15/wire-format-quirks-doc`
   - `v15/test-helpers-extract`
2. **Schema infrastructure:**
   - `v15/fu12-validate-workflow`
   - `v15/usemodel-empty-prompt-guard` ← **must precede `v15/test-empty-string-coverage`**
3. **Action coverage (bulk; order doesn't matter within tier):**
   - Batch 2: `v15/model-file-rename`, `v15/model-text-combine`, `v15/model-addnewreminder`
   - Batch 3: `v15/model-sendmessage`, `v15/model-previewdocument`, `v15/model-filter-calendarevents`
   - Batch 4: `v15/model-showresult`, `v15/model-choosefromlist`, `v15/model-list-helpers`, `v15/model-alert`
   - Batch 6: `v15/model-share`, `v15/model-sendemail`, `v15/model-round`, `v15/model-photo-getters`
   - Batch 7: `v15/model-gettraveltime`, `v15/model-readinglist`, `v15/model-resizewindow`
   - Batch 8: `v15/model-event-helpers`
4. **Test discipline:**
   - `v15/test-empty-string-coverage` ← gated on `v15/usemodel-empty-prompt-guard`; drop the now-stale `test_use_model_empty_prompt_emits_empty_string` test on merge
5. **Examples (after action coverage):**
   - `v15/v1-examples-typed-handles` ← **must precede the SKILL refresh**
   - `v15/note-to-github-modernize`
6. **Docs / SKILLs / discoverability (last):**
   - `v15/skill-refresh-make-shortcut` ← gated on (5) above
   - `v15/skill-refresh-edit-shortcut`
   - `v15/schema-gaps-inventory`
   - `v15/readme-release-notes`

Within each tier (excepting the HARD constraints above), merge order doesn't matter for correctness.

After merging all 31, run `prek run --all-files` and `uv run pytest -q` to confirm. Test count should land somewhere around **460+ passing** (started at 336; ~160+ new tests across action branches + envelope oracle + factory methods + Var[T] + FU-12 fixes + V1.5 polish).

## What landed without a branch (committed directly to `main`)

- **`589e500`** — gitignore `.claude/`
- **`3c6db55`** — committed the 20 public decoded sample XMLs (`samples/decoded/*.xml`); kept `samples/decoded/private/` ignored. Per deep review C: makes the 28 wire-format equivalence tests run on fresh clones instead of skipping. Test count on a clean clone now matches the development environment.
- **`f203f62`** — `docs/roadmap.md` — recorded the user's 2026-05-09 v1.0.0 criterion redefinition.
- **`d1ad7d4`** — `docs/roadmap.md` — relabel prior milestone "v0.9-equivalent" → "v0.1.0"; tag `v0.1.0` applied at this commit.

## Open V1.5 follow-ups (carried forward from reviews)

These were flagged across the reviews + deep reviews but deliberately NOT actioned in the autonomous batches. Each has a clear home (existing handoff entry or new):

- **`alert_enabled: bool` translator for `AddNewReminder`** — V1.5 polish (deep review A); convert string `"Alert"`/`"No Alert"` to a boolean Python field.
- **`Quantity`-typed field for `AddNewReminder.alert_location_radius`** — currently raw dict pass-through.
- **`content_item_filter` dict-type guard on `FilterCalendarEvents`** — two-line defensive check.
- **`properties.calendarevents` companion action** — surfaced in `dictionary.xml`; not modelled.
- ~~**`WFItemIndex` without `WFItemSpecifier` Apple quirk** on `GetItemFromList` — needs a fresh sample to confirm.~~ **CLOSED 2026-05-10** by `v15/model-getitemfromlist` (`ab0e553`): `tile_last_2_windows.xml:89-92` shows `WFItemIndex="2"` co-exists with `WFItemSpecifier="Last Item"` — Apple preserves the last-typed index regardless of which specifier is currently active. The `GetItemFromList` schema emits `WFItemIndex` whenever set, unconditionally on specifier (round-trip-faithful).
- **The 3 V1 xfails:** `RepeatCount` configured-count sample, `ChooseFromMenu` fresh sample (fixed in the V1 sweep: `TextSplit` Show-text); the first two remain.
- **TextCombine cross-field check** moved from `_params` to `__post_init__` (pattern-outliers cleanup, deep review A).
- **Three actions missing `__post_init__`** (deep review A; identify which during cleanup).
- **Skill refresh:** `make-shortcut/SKILL.md` should show `s.set` typed handles, `ask_text_on_import`, and factory methods. `edit-shortcut/SKILL.md` doesn't mention `Shortcut.from_file` or `_extra` round-trip.
- **`docs/handoff.md`** needs status-flips for closed FUs after each batch merges (FU-10 done, FU-12 done, FU-9 done, FU-13 done).
- **Doc sweep checklist post-V1.5-merge** (deep review C): ~15 docs need updates.
- **Schema-gaps Batch B onwards** (per `docs/schema-gaps.md`): list/selection actions beyond what was modelled here, then filter family (V2), then surface integrations.
- **More tier-2 action models:** `share` (3), `sendemail` (3), `gettraveltime` (3), `getlastphoto`/`getlastscreenshot` (3 each), `round` (3), etc.

## Infra finding — jellycore_facts.json query shape

Discovered on 2026-05-10 (during `v15/model-number-actions` review): the agent prompt template I used for batches 9–11 instructed sub-agents to verify jellycore entries with `jq '.["is.workflow.actions.X"]'`. **This silently returned `null` for every action** — the file structure is `{"actions": [...288 entries], "structural_identifiers": [...]}`, not a top-level map keyed by identifier. Correct query: `jq '.actions[] | select(.identifier == "is.workflow.actions.X")'`.

Effect on prior batches:

- **`v15/model-math`** — over-disclaimed; jellycore confirms `scientific` as a parameter key. **Fixed inline at `d9d43c7`** (refined "Source confidence" block in docstring).
- **`v15/model-statistics`** — jellycore says `parameter_keys: ["Input", "operation"]`. Branch uses `WFStatisticsOperation`. Corpus exercises only the default ("Average"), so neither name is observable. **Real risk**: branch may be guessing wrong wire key. **Filed as follow-up**: needs a non-default-operation sample to disambiguate. If `operation` (lowercase) is correct, this is the same AppIntent convention seen on `Input`. Until then, the branch ships with the corpus-imitating speculation; document the uncertainty in the docstring before merge.
- **`v15/model-adjustdate`** — jellycore says `["operation", "WFDuration", "WFDate"]`. Branch uses `WFAdjustOperation` (matches corpus). The lowercase `operation` in jellycore is the AppIntent abstraction-layer name, not the wire key. **No bug.**
- **`v15/model-getitemfromlist`** — jellycore says `["WFInput", "type", "WFItemIndex", "WFItemRangeStart", "WFItemRangeEnd"]`. Branch uses `WFItemSpecifier` (matches corpus). Same pattern as adjustdate — `type` is AppIntent abstraction; corpus is the wire-format ground truth. **No bug.**
- **`v15/model-list`** — jellycore says `["WFItems"]`. Branch uses `WFItems` (matches). **No bug.**
- **`v15/model-calculateexpression`** — jellycore says `["Input"]`. Branch uses `Input` (matches). **No bug.**
- **`v15/model-getdistance`** — genuinely absent from jellycore. Original "null" claim was correct.

Memory entry saved: `feedback_jellycore_query_shape.md`. All future agent prompts use the array-select form.

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
