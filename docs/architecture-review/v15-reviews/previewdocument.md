# Review: v15/model-previewdocument

**Action:** `is.workflow.actions.previewdocument`
**Reviewer:** automated (Claude Sonnet 4.6)
**Date:** 2026-05-09
**Head:** afb0f68

---

## 1. Verdict

LGTM. Correct, minimal, and well-tested. No issues found.

---

## 2. Test result

7/7 passed in 0.18 s.

```
PASSED test_preview_document_default
PASSED test_preview_document_string_input
PASSED test_preview_document_action_input
PASSED test_preview_document_output_reference
PASSED test_preview_document_registered
PASSED test_preview_document_default_output_name
PASSED test_preview_document_wire_format
```

`pre-commit` binary is not installed in the worktree environment. Ruff check and format-check were run directly (`uv run ruff check` / `uv run ruff format --check`) — both clean for the new files. The one ruff error reported (`sim210` in an unrelated file, `get_text.py`) is pre-existing and not introduced by this branch.

---

## 3. Sample grounding

All 4 corpus appearances were inspected in full:

| Sample file | WFInput present | Additional params |
|---|---|---|
| `turn_text_into_audio.xml` | Yes — `WFTextTokenAttachment` ("Spoken Audio") | None |
| `daily_standup.xml` | Yes — `WFTextTokenAttachment` ("Text") | None |
| `combine_screenshots_and_share.xml` | Yes — `WFTextTokenAttachment` ("Combined Image") | None |
| `dictionary.xml` | Yes — `WFTextTokenAttachment` ("Renamed Item") | None |

The agent's claim is confirmed: every appearance has exactly one param (`WFInput`) and nothing else. No hidden toggles, no `WFShowFullPreview` or similar flags.

Notably, all 4 appearances use the `WFTextTokenAttachment` / `ActionOutput` envelope — no bare string or clipboard-implicit variant is present in the corpus. The schema correctly handles both forms (the string case is synthetic but valid given how `coerce_value` works), and the no-input default (omit `WFInput`) is a sensible extension even without a direct sample, since Quick Look is defined to preview the shortcut's current input when none is specified.

---

## 4. Issues

None.

The implementation is as simple as it should be for a single-parameter action:

- `_params()` uses the idiomatic `if self.input is not None` guard — `WFInput` is correctly omitted when `None`.
- `@register @dataclass` ordering is correct and consistent with the rest of the codebase.
- `ClassVar` annotations for `identifier` and `default_output_name` are correct.
- Docstring follows Google style; imperative summary under 72 chars; `Args` block present.
- Test file imports are clean; `_normalise` and UUID-stripping helpers are sound and consistent with other action test files.

---

## 5. Merge recommendation

**Merge as-is.** No changes required.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `afb0f68` (matches _SUMMARY.md record `afb0f68`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: automatic merge succeeded with no conflicts; branch adds only two new files (`src/shortcut_lib/schema/actions/preview_document.py`, `tests/test_action_preview_document.py`) which have no overlap with any main advancement.

**Pytest on merged state:** 338 passing, 0 failing (6 skipped, 3 xfailed). One transient failure (`test_signs_to_disk`) appeared on the first run but passed when run in isolation and on two subsequent full-suite runs — pre-existing flaky test unrelated to this branch.

**prek:** skipped (pre-commit binary not installed in worktree; ruff check/format previously confirmed clean on initial review)

**Drift / observations:**
- Main has advanced 27 commits since branch cut, adding 30+ review files, new sample XMLs, and test infrastructure (`test_wire_format_equivalence.py`). None conflict with this branch's additions.
- The `docs/architecture-review/v15-reviews/` directory did not exist in the worktree (branch predates it); the review file was carried forward from main for this pass.
- No sibling actions on main contradict the wire-key (`WFInput`) or envelope (`WFTextTokenAttachment` via `coerce_value`) choices made here.
- New `test_wire_format_equivalence.py` from main runs cleanly against the merged state; `previewdocument` is not in its parametrize list (it uses a dedicated test file instead), no gap.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
