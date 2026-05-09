# Review: v15/model-addnewreminder

**Verdict: green**
**Branch:** `v15/model-addnewreminder` (head: 7a55c54)
**Reviewer:** Claude Sonnet 4.6 (autonomous, 2026-05-09)

---

## Test result

16/16 passed, 0 failures, 0 skipped. Full suite: 346 passed, 7 skipped, 3 xfailed.
All pre-commit hooks pass (ruff lint, ruff format, ty, uv-lock).

---

## What landed

Three files changed (+570 lines):

- `src/shortcut_lib/schema/actions/add_new_reminder.py` — 196 lines. Typed schema for `is.workflow.actions.addnewreminder`. Ten fields, two Literal aliases, runtime validation in `__post_init__`, clear field-by-field `_params()` logic with comment on each key.
- `tests/test_action_add_new_reminder.py` — 358 lines. 16 tests covering minimal, full, required-field validation, optional-field omission, registry lookup, `alert_enabled`/`alert_condition` independence, invalid-value rejection, WFTextTokenString serialisation, and two wire-format equivalence tests grounded in real corpus samples.
- `docs/known_identifiers.md` — histogram refresh to incorporate new corpus scans (counts and file lists updated across several rows).

---

## Sample-grounding verification

Five corpus appearances across four files: `batch_add_reminders.xml` (actions 2 and 12), `set_weekend_chores.xml` (action 3), `add_expiry_reminder.xml` (action 3), `dictionary.xml` (empty params — title-only appearance). All five were independently inspected.

**`WFAlertEnabled` value type.** Confirmed string-valued in all observations where present. `"Alert"` appears in `set_weekend_chores.xml:3` and `add_expiry_reminder.xml:3`. `"No Alert"` appears in `batch_add_reminders.xml:12`. The key is absent entirely from `batch_add_reminders.xml:2` and `dictionary.xml`. No boolean `<true/>`/`<false/>` usage observed anywhere. The implementation is correct.

**`WFAlertCondition` values.** `"When I Arrive"` appears in `batch_add_reminders.xml` actions 2 and 12. `"At Time"` appears in `set_weekend_chores.xml:3` and `add_expiry_reminder.xml:3`. These are the only two values observed in the corpus. The Literal alias adds a third speculative value `"When I Leave"` (symmetric with "When I Arrive") — addressed separately under Design Opportunities.

**`WFAlertCondition` without `WFAlertEnabled` — the batch_add_reminders:2 quirk.** Independently confirmed: `batch_add_reminders.xml` action 2 carries `WFAlertCondition: "When I Arrive"` with no `WFAlertEnabled` key whatsoever. The action also carries `WFAlertLocationRadius`, `WFCalendarItemNotes`, `WFCalendarItemTitle`, and `WFFlag: false`. The agent's decision not to enforce co-occurrence is correct. Apple's Shortcuts runtime clearly allows the condition to be stored independently of the toggle, which may represent an intermediate UI state or a runtime-resolved default. Enforcing co-occurrence would make it impossible to round-trip this real sample.

**`WFCalendarItemNotes` wire format.** Present in `batch_add_reminders.xml:2` and `set_weekend_chores.xml:3` as a bare empty `<string></string>`, not wrapped in a WFTextTokenString envelope. Confirmed. The schema models this as `str | None` (not `ParamValue`), which is correct for the observed wire format. An LLM author who needs a dynamic notes body would need a different field type — this is a V1 limitation but is grounded in what samples actually show.

**`WFURL` wire format.** Present in `batch_add_reminders.xml:12` as a bare empty `<string></string>`. The `WFURL` appearances in `dictionary.xml` that carry WFTextTokenString envelopes belong to `showwebpage` and `readinglist` actions — not `addnewreminder`. Within the addnewreminder corpus, bare string is the only observed format. The `str | None` type for `url` is correct for V1.

**`WFAlertLocationRadius` wire shape.** Confirmed as `WFQuantityFieldValue` dict with `Value: {Magnitude, Unit}` shape from `batch_add_reminders.xml:2`. Only one sample observation. The dict pass-through is the right V1.5 punt.

**`WFFlag`.** Confirmed as native plist boolean (`<false/>`) in `batch_add_reminders.xml:2`. The `bool | None` type is correct.

**`WFParentTask`.** Confirmed as `WFTextTokenAttachment` in `batch_add_reminders.xml:12`, referencing action 2's UUID by `OutputName: "New Reminder"` and `OutputUUID`. The schema's use of `coerce_value` to emit `WFTextTokenAttachment` is correct, and stripping `OutputUUID` in the equivalence test allows deterministic comparison.

---

## Type-system assessment

The agent used `Literal` types for both controlled-vocabulary fields, consistent with the V1 Literal-migration pattern established in `text_split.py` and `ask.py`. This is the correct approach.

**`WFAlertEnabled = Literal["Alert", "No Alert"]`** — alias name is clear and follows the established `WFXxx = Literal[...]` convention. The `_VALID_ALERT_ENABLED` frozenset derived via `get_args(...)` mirrors the TextSplit and Ask patterns exactly.

**`WFAlertCondition = Literal["At Time", "When I Arrive", "When I Leave"]`** — the two observed values are correctly included. The speculative third value `"When I Leave"` is discussed under Design Opportunities.

