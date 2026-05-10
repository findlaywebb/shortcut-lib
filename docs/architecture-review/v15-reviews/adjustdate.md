# Review: v15/model-adjustdate — `is.workflow.actions.adjustdate`

**Reviewer:** automated review agent
**Date:** 2026-05-09
**Head:** 44b1bb0

---

## 1. Verdict

**Merge with one follow-up filed.** The implementation is correct, cleanly
written, and honestly grounded in the corpus. All 22 tests pass; prek is green.
The dual-slot design choice is the central question here, and it is defensible —
though the wire-equivalence test patching reveals a real unresolved seam that
deserves a follow-up issue. Doc quality is the strongest in the v15 batch.

---

## 2. Test Results

```
22 passed in 0.11s
```

Coverage: all four operations, all seven unit-abbreviation pairs (parametrized),
scalar and variable magnitude, missing-input omission, registry lookup, identifier
and default-output-name constants, three validation error paths, period-op
magnitude exemption, and one wire-format equivalence test against
`start_pomodoro.xml`.

Pre-commit (`prek run --all-files`): all 8 hooks pass (trailing whitespace, YAML,
ruff lint, ruff format, uv-lock, ty).

---

## 3. What Landed

`src/shortcut_lib/schema/actions/adjust_date.py` — 265 lines:

- `AdjustDate` dataclass registered under `is.workflow.actions.adjustdate`.
- Four fields: `input` (`ParamValue`, nullable), `operation` (`WFAdjustOperation`,
  default `"Add"`), `magnitude` (`ParamValue`, nullable), `unit` (`WFTimeUnit`,
  default `"Hour"`).
- `__post_init__` validates both enum fields via `frozenset` and enforces
  `magnitude is not None` for Add/Subtract operations, raising `SchemaError` with
  diagnostic messages in all three cases.
- `_params()` emits `WFAdjustOperation` as a bare string (corpus-confirmed),
  `WFDate` via `coerce_text_field`, `WFDuration` as a `WFQuantityFieldValue`
  envelope with abbreviated units, and `WFAdjustOffsetPicker` as a
  `WFTimeOffsetValue` envelope with spelled-out units. For period operations, the
  two duration slots are omitted.
- `_UNIT_TO_ABBREV` maps all seven spelled-out units to their abbreviated wire
  forms; `_PERIOD_OPERATIONS` is a `frozenset` gate controlling dual-slot emission.
- `default_output_name = "Adjusted Date"` — corpus-confirmed: `dictionary.xml`
  uses `"Adjusted Date"` as the `OutputName` of the action's output downstream
  in the `gettimebetweendates` action.

`tests/test_action_adjust_date.py` — 390 lines, 22 tests.

---

## 4. The Dual-Slot Finding

### Verification

The corpus evidence is clear. In `start_pomodoro.xml`, the `adjustdate` action
emits all three of `WFAdjustOperation`, `WFDuration`, and `WFAdjustOffsetPicker`
simultaneously. Verified directly against the decoded XML:

- `WFDuration` is a `WFQuantityFieldValue` envelope. Its `Magnitude` is the
  `"Rounded Number"` action output (from the preceding `round` action).
  Its `Unit` is `"min"` (abbreviated).
- `WFAdjustOffsetPicker` is a `WFTimeOffsetValue` envelope. Its `Value` is the
  `"Ask for Input"` action output — **a different upstream action** from `WFDuration`.
  Its `Unit` is `"Minute"` (spelled-out).

So the dual-slot claim is confirmed, and the corpus further reveals that Apple's
own Shortcuts editor produced two *different* action output references for the two
slots in this sample — `Rounded Number` for `WFDuration` and `Ask for Input` for
`WFAdjustOffsetPicker`. This is not a corpus encoding artifact: these are two
distinct upstream actions in the workflow, and the Shortcuts editor independently
wired each slot.

The `dictionary.xml` sample confirms the period-operation claim by negation: only
`WFDate` is present, with no `WFAdjustOperation`, `WFDuration`, or
`WFAdjustOffsetPicker`. This is consistent with the action not yet having an
operation configured in that demo shortcut.

