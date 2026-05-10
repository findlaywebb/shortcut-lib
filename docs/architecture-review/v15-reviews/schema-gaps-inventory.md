# Review: `v15/schema-gaps-inventory` — Schema Gaps Inventory

**Branch:** `v15/schema-gaps-inventory` (head: 63fca34)
**Date:** 2026-05-09
**Reviewer:** agent (automated)
**Verdict:** GREEN — merge as-is, add a short postscript noting V1.5 progress

---

## 1. Verdict

The document is accurate, well-structured, and immediately actionable.
All spot-checks pass. The one known staleness (four actions now modelled on
parallel V1.5 branches) is minor, expected, and the user is already aware.
Merge and add a one-paragraph postscript.

---

## 2. What Landed

A single new file: `docs/schema-gaps.md` (439 lines).

Seven sections as specified:
- Snapshot with tier breakdown
- Tier-1 (6 actions, 4+ appearances) — fully detailed entries
- Tier-2 (partial inline list + truncation note pointing to data file)
- Tier-3 (cluster table, 274 singletons)
- Currently Modelled cross-reference
- Recommended Next Batches (Batches A–G, plus filter-predicate deferral)
- Out-of-Scope Flags

All previous v15-review files were cleaned off the branch in the same
commit, so the diff is a net deletion of ~960 lines offset by +439.

---

## 3. Accuracy / Freshness Assessment

**Snapshot numbers — PASS.**
The doc claims 393 distinct identifiers, 29 modelled (24 leaf + 5
control-flow), 364 unmodelled. `list_actions()` on `main` returns exactly
24 leaf entries; the five control-flow constructs are listed explicitly in
Section 5. The 393 / 364 split is consistent and matches the V1 closeout
figure. No arithmetic errors.

**Tier-1 spot-checks — PASS.**
- `is.workflow.actions.sendmessage` (corpus count 5): present in Tier-1,
  line 75. ✓
- `is.workflow.actions.filter.calendarevents` (corpus count 4): present in
  Tier-1, line 104, correctly flagged as high complexity and deferred to V2
  predicate infrastructure. ✓
- Six Tier-1 entries total: `file.rename` (7), `addnewreminder` (5),
  `text.combine` (5), `sendmessage` (5), `previewdocument` (4),
  `filter.calendarevents` (4). All six are present.

**Currently Modelled cross-reference — PASS.**
Section 5 lists exactly 24 leaf actions and 5 control-flow constructs, in
alphabetical order. Spot-checked against `list_actions()` output: every
identifier in the registry appears in the doc and vice versa. No
omissions, no phantom entries.

**Staleness vs parallel V1.5 work — ACKNOWLEDGED BUT NOT FLAGGED IN DOC.**
The doc was authored against `main` and has no "as-of" commit hash, only a
generation date (`2026-05-09`). It does not mention that `file.rename`,
`text.combine`, `addnewreminder`, and `previewdocument` — all listed in
Batch A and Batch D as "model next" — are already modelled on parallel
branches (`v15/model-file-rename`, `v15/model-text-combine`,
`v15/model-addnewreminder`, `v15/model-previewdocument`). This is expected:
the agent couldn't have known about work on sibling branches. The user is
aware. See merge recommendation for the fix.

---

## 4. Usefulness for the User's Next-Batch Decision

**High.** Once the four V1.5 parallel actions are merged, Batch A is
complete and the user can move directly to Batch B (list/selection actions:
`list`, `choosefromlist`, `getitemfromlist`, `count`) without any
re-analysis. The rationale sections are concise and grounded — each batch
cites the specific envelope types, Literal fields, and any infrastructure
preconditions. The filter-predicate deferral (Batches A–G all skip
`filter.*`, Section 7 explains why) is the right call and saves the user
from discovering the predicate-dict problem piecemeal.

The Tier-2 truncation (the inline list covers ~40 priority entries; the
rest are noted as catalogued in `data/observed_envelope_types.json`) is
appropriate — the full 84-entry list would have been noise at this stage.

---

## 5. Issues

**Minor — no commit hash anchor.**
The header says `_Generated 2026-05-09 against 20 decoded corpus samples_`
but does not record the `main` commit it was built from. When the parallel
branches merge, Section 5 and the tier counts will silently become stale.
A one-line `> Built from main @ <hash>` note would make future freshness
checks trivial. Not a blocker; fix in the postscript.

**Tier-2 count claim — unverified but plausible.**
The snapshot claims 84 Tier-2 identifiers (2-3 appearances). The inline
list in Section 3 covers roughly 35 entries before the truncation note.
The remaining ~40 are deferred to `data/observed_envelope_types.json`.
This review does not independently recount the corpus; the figure is
internally consistent (6 + 84 + 274 = 364 = 393 − 29) so any error would
be a miscategorisation rather than an arithmetic mistake.

**No issues blocking merge.**

---

## 6. Merge Recommendation

**Merge as-is.** The document is accurate against `main` at time of
authoring and immediately useful.

After merging, add a short postscript to `docs/schema-gaps.md`:

> **V1.5 progress note (added post-merge):** `file.rename`, `text.combine`,
> `addnewreminder`, and `previewdocument` — listed above in Batch A and
> Batch D — are modelled on parallel branches pending review. Once those
> land, Batch A is complete; start at **Batch B** for the next sprint.
> Main at merge: `<hash>`.

This keeps the inventory useful for the next reading without requiring a
full regeneration pass.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `25915ba` (matches _SUMMARY.md record `25915ba`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: No conflicts. `docs/known_identifiers.md` diverged between branch and main (branch omits `voice_note_to_github` corpus entries; main has the newer regenerated version), but git auto-merged without conflict — main's version will take precedence at actual merge, which is correct per the brief's soft-conflict guidance.

**Pytest on merged state:** 330 passed, 6 skipped, 3 xfailed, 8 warnings

**prek:** skipped — `pre-commit` not installed in worktree venv

**Drift / observations:**
- `docs/schema-gaps.md` does not exist on main; this branch is the sole source. No drift concern.
- Main has advanced significantly (27 commits ahead): parallel action branches for `file.rename`, `text.combine`, `addnewreminder`, `previewdocument`, and many others have now merged. Section 5 of `schema-gaps.md` (24 leaf actions / 5 control-flow) will be stale post-merge, but the existing review already noted this and recommended a postscript fix. No action needed before merge.
- `list_actions()` on branch HEAD returns 24 leaf identifiers — consistent with what `schema-gaps.md` Section 5 claims (built from pre-V1.5-merge main). Expected drift, not a correctness error.
- The doc header already carries a freshness anchor (`main @ 422c520...`) added in commit `25915ba`, addressing the issue flagged in the original review Section 5.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