**`calendar: str | None`** — the review brief asked whether this should be a Literal. The answer is no: the observed values are `"Shopping"` and `"Chores"` (user-defined list names), not a fixed Apple-defined set. Free `str` is correct here. There is no typo risk because the value is opaque to the schema — it's whatever list name the user has in Reminders.app.

**`notes: str | None` and `url: str | None`** — both are bare strings in all corpus observations. `str | None` is correct. The risk of a LLM author passing a variable reference (which would need WFTextTokenString wrapping) cannot be eliminated at V1 without changing the type to `ParamValue`. This is a known V1 limitation, addressed under Design Opportunities.

**`__post_init__` runtime validation** — validates `alert_enabled` and `alert_condition` against their respective `_VALID_*` frozensets. Clear error messages with expected values. `title=None` check fires before the Literal checks, which is the correct ordering. The runtime guards are the right backstop given that type checkers cannot enforce Literal constraints on all callers.

The `ty: ignore` annotations in the test file for intentionally invalid-type calls are correctly applied and do not suppress real type errors.

---

## Issues

### Blockers

None.

---

### Design opportunities

**1. `"When I Leave"` speculation should be flagged, not silently included.**

`WFAlertCondition` includes `"When I Leave"` without any corpus evidence. Zero of the 5 samples use this value. It is plausible (symmetric with "When I Arrive") but unverified. Including it is low-risk given that an invalid value passed to Apple would fail at runtime, not silently do the wrong thing — and the corpus is small. However, the docstring and the alias comment do not flag this as speculative. A one-line note (`# "When I Leave" — symmetric, not observed in corpus; included by reasoning`) would make the assumption explicit for future reviewers. Not a blocker, but apply before merge if easy.

**2. `notes` and `url` accept only bare strings; variable references would silently fail.**

Both `WFCalendarItemNotes` and `WFURL` are typed `str | None`, matching their corpus appearances (all empty strings). An LLM author who tries to pass an `Output` or `NamedVar` to `notes` or `url` would get a Python `str` type error but no clear schema-level guidance. The docstring for `notes` doesn't mention this limitation. At V1 this is an acceptable scope cut — no sample shows a variable reference in either field for this action. Worth noting in the docstring for a future V1.5 upgrade to `ParamValue` if corpus evidence emerges.

**3. `WFAlertEnabled` string toggle vs. LLM-author-friendly boolean.**

The brief raised whether `alert_enabled: bool` mapping to `"Alert"` / `"No Alert"` internally would be cleaner for callers. It would be. The current API requires `alert_enabled="Alert"` rather than `alert_enabled=True`. The string values are unusual — they look like they should be booleans from a user perspective, and the Apple wire format's choice to use strings instead of `<true/>`/`<false/>` is a quirk that bleeds through to the schema surface. A future V2 convenience wrapper (`alert: bool`) that maps to the string internally would improve ergonomics without breaking wire compatibility. Not a V1 blocker — the Literal type at least prevents silent typos — but worth a roadmap note.

**4. `WFAlertLocationRadius` dict pass-through.**

One sample observation, `WFQuantityFieldValue` shape (`{Value: {Magnitude, Unit}, WFSerializationType: "WFQuantityFieldValue"}`). Deferring to a `Quantity`-typed field is correct V1 discipline. The existing `dict[str, Any]` type with a docstring note is sufficient for now. Flag for V1.5 if a `Quantity` type is introduced elsewhere.

---

### Notes

**`default_output_name = "New Reminder"`.** Confirmed grounded: `batch_add_reminders.xml:12`'s `WFParentTask` references action 2 by `OutputName: "New Reminder"`. The name matches what Shortcuts.app assigns by default. The dedicated test `test_default_output_name` verifies this explicitly.

**Wire equivalence test indexing.** The brief described the tested equivalence tests as `batch_add_reminders:12` and `set_weekend_chores:3`. This is correct. Action index 12 (0-based) in `batch_add_reminders.xml` is the child reminder with `WFParentTask` and `WFAlertEnabled: "No Alert"`. Action index 3 (0-based) in `set_weekend_chores.xml` is the timed-alert reminder with `WFAlertCustomTime` and `WFAlertEnabled: "Alert"`. Both equivalence tests pass with normalised comparison (UUID stripping). A third grounding test for `add_expiry_reminder.xml:3` (which exercises an `ActionOutput`-referenced `WFAlertCustomTime` rather than an `Ask` reference) would give additional coverage but is not required for a green verdict.

**Comment quality in `_params()`.** Each key emission block has a comment explaining the wire key name, format, and condition. This is above average for this codebase and makes the file self-documenting for future maintainers.

**File sizes within policy.** Implementation: 196 lines (under 500-line ceiling). Tests: 358 lines. Both within project norms. The implementation would be a reasonable split candidate at 250+ lines, but 196 is comfortably under.

---

## Merge recommendation

**Merge.** All tests pass, full suite is clean, pre-commit hooks pass. The Literal type choices are correct and consistent with the project pattern. Sample grounding is thorough across all five corpus appearances. The `"When I Leave"` speculation note is a minor documentation gap — add a one-line comment if easy, but do not block merge on it. The design opportunities (bool wrapper, `notes`/`url` variable support, Quantity type for location radius) are V1.5 items and are appropriately deferred.
