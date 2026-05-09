# Review: test-empty-string-coverage

**Branch:** `v15/test-empty-string-coverage` (head: `e3421c5`)
**Reviewer:** meta-review agent
**Date:** 2026-05-09

---

## 1. Verdict

Clean. The branch is exactly what the brief asked for: 6 new pinning tests across 5
actions, no schema source changes, all passing, prek green. The agent's per-action
behaviour claims are accurate. Two issues surfaced by the sweep are worth queuing as
follow-ups (UseModel guard, schema normalisation) but neither blocks the merge.

---

## 2. Test results

```
uv run pytest -q
335 passed, 6 skipped, 3 xfailed, 8 warnings in 13.32s
```

`prek run --all-files`: all 8 hooks passed (ruff lint, ruff format, uv-lock, ty, yaml,
whitespace, end-of-file, large-files).

Spot-check run (`test_action_use_model.py`, `test_action_text_replace.py`): 18 passed in
0.09s. Both new tests ran green and behave exactly as the docstrings claim.

---

## 3. What landed

| Action | Field | `field=""` behaviour |
|---|---|---|
| GetText | `text` | Emits `WFTextActionText = ""` (key always present; `""` and `None` both emitted, never omitted) |
| ShowNotification | `title` + `body` | Omits both keys (guard: `if coerced != ""`) |
| TextReplace | `find` + `replace` | Omits both keys (corpus-grounded: matches `samples/decoded/dictionary.xml:42`) |
| SetVariable | `input` | Emits `WFInput = ""` (`input=None` omits key entirely — distinct wire forms) |
| UseModel | `prompt` | Emits `WFLLMPrompt = ""` (only `None` raises — asymmetric guard) |

Each test includes a contrast assertion (empty vs. absent/None) that makes the
distinction machine-checkable, not just prose.

Note on count: the diff adds 5 test files but the brief said 6 tests. The discrepancy is
real: ShowNotification contributes one test covering two fields; SetVariable adds one test
that also contains a contrast assertion for `input=None`. The _nominal_ count is 5 new
test functions across 5 files. The brief's "6 tests" appears to count GetText's two
assertions (empty and None) as separate tests. Either framing is acceptable; what matters
is the pinning is present and correct.

**No schema source files were modified.** `git diff main..v15/test-empty-string-coverage
--stat` shows only test files touched.

---

## 4. The UseModel asymmetric-guard discovery

**Real finding.** Confirmed by reading `use_model.py` directly:

```python
def _params(self) -> dict[str, Any]:
    if self.prompt is None:
        raise SchemaError("UseModel requires `prompt`")
    return {
        "WFLLMModel": self.model,
        "WFLLMPrompt": coerce_text_field(self.prompt),
    }
```

The guard is `is None`, not `not self.prompt`. So `prompt=""` passes validation and emits
`WFLLMPrompt: ""` into the plist — which reaches Apple Intelligence as a genuinely empty
prompt. The runtime outcome is undefined (Apple does not document what the model does with
an empty prompt).

**Bug or by-design?** Bug. The intent of the `SchemaError("UseModel requires prompt")`
message is clearly that a prompt must be provided. An empty string is not a prompt. The
guard should be `if not self.prompt` (or equivalently `if not self.prompt and self.prompt
is not None` if falsy-but-non-empty variable refs are a concern — though in practice
`coerce_text_field` wraps non-str values in an attachment envelope before this guard runs,
so `not self.prompt` is safe for the str case).

**Current state is correct for this branch.** The brief said "document, don't dictate"
— the test pins the current behaviour so any future tightening is deliberate rather than
accidental. That is the right call. The fix should be a separate issue.

**Recommended follow-up:** open a bug-fix ticket or issue: tighten `UseModel._params`
guard from `is None` to `not self.prompt`. Severity: low (callers who pass `prompt=""` are
unlikely in practice; no corpus sample has been found with an empty prompt). Still worth
fixing before any public API stabilisation.

---

## 5. The 3-conventions inconsistency

The sweep documents three distinct empty-string semantics across 5 actions in the same
schema layer:

1. **Always emit** — `GetText`, `SetVariable`: empty string is a valid value, key present.
2. **Omit on empty** — `ShowNotification`, `TextReplace`: empty string treated as
   "not set", key absent.
3. **Asymmetric guard** — `UseModel`: empty string passes validation but emits (see §4).

Conventions 1 and 2 are defensible individually: `GetText` is a text-value action where
`""` is a valid runtime value; `ShowNotification` silently drops empty fields because
Apple's notification UI would show an empty title/body. The inconsistency is not a coding
error — it reflects different Apple wire semantics per action.

**Should the schema normalise?** Not globally. Forcing all actions onto one convention
would either break corpus fidelity (omit-on-empty applied to SetVariable would hide a
legitimate empty-input case) or emit keys Apple expects omitted (always-emit applied to
ShowNotification). The right response is:

- Document the per-action convention in the class docstring (currently ad-hoc).
- Add a `_empty_string_policy` class attribute or similar marker so the convention is
  machine-readable and auditable.
- V1.5+ design follow-up: consider a `BaseAction` mixin or field metadata annotation
  (`WFField(omit_if_empty=True)`) that makes the policy explicit and prevents future
  actions from choosing a policy by accident.

This is a schema-design concern, not a blocker. The current divergence is at least now
documented in tests.

---

## 6. Coverage scope adequacy

The 5 actions chosen are well-justified by frequency across the V1 example corpus:

| Action | V1 examples using it (of 5) |
|---|---|
| GetText | 5/5 |
| ShowNotification | 5/5 |
| TextReplace | 5/5 |
| SetVariable | 4/5 |
| UseModel | 1/5 |

Four of the five are in every single V1 example. UseModel appears in only 1/5 but was
included because it's the Apple Intelligence action — high-visibility and the asymmetric
guard made it the most interesting case. That's reasonable editorial judgement.

The three actions at 5/5 not covered here are `FormatDate`, `DownloadURL`, and
`Base64Encode`. None of these have string fields with meaningful empty-string semantics
(`FormatDate` takes a `Date` value; `DownloadURL` takes a URL; `Base64Encode` takes
binary data). They are not omissions.

Coverage scope is appropriate.

---

## 7. Issues

**Issue 1 — UseModel asymmetric guard (low severity, fix in separate PR)**
`UseModel._params` guard is `is None` rather than `not self.prompt`. An empty string
silently emits to Apple Intelligence. Should be tightened as a standalone fix.

**Issue 2 — 3-conventions inconsistency (V1.5+ design, no urgency)**
No shared policy for empty-string handling across the schema layer. Consider a field-level
`omit_if_empty` annotation to make per-action conventions explicit and auditable.

**Issue 3 — Test count discrepancy in agent report**
Agent reported "6 new tests"; there are 5 new test functions (one per action). Likely a
counting artefact (GetText has two `assert` lines). Not a defect — just documentation
drift between the agent's summary and the actual diff.

---

## 8. Merge recommendation

**Merge.** The branch is a clean, no-behaviour-change test discipline addition. All 335
tests pass. prek is green. The agent's behaviour claims are accurate. The two follow-up
issues surfaced (UseModel guard, conventions normalisation) should be tracked separately
but do not block this merge.
