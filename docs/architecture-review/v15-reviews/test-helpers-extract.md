# Review: v15/test-helpers-extract

**Date:** 2026-05-10
**Reviewer:** sonnet sub-agent (merge-readiness pass)
**Branch HEAD:** `f116673`

## Summary

Refactoring-only branch. Extracts the wire-format normalisation helpers that
lived inline in `tests/test_wire_format_equivalence.py` into a new shared
module `tests/_wire_helpers.py`. No action schema changes. No new tests. The
existing wire-equivalence tests are updated to import from the shared module
instead of using the local copies.

**Files changed (3):**

- `tests/_wire_helpers.py` — new module (192 lines); contains `load_sample`,
  `find_action`, `strip_output_uuids`, `normalise_action`,
  `normalise_sequence`, `find_action_sequence`.
- `tests/test_wire_format_equivalence.py` — ~83 lines shorter; helpers
  removed, replaced by imports from `_wire_helpers`.
- `docs/known_identifiers.md` — regenerated; corpus histogram reflects a
  different sample set (voice_note_to_github removed, intelly added).

## Observations

**Extraction fidelity:** All six helper functions are byte-for-byte equivalent
to the original inline versions (verified by diff). No behaviour change.
`normalise_sequence` docstring improved in the shared module (adds
`CustomOutputName` to the listed stripped keys, which was omitted in the old
inline version — the code already stripped it; the doc is now accurate).

**Import style:** `test_wire_format_equivalence.py` now uses one-name-per-import
`from _wire_helpers import (name) as _name` blocks — slightly verbose but
passes ruff lint and ty checks. No functional concern.

**Test path:** `tests/` has no `__init__.py`; pytest's default rootdir-based
path includes `tests/` in `sys.path`, so `from _wire_helpers import ...`
resolves correctly. Confirmed by test run.

**`docs/known_identifiers.md` change:** The histogram on this branch reflects a
different corpus set than `main` (voice_note_to_github sample removed,
intelly sample added — counts for several identifiers differ). This file is
regenerated deterministically from whatever samples are on disk; the branch's
version should be accepted on merge only if the sample set it reflects is
intentional. The brief notes it is safe to restore `main`'s version here
(regen is deterministic post-merge). This conflict resolves trivially.

**Forward-looking note (per brief):** Once the 16 V1.5 action branches merge,
any of their `test_action_*.py` files that needed normalisation helpers can
import from `_wire_helpers` rather than copying helpers. None of the V1.5
branches currently reference `_wire_helpers` — they were created before this
branch and independently don't use the helpers (they test schema construction,
not corpus equivalence). The benefit is purely prospective for future
corpus-equivalence test files.

**Not in scope:** This branch deliberately makes no schema changes, no envelope
changes, no new action coverage. Source-confidence ladder doesn't apply here.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `f116673` (diverges from _SUMMARY.md record — branch is not
listed in _SUMMARY.md; it is a deep-review-A-driven follow-up that post-dates
that document)

**Merge against main:**
- Result: clean
- Conflict files: none (`docs/known_identifiers.md` merged automatically with
  no conflicts — the branch changes are line-order/count adjustments only;
  git resolved them cleanly)
- Resolution: no manual intervention needed

**Pytest on merged state:** 330 passed, 6 skipped, 3 xfailed, 8 warnings in
14.12s

**prek:** green (trim whitespace, ruff lint, ruff format, ty all passed)

**Drift / observations:**
- No action schema files touched; no drift risk on wire-key or envelope
  conventions.
- `docs/known_identifiers.md` differs from `main`'s version (corpus sample
  set diverged — voice_note_to_github out, intelly in). This is a benign
  regen difference; main's version is canonical and will be regenerated
  correctly post-merge. Not a blocking concern.
- The extracted helpers in `_wire_helpers.py` are faithfully equivalent to the
  inline originals; `normalise_sequence` docstring gained accuracy (now lists
  `CustomOutputName` as a stripped key, matching what the code actually does).
- No per-action test files on the V1.5 branches currently reference
  `_wire_helpers` — the prospective benefit is for future corpus-equivalence
  tests, not for unblocking any existing branch.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
