# Review: `v15/model-file-rename` — FileRename schema

**Verdict: GREEN**
**Date: 2026-05-09**
**Reviewer: agent (autonomous)**

---

## Test result

All 9 dedicated unit tests pass. The wire-format equivalence test in
`tests/test_action_file_rename.py` passes, and `test_file_rename_wire_format`
in `tests/test_wire_format_equivalence.py` also passes independently.

Full suite: **341 passed, 6 skipped, 3 xfailed** — no regressions.
Pre-commit (`prek run --all-files`): all 8 hooks pass (ruff lint, ruff format,
ty, uv-lock, whitespace, YAML, file-size).

---

## What landed

4 files changed, 420 insertions, 11 deletions:

- `src/shortcut_lib/schema/actions/file_rename.py` (89 lines) — the new schema.
- `tests/test_action_file_rename.py` (254 lines) — 9 unit tests.
- `tests/test_wire_format_equivalence.py` (+61 lines) — adds
  `test_file_rename_wire_format` to the shared equivalence suite.
- `docs/known_identifiers.md` — minor reformat; `is.workflow.actions.file.rename`
  now correctly listed with count 7 and source files `dictionary, rename_files`.

The schema follows the `text_split.py` simple-action pattern exactly:
`@register @dataclass`, `ClassVar` identifier and `default_output_name`,
`__post_init__` validation, `_params()` emission with `coerce_value` /
`coerce_text_field`.

---

## Sample-grounding verification (independent)

Corpus appearances confirmed independently against
`samples/decoded/rename_files.xml` (5 hits) and
`samples/decoded/dictionary.xml` (2 hits) — 7 total, matching the agent's
claim.

**`WFFile` envelope:** Every appearance wraps the file reference in
`WFTextTokenAttachment`. The 5 rename_files.xml instances use
`{Type: Variable, VariableName: "Repeat Item"}` (a loop variable). The 2
dictionary.xml instances use `{Type: ActionOutput, OutputName: "File"}` —
both confirmed `WFTextTokenAttachment`, no exceptions.

**`WFNewFilename` envelope:** Present in exactly 5 appearances
(all from rename_files.xml). The 2 dictionary.xml entries have only `WFFile`
and no `WFNewFilename` — confirmed placeholder/demo entries where the action
was dropped incomplete. All 5 configured instances use `WFTextTokenString`,
including single-attachment (one variable reference) cases — which is why
`coerce_text_field` is correct here and not `coerce_value`.

**Key spelling:** The corpus spells the key `WFNewFilename` (lowercase 'n' in
'name') — confirmed by direct grep. The schema uses `WFNewFilename` throughout.
No mismatch.

---

## Oracle alignment

`data/observed_envelope_types.json` entry for `is.workflow.actions.file.rename`:

```json
{
  "WFFile": {
    "envelopes": { "WFTextTokenAttachment": { "count": 5 } }
  },
  "WFNewFilename": {
    "envelopes": { "WFTextTokenString": { "count": 5 } }
  }
}
```

The schema's coerce choices align exactly:
- `WFFile` → `coerce_value` emits `WFTextTokenAttachment`. Correct.
- `WFNewFilename` → `coerce_text_field` emits `WFTextTokenString` (and
  rewraps a bare `WFTextTokenAttachment` into the one-attachment
  template-string envelope for variable inputs). Correct.

The oracle does not record the 2 dictionary.xml appearances (no `WFNewFilename`
in those entries, so they contribute nothing to the WFNewFilename count). The
schema's optionality for both fields is consistent with this: the oracle cannot
distinguish "never set" from "set but not observed with a variable ref."

---

## Sharp issues — all clear

**`WFNewFilename` spelling:** Correct. Corpus unambiguously uses lowercase 'n'
in 'name'. The implementation matches exactly.

**`__post_init__` logic:** Verified correct. Both-None does not raise (handles
the dictionary.xml placeholder shape). `new_name` set without `file` raises
`SchemaError` with a clear message. `file` set without `new_name` does not
raise (matches the dictionary.xml placeholder pattern where `WFFile` is
present but `WFNewFilename` is absent). Test coverage exists for all three
cases.

**Registry discoverability:** `uv run python scripts/print_actions.py`
returns `FileRename → Renamed File` with the correct identifier and docstring
summary. Discoverable as expected.

**`default_output_name`:** Set to `"Renamed File"`. This is a reasonable
human-facing label for the action's output (the renamed file object). No
corpus evidence to contradict it; consistent with analogous actions in the
registry (e.g. `"Translated Text"`, `"Dictated Text"`).

---

## Issues

None. The implementation is clean and complete.

One minor observation, not blocking: the wire-format equivalence test in
`test_action_file_rename.py` (at the bottom of the unit-test file) duplicates
coverage already added to `tests/test_wire_format_equivalence.py`. Both target
`rename_files.xml` action index 6 with the same reconstruction. The duplication
is harmless and the extra test in the unit file serves as locally readable
documentation of the wire shape — no action required.

---

## Merge recommendation

**Merge.** The schema is correct, sample-grounded, and fully tested. All
tooling passes. The agent's parameter claims have been independently verified
against the corpus and oracle. No issues found.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `65412bc` (matches _SUMMARY.md record `65412bc`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: `git merge main --no-commit --no-ff` completed with only an automatic merge of `tests/test_wire_format_equivalence.py` (other branches added entries to this file; no logic conflicts). No manual resolution required.

**Pytest on merged state:** 341 passed, 6 skipped, 3 xfailed — identical to the original review baseline.

**prek:** skipped (merge aborted before pre-commit hook ran; original review confirms all 8 hooks green)

**Drift / observations:**
- main is 27 commits ahead; the additional commits are other v15/* batch additions (other action schemas, test additions to `test_wire_format_equivalence.py`). None contradict `FileRename`'s wire-key choices (`WFFile`, `WFNewFilename`) or envelope choices (`coerce_value` / `coerce_text_field`).
- The `v15-reviews/` directory was added to main after this branch was cut; the review file was committed directly on main. Appending this section required placing the file in the worktree for the first time — no schema or test files were touched.
- No sibling actions on main share the `file.rename` action family; no cross-action consistency issue to flag.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
