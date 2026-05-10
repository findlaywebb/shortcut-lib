# v15/v1-examples-typed-handles — review

**Branch origin:** Deep-review Section C (C-examples-and-docs.md) finding F4.
**What it does:** Migrates the four V1 examples (`share_to_inbox.py`,
`spotlight_quick_task.py`, `vault_note_to_git.py`, `voice_note_to_git.py`)
from the discarded-return `s.set("X", value)` + `NamedVar("X")` pattern to
captured typed handles: `x = s.set("X", value)` with `x` referenced
downstream. Eliminates 40 `NamedVar` string-refs across the four files.
Helpers that previously returned `None` now return typed handles (single
`NamedVar` or tuples of `NamedVar`).

**No new action schemas, no test changes.** This is a pure example-quality
improvement.

**Coupling:** `v15/skill-refresh-make-shortcut` cross-references
`examples/vault_note_to_git.py` and depends on this branch's typed-handle
pattern. Hard merge order: this branch must merge before the skill refresh.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `6750f0f` (matches _SUMMARY.md record — this branch was not
in the autonomous-batch summary; it was created as a deep-review-C follow-up
with HEAD recorded in the task brief as `6750f0f`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: `git merge main --no-commit --no-ff` produced no conflicts;
  `docs/known_identifiers.md` was not modified by this branch so the soft
  conflict noted in the brief did not arise.

**Pytest on merged state:** 330 passed, 6 skipped, 3 xfailed

**prek:** green (ruff lint, ruff format, ty, uv-lock all passed)

**Drift / observations:**
- The four example files are the only files changed on this branch. No schema
  or test files were touched. Zero risk of cross-branch schema drift.
- Residual `NamedVar` string references in `share_to_inbox.py`
  (`_url_branch_body`, `_text_branch_body`) and `voice_note_to_git.py`
  (`_add_metadata_gate` branch bodies) are correctly documented as
  intentional: branch body actions are constructed outside `s.set()` inside
  `If` / `ChooseFromMenu` constructs, so typed handles from the outer scope
  are not available at the call site. `_add_branch` in `share_to_inbox.py`
  returns `NamedVar("Body")` — also correct and documented.
- `SetVariable` import is retained in `share_to_inbox.py` (used by the branch
  body helpers at lines 138, 166) and `voice_note_to_git.py` (used inside
  `ChooseFromMenu` branch lists at lines 119, 125). Correctly removed from
  `vault_note_to_git.py` and never present in `spotlight_quick_task.py`.
- Branch brings no changes to `docs/known_identifiers.md`, README, or any
  doc file — consistent with its narrow scope.
- Pytest on branch-only state before merge: 311 passed, 28 skipped (the 28
  skips are sample-gated wire-format equivalence tests; this is the expected
  baseline per deep-review Section C).
- Merge adds ~19 tests from main's batch branches (330 total vs 311
  branch-only), confirming integration is clean.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none — this is a structural quality improvement with no schema risk.
  Typed-handle pattern is identical to that established in
  `examples/note_to_github.py` (already on main). Merge safe.
