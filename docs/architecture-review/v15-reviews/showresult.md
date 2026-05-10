# Review: `v15/model-showresult` — ShowResult action schema

**Branch:** `v15/model-showresult` (head: ddc52b6)
**Files changed:** `src/shortcut_lib/schema/actions/show_result.py` (+40), `tests/test_action_show_result.py` (+196)
**Verdict:** APPROVE — correct, well-tested, sample-grounded.

---

## What landed

A typed `ShowResult` dataclass for `is.workflow.actions.showresult`. Single public
field: `text: ParamValue = None`. Serialisation is handled by `_params()`, which calls
`coerce_text_field` when `text` is not `None` and non-empty, writing the result under
the wire key `Text`. The action is registered via `@register` and is discoverable
through `lookup("is.workflow.actions.showresult")`.

---

## Corpus grounding

Both corpus appearances are confirmed and correctly indexed:

- **`dictionary.xml`, action index 1** — bare `<dict/>` params (no `Text` key). Apple
  emits this form when the action displays the implicit pipeline input. The schema
  matches by omitting `Text` when `text is None`.
- **`start_pomodoro.xml`, action index 10** — `Text` contains a `WFTextTokenString`
  envelope with one attachment at range `{20, 1}` referencing `OutputName "Break
  Length"` / `Type "ActionOutput"`. The wire-format test reconstructs this exactly,
  using the corpus UUID (`E27FB393-66E9-441D-A088-5B0674806611`) and the full sentence
  string (including the `￼` object-replacement character at position 20).

---

## Verification checklist

| Check | Result |
|---|---|
| Both corpus appearances confirmed | Yes — `dictionary.xml` index 1, `start_pomodoro.xml` index 10 |
| Wire key is `Text` (capital T, no `WF` prefix) | Confirmed by corpus; see note below |
| Field omitted when `None` | Yes — `test_show_result_no_text_emits_empty_params` and wire-format test against `dictionary.xml` |
| Empty string omits key | Yes — `test_show_result_empty_string_omits_key` covers this edge case |
| `coerce_text_field` routing for templated case | Yes — `test_show_result_text_template` and `test_show_result_output_reference_wraps_as_token_string` confirm `WFSerializationType: WFTextTokenString` envelope |
| All 9 tests pass | 9/9 in 0.17 s |
| Pre-commit clean | All 8 hooks pass (ruff lint, ruff format, ty, uv-lock, etc.) |

---

## Note on the `Text` wire key

The wire key `Text` (capitalised, no `WF` prefix) is genuinely unusual. Across the
existing action models in this repo, action-parameter keys are almost universally
prefixed `WF` (e.g. `WFInput`, `WFLLMPrompt`, `WFHTTPMethod`). The handful of
unprefixed keys found elsewhere (`audioFile`, `separator`, `summaryType`) are all
camelCase or lowercase — not Title-Case. The only other `Text` keys that appear in the
decoded corpus are inside `WFWorkflowImportQuestions` metadata dicts, which are
completely separate from action params. Apple therefore made a deliberate exception for
`showresult`: the param key is just `Text`, not `WFText` or `WFResultText`. The agent
correctly identifies this from the corpus rather than guessing, the schema uses the
literal corpus key, and the wire-format equivalence test locks it down — so there is no
risk of drift. If future corpus additions reveal a `WFText` variant (e.g. in a newer OS
version), the test would catch it immediately.

---

## Minor observations (non-blocking)

- The docstring covers `None` semantics clearly, tying the "empty params" behaviour
  back to Apple's `<dict/>` wire form. Good.
- `test_show_result_none_omits_text_key` duplicates `test_show_result_no_text_emits_empty_params`
  (both test `text=None` → no `Text` key). The explicit redundancy is acceptable given
  how small this action is, but could be collapsed into a parametrised test if
  consistency with the broader test suite matters.
- No `from_action_dict` / round-trip parsing exists, consistent with the rest of the
  v15 series.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `ddc52b6` (matches _SUMMARY.md record `ddc52b6`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts; 26 commits on main added new samples, review files, and schema modules that are orthogonal to ShowResult.

**Pytest on merged state:** 340 passed, 6 skipped, 3 xfailed in 11.34s

**prek:** green (all 8 hooks: trim whitespace, fix end of files, check yaml, check for added large files, ruff lint, ruff format, uv-lock, ty)

**Drift / observations:**
- Main has advanced 26 commits (new corpus samples, additional action schemas, deep-review docs). None touch `showresult` or the `Text` wire-key convention.
- The `docs/known_identifiers.md` file had an unstaged regeneration in the worktree (corpus counts updated); restored to HEAD before merge attempt — this is the expected soft-conflict pattern noted in the brief, and it will re-emit correctly post-merge.
- No sibling actions on main use a Title-Case unprefixed wire key; the `Text` key remains the sole documented exception, correctly grounded in corpus and locked down by the wire-format equivalence test.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
