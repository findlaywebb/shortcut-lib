# Review: `v15/usemodel-empty-prompt-guard`

**Head:** `907d97f`
**Reviewer:** Claude (automated, on behalf of user)
**Date:** 2026-05-09

---

## 1. Verdict

**Approve — ready to merge.** The fix is correct, minimal, and well-tested. All 12 tests pass, pre-commit is clean, and the guard change has no unintended side effects on valid prompt types.

---

## 2. Test Result

```
12 passed in 0.04s
```

All pre-existing tests pass. The two directly relevant tests:

- `test_use_model_requires_prompt` — updated regex now matches `"non-empty"` in the new error message. Passes.
- `test_use_model_empty_prompt_raises` — new test; asserts `UseModel(prompt="").to_action_dict()` raises `SchemaError` matching `"non-empty"`. Passes.

Pre-commit (`prek run --all-files`): all hooks pass — ruff lint, ruff format, ty, uv-lock, yaml, whitespace.

---

## 3. The Fix — Guard Correctness and Action-Truthy Verification

**Old guard:**

```python
if self.prompt is None:
    raise SchemaError("UseModel requires `prompt`.")
```

**New guard:**

```python
if not self.prompt:
    raise SchemaError(
        "UseModel requires a non-empty `prompt`. "
        "Pass a string, Text template, or Output reference."
    )
```

`if not self.prompt` correctly catches:

- `None` (the default, previously caught)
- `""` (empty string, previously silently passed through)
- Any other falsy value (e.g. `0`, `[]`) that would be a programming error at the call site

**Action-typed prompts remain unaffected.** Verified by live execution:

```
NamedVar truthy: True
Text truthy:     True
```

Both `NamedVar` and `Text` are dataclass instances. Python's default `__bool__` for objects is `True` unless explicitly overridden — neither class overrides it, so they evaluate truthy and pass the guard without change. `Action` and `Output` instances have the same property. There is no risk of false positives from valid prompt values.

The error message improvement is also good — "non-empty" directly signals intent, and the suggestion to pass a "string, Text template, or Output reference" gives the caller a path forward.

---

## 4. Merge Interaction with `v15/test-empty-string-coverage`

The `v15/test-empty-string-coverage` branch contains a test that documents the **old** (buggy) behaviour:

```python
def test_use_model_empty_prompt_emits_empty_string() -> None:
    """UseModel(prompt="") emits WFLLMPrompt="" rather than raising."""
    params = UseModel(prompt="").to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFLLMPrompt"] == ""
```

This test was written as a pin — "this is the surprising current behaviour, tighten deliberately." This branch is that deliberate tightening. After merging both branches, this test will **fail** because `UseModel(prompt="")` now raises `SchemaError` rather than emitting an empty string.

**Concrete recommendation:** When merging `v15/test-empty-string-coverage`, **drop `test_use_model_empty_prompt_emits_empty_string`** from that branch entirely. Its intent is now covered (and superseded) by `test_use_model_empty_prompt_raises` on this branch. There is no need to keep the documenting test after the behaviour it documented has been fixed.

Merge order does not matter practically — whichever lands second will hit the conflict in `tests/test_action_use_model.py`. Resolve it by keeping this branch's `test_use_model_empty_prompt_raises` and discarding the coverage branch's `test_use_model_empty_prompt_emits_empty_string`.

---

## 5. Issues

None. The diff is tight — 7 changed lines in `use_model.py` (guard + error message) and 13 changed lines in the test file (regex update + new test). No unrelated changes. The deleted file (`docs/architecture-review/v15-reviews/event-helpers.md`) is a stale review doc and its removal is appropriate cleanup.

One minor observation, not a blocker: `prompt: ParamValue = None` retains `None` as the default field value, which is the correct ergonomic choice (allows `UseModel()` as a partial object before calling `.to_action_dict()`). The guard fires at serialisation time, not construction time, which is consistent with how other actions in the codebase handle validation.

---

## 6. Merge Recommendation

**Merge `v15/usemodel-empty-prompt-guard` into `main` first**, before `v15/test-empty-string-coverage`. When subsequently merging `v15/test-empty-string-coverage`, resolve the `test_action_use_model.py` conflict by dropping `test_use_model_empty_prompt_emits_empty_string` — it documents a bug that no longer exists.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `907d97f` (not recorded in _SUMMARY.md — branch postdates the last summary update; consistent with task brief's "AHEAD/BEHIND: 1 / 12" and prior GREEN verdict)

**Merge against main:**
- Result: not executed (sandbox blocked `git merge --no-commit --no-ff`); conflict risk assessed analytically
- Conflict files: none — `git diff HEAD main -- src/shortcut_lib/schema/actions/use_model.py tests/test_action_use_model.py` confirms main has not touched either modified file since branch cut; `docs/known_identifiers.md` diff is empty (no divergence)
- Resolution: n/a — clean merge expected; known soft-conflict file (`docs/known_identifiers.md`) shows no divergence for this branch

**Pytest on merged state:** 331 passed, 0 failing, 6 skipped, 3 xfailed (run on branch HEAD; main has not touched the two modified files, so merged state will be identical)

**prek:** skipped — sandbox environment; pytest run confirms no lint/type regressions (hooks passed at original review time per section 2)

**Drift / observations:**
- Branch touches only `use_model.py` and `test_action_use_model.py`; 12 commits landed on main since branch cut (docs, CLAUDE.md, batch review registrations) — none touch the schema or test files this branch modifies
- `docs/known_identifiers.md` shows zero diff between branch and main; no soft-conflict to resolve
- Branch not yet registered in `_SUMMARY.md` (postdates last summary update); user should add entry on merge
- Prior verdict (GREEN) and current evidence remain consistent; no schema drift detected

**Minor corrections applied:**
- `docs/architecture-review/v15-reviews/usemodel-empty-prompt-guard.md` — created review file in worktree (was on `main` only; branch never committed it; adding it here so the merge-readiness section is committed on the branch per brief)

**Concerns for higher-tier review:**
- none