Jellycore's `parameter_keys` for this action lists only `["operation", "WFDuration",
"WFDate"]` — `WFAdjustOffsetPicker` is absent. This is a jellycore omission (it
is a rendered UI widget, not a canonical parameter key), not a reason to doubt the
corpus observation.

### Design Choice Assessment

The corpus reveals that Apple's Shortcuts editor independently populates
`WFDuration` and `WFAdjustOffsetPicker` from potentially different source actions.
This is almost certainly an implementation detail of Apple's UI: `WFDuration` is
the primary value slot for date arithmetic; `WFAdjustOffsetPicker` is a redundant
preview/picker widget whose value tracks user interaction separately. They happen
to converge on the same magnitude in the typical case (same variable, same unit),
but they are technically independent slots.

Three design options were on the table:

**(a) Single `magnitude` field mirrored into both slots** — current implementation.
The schema reflects the common case (same magnitude in both slots), produces valid
wire output, and keeps the API simple. The cost: it cannot reproduce a workflow
where the two slots were authored with different source values.

**(b) Separate `quantity` and `picker_value` fields.** Would faithfully reproduce
every possible corpus configuration. Cost: ergonomics suffer significantly — users
would need to pass the same value twice in the common case, and the distinction
between the fields is opaque to anyone unfamiliar with the wire format.

**(c) Default-mirror with override hook** — e.g. `picker_value: ParamValue | None = None`,
falling back to `magnitude` when `None`. Balances correctness and ergonomics: the
common case is simple, the edge case is representable.

**Recommended posture: (a) for now, with option (c) as the clear upgrade path.**
The `start_pomodoro.xml` divergence (Rounded Number vs Ask for Input) is a real
corpus observation but not a case the library needs to reproduce in v1.0. The
library's job is to *author* new shortcuts, not round-trip arbitrary existing ones.
For authoring, the single-magnitude model is correct: you pick a duration and unit,
and both Apple slots carry it. Option (c) should be filed as a follow-up for
completeness — if a user ever needs to reproduce a corpus-diverged shortcut, it's
the natural extension point.

The current implementation (option a) is the right call for v1.0. It is not hiding
complexity it should expose; it is making a sensible API trade-off.

---

## 5. The Wire-Equivalence Test Patching

`test_wire_format_vs_start_pomodoro` patches the schema's
`WFAdjustOffsetPicker.Value.Value` with the sample's picker value (Ask for Input)
before asserting equality. The docstring explains why: the sample uses two different
action outputs for the two slots, the schema mirrors one, so the picker side will
always diverge from the sample without the patch.

This is a **smell, but a well-lit one.** The patch is not hiding a bug — it is
explicitly documenting a known limitation of the current design. The test docstring
calls out the divergence in plain language: *"The sample's WFAdjustOffsetPicker.Value
references 'Ask for Input' (a different OutputName from WFDuration.Magnitude which
is 'Rounded Number')."*

The alternative — splitting the test into "structural shape is correct" and "corpus
equivalence with known caveat" sub-assertions — would not add information; the
current patched test already communicates both things. The test correctly asserts:
(1) the schema produces the right structural shape, and (2) the sample's picker-side
value is accepted as a valid substitution in that shape.

The smell is real: a pure wire-equivalence test should not mutate the schema output
before comparison. If option (c) is ever implemented, this test should be rewritten
to construct a schema action with both `magnitude=rounded` and
`picker_value=ask_for_input`, and the patch should disappear. Until then, the
current approach is defensible given the documented design constraint.

---

## 6. Doc Quality

**5 / 5.**

This is the strongest docstring in the v15 series. It covers:

- Module-level docstring with wire-format evidence in two explicit corpus samples,
  rendered as doctest-style block literals.
- The dual-slot quirk (abbreviated vs spelled-out units, same value mirrored) is
  named explicitly at the module level, not buried.
- The class docstring documents all four parameters with types, defaults, and
  the period-operation exemption for `magnitude`.
- Two wire-format tables (Add/Subtract vs Get Start/End) show the exact key names
  and serialisation types.
- Corpus evidence section references both corpus files by name and describes what
  each confirms or denies.
- Four working examples cover the canonical use cases.

The v1.0.0 criterion (comprehensive coverage + clear per-action docs) is met. The
dual-slot quirk is documented at the right level of prominence — visible in the
module docstring before any code, not relegated to a comment inside `_params()`.

---

## 7. Issues

**Minor / non-blocking:**

1. **`_UNIT_TO_ABBREV` not tested for `WFAdjustOffsetPicker` side.** The
   parametrized `test_unit_abbreviation` test verifies that each unit produces the
   correct abbreviated form in `WFDuration`. It does not assert that the
   spelled-out unit is correctly mirrored in `WFAdjustOffsetPicker.Value.Unit`.
   This is low-risk (the code path is trivially `self.unit` without transformation),
   but a one-liner assertion per parametrize case would close the gap.

2. **`dictionary.xml` not tested directly.** The `dictionary.xml` sample's
   `adjustdate` appearance (date-only, no operation) is described in the module
   docstring but has no corresponding wire-equivalence test. The `test_no_input_omits_wfdate`
   test covers the `WFDate`-absent case but does not load the corpus file and
   compare normalised dicts. Medium priority — the corpus is referenced only
   implicitly.

3. **Follow-up: option (c) picker-value override hook.** The
   `WFAdjustOffsetPicker.Value.Value` divergence is a real corpus observation that
   the current schema cannot reproduce. Filing as a v1.x follow-up issue for the
   rare case where a user needs to round-trip a corpus shortcut with diverged slot
   values.

4. **Jellycore `parameter_keys` omits `WFAdjustOffsetPicker`.** The
   `jellycore_facts.json` entry lists only `["operation", "WFDuration", "WFDate"]`.
   This is a jellycore gap, not a schema gap, but worth noting: the schema correctly
   emits a fourth key that jellycore does not document.

---

## 8. Merge Recommendation

**Merge as-is, with follow-up filed for issue #3 (picker-value override hook).**

The implementation is correct, cleanly written, and honestly grounded in two corpus
samples. The dual-slot design choice (option a, single magnitude mirrored) is the
right call for v1.0 authoring use cases. The wire-equivalence test patching is a
smell but fully documented and consistent with the stated design constraint. Doc
quality is exemplary. Issues #1 and #2 (picker-unit assertion gap, no
`dictionary.xml` wire-equivalence test) are cosmetic and do not affect correctness.
Issue #3 (picker-value override) is the natural extension point if a future user
needs to reproduce corpus-diverged shortcuts.
