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
