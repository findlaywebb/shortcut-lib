# Review: v15/model-share

**Branch:** `v15/model-share` (head `9af2dd3`)
**Reviewer:** automated review, 2026-05-09
**Scope:** `src/shortcut_lib/schema/actions/share.py` + `tests/test_action_share.py` (271 lines added, 2 files)

---

## 1. Verdict

Clean, minimal, correct. The implementation matches corpus evidence exactly and
introduces no over-engineering. The `VariableUUID` strip question is the only
non-trivial design point (addressed below). Ready to merge as-is.

---

## 2. Test results

All 10 share tests pass on the branch:

```
10 passed in 0.08s
```

**Comment-test status.** `test_comment_wire_format` also fails on `main`:

```
FAILED tests/test_wire_format_equivalence.py::test_comment_wire_format - AssertionError
1 failed in 0.11s
```

This is a pre-existing failure on `main` (unicode curly-quote mismatch in
Comment text). The branch neither introduces nor repairs it — it is `main`'s
responsibility.

**Linting.** `ruff check` on the two new files is clean. The one ruff error
reported project-wide (`default if default else None` → `or` operator in an
unrelated file) pre-exists on `main`; this branch does not touch it.

---

## 3. What landed

`Share` is a two-method dataclass (`_params` + inherited `to_action_dict`).
Key design choices:

- **Single param `input: ParamValue = None`.** When `None`, `WFInput` is
  omitted entirely, which is correct — an absent `WFInput` means "share
  whatever is in the pipeline". This matches all three corpus samples.
- **No `default_output_name`.** The action produces no chainable output, so
  the attribute is `""` (the `Action` base default). This is the right call;
  sharing to the sheet terminates the pipeline for output purposes.
- **Identifier `is.workflow.actions.share`.** Confirmed against all three
  corpus files.
- **`coerce_value` delegation.** The implementation correctly delegates to
  `coerce_value` rather than hand-rolling envelope construction, consistent
  with every other action in the schema.

Wire-format tests cover both reference types observed in corpus: `ActionOutput`
(`daily_standup.xml`, index 37) and named-variable (`combine_screenshots_and_share.xml`). The third sample (`dictionary.xml`) is documented in the
class docstring but not given a separate wire test — acceptable, as its shape
is identical to `daily_standup` (`ActionOutput` with `OutputUUID` stripped).

---

## 4. The `VariableUUID` strip — should it go to `_wire_helpers.py`?

Yes, but not yet.

`VariableUUID` is an author-time key emitted by Shortcuts for named-variable
references; `NamedVar` intentionally omits it. The current test adds
`VariableUUID` to the `_strip_ref_uuids` helper inside
`tests/test_action_share.py`. This is the right behaviour — it is not a
one-off artefact of this sample, it will recur in any test that normalises a
`NamedVar` reference drawn from a corpus file.

`_wire_helpers.py` does not yet exist on `main`; it is being introduced on the
parallel branch `v15/test-helpers-extract`. The correct resolution is:

1. Keep the local `_strip_ref_uuids` (plus `_load`, `_find_action`,
   `_normalise`) in `test_action_share.py` for now.
2. When `v15/test-helpers-extract` is merged, migrate the shared helpers
   (including `VariableUUID` stripping) to `_wire_helpers.py` and update
   `test_action_share.py` to import from there.

The branch author's decision to **not** pre-emptively import from a
not-yet-merged module is correct. No action required before merge.

---

## 5. Issues

None blocking. One minor observation:

**`dictionary.xml` wire test is absent.** The docstring mentions three samples
but only two have explicit wire tests. The `dictionary.xml` case is structurally
identical to `daily_standup` (both are `ActionOutput` references) so coverage
is not materially weakened. A third wire test would be redundant. Fine to leave
as-is, or add as a follow-up if the pattern is to cover every sample.

No conflation with related identifiers. A corpus-wide grep confirms the only
appearances of `is.workflow.actions.share` (exact) are the 3 counted in the
inventory. Variants such as `is.workflow.actions.sharedshortcut` do not appear
in the corpus at all and are not referenced by this branch.

---

## 6. Merge recommendation

**Merge.** No changes required. The `VariableUUID` question should be tracked
as a follow-up cleanup against `v15/test-helpers-extract` when that branch
lands, not held against this one.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `9af2dd3` (matches _SUMMARY.md record `9af2dd3`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts. Main had added the `share.md` review file and other batch review files, all cleanly merged with the branch's new `share.py` and `test_action_share.py`.

**Pytest on merged state:** 341 passing, 0 failing (6 skipped, 3 xfailed)

**prek:** green

**Drift / observations:**
- The `share.md` review file already existed on `main` (added by a prior review agent); the merge brought it in cleanly alongside the branch's new schema/test files.
- `_SUMMARY.md` on `main` records HEAD `9af2dd3` for this branch — exact match, no drift.
- `coerce_value` delegation pattern is consistent with all sibling actions on `main`; no contradictions observed.
- The pre-existing `test_comment_wire_format` failure noted in the original review is no longer present in the merged state — that issue has been resolved on `main` in the 19 commits since the branch was cut.
- `v15/test-helpers-extract` branch referenced in section 4 is not yet merged to `main`; the deferred `_wire_helpers.py` migration noted in the original review remains a valid follow-up.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
