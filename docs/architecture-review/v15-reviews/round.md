# Review: v15/model-round — `is.workflow.actions.round`

**Reviewer:** automated review agent
**Date:** 2026-05-09
**Head:** b5fa038

---

## 1. Verdict

**Approve.** The implementation is clean, honest about its speculative surface, and
fully verified against the corpus. All 16 tests pass; pre-commit is green. No
blocking issues.

---

## 2. Test Results

```
16 passed in 0.11s
```

All categories covered: constructor defaults, per-field emission logic, validation
errors, registry lookup, wire-format equivalence against all three corpus samples,
and a spot-check sweep across 8 of the 11 place literals.

Pre-commit (`prek run --all-files`): all 8 hooks pass (trailing whitespace, YAML,
ruff lint, ruff format, uv-lock, ty).

---

## 3. What Landed

`src/shortcut_lib/schema/actions/round.py` — 97 lines:

- `RoundNumber` dataclass registered under `is.workflow.actions.round`.
- Three fields: `input` (`ParamValue`, nullable), `mode` (`WFRoundMode`,
  default `"Normal"`), `place` (`WFRoundPlace`, default `"Ones Place"`).
- `_params()` applies the two default-omission rules: `WFRoundMode` absent when
  `"Normal"`, `WFRoundTo` absent when `"Ones Place"`. Both are confirmed by the
  corpus (two dictionary.xml samples carry neither key; start_pomodoro.xml carries
  only `WFRoundMode`).
- `__post_init__` validates both enums using `frozenset` fast-path; raises
  `SchemaError` with a diagnostic message naming the bad value.
- Oracle confirms `WFInput` wraps as `WFTextTokenAttachment` (count: 3, matching
  the three corpus appearances). `coerce_value` is the right call here.
- `default_output_name = "Rounded Number"` is plausible but not corpus-confirmed
  (none of the three samples carry a `CustomOutputName`). This is acceptable — it
  is documented as the default Apple label, not an observed value.

`tests/test_action_round.py` — 300 lines, 16 tests:

Wire-format tests target all three corpus samples by UUID, exercising both the
default-only path (dictionary.xml ×2) and the non-default-mode path
(start_pomodoro.xml). The test for the second dictionary.xml appearance explicitly
asserts `len(round_actions) >= 2`, which would catch a corpus regression.

---

## 4. Literal-Speculation Discipline

This PR introduces the most speculative enum surface in the v15 series to date:
11 `WFRoundPlace` values with zero corpus confirmation.

The discipline is well-applied:

- The module-level comment above `WFRoundPlace` is explicit: *"Not observed in the
  three corpus samples … Values sourced from Apple's documented Shortcuts action
  surface (jellycore parameter key: `roundTo`)."*
- The class docstring names the default-omission basis: all three corpus samples
  carry no `WFRoundTo`, which only tells us the default value, not the full set.
- `_VALID_ROUND_PLACES` is a closed `frozenset` — unrecognised values fail
  loudly, which is the right stance for an unverified set.

The one mild concern: `test_round_all_valid_places_spot_check` tests 8 of 11 place
values rather than all 11. The three omitted values (`Ten Thousands`,
`Hundred Thousands`, `Millions`) are the large-magnitude end of the range. This is
not a correctness gap — all values are equally unconfirmed — but a future reviewer
seeing partial coverage might wonder whether the omissions are intentional. A brief
comment in the test (or expanding to all 11) would close that question. This is
cosmetic, not blocking.

The underlying risk of 11 unconfirmed literals is real but acceptable at this
project's confidence level: jellycore is a well-maintained open-source reference for
the Shortcuts action surface, and the place names are stable UI strings unlikely to
differ from wire values.

---

## 5. Issues

**Minor / non-blocking:**

1. `test_round_all_valid_places_spot_check` omits three of the eleven place values
   (`"Ten Thousands"`, `"Hundred Thousands"`, `"Millions"`). A brief inline comment
   explaining the omission — or expanding to cover all 11 — would remove any future
   ambiguity about intent.

No other issues found. No pre-existing smells were surfaced in adjacent files during
this review.

---

## 6. Merge Recommendation

**Merge.** The implementation is complete, honest, and fully tested against the
corpus. Default-omission logic matches observed wire format. Literal-speculation
risk is clearly documented at both the module and docstring level. The single minor
issue (spot-check omitting 3 of 11 place values) is cosmetic and does not affect
correctness.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `b5fa038` (matches _SUMMARY.md record `b5fa038`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts. The branch only adds `src/shortcut_lib/schema/actions/round.py` and `tests/test_action_round.py`; main's 19-commit advance touched neither file.

**Pytest on merged state:** 347 passing, 0 failing, 6 skipped, 3 xfailed

**prek:** green (all 8 hooks pass: trailing whitespace, end-of-files, YAML, large-files, ruff lint, ruff format, uv-lock, ty)

**Drift / observations:**
- No schema, wire-key, or envelope conventions on main contradict this branch's choices. `coerce_value` for `WFTextTokenAttachment` and default-omission via `_params()` match the established pattern across merged siblings.
- The review file (`docs/architecture-review/v15-reviews/round.md`) was committed to main as part of batch 14 registration and was absent from the worktree — added here to bring the branch into sync before merge.
- 1/3 mode values corpus-confirmed (one appearance of a non-default mode in `start_pomodoro.xml`); 0/11 place values corpus-confirmed. Both honestly disclaimed in the source. Speculation level is within the accepted band for this project.

**Minor corrections applied:**
- `docs/architecture-review/v15-reviews/round.md` — review file created in worktree (was missing; existed on main only, added by batch-14 registration commit). No schema or test changes. (commit recorded below)

**Concerns for higher-tier review:**
- none
