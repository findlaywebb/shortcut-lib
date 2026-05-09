# V1.5 Section A — Deep Review: Action Coverage

**Scope:** the 11 unmerged `v15/*` branches that add typed action models
(`fu13-textsplit-showtext`, `model-file-rename`, `model-text-combine`,
`model-addnewreminder`, `model-sendmessage`, `model-previewdocument`,
`model-filter-calendarevents`, `model-showresult`, `model-choosefromlist`,
`model-list-helpers` — adding `GetItemFromList` and `Count`,
`model-alert`).

**Reviewer:** Opus deep cross-cutting pass. Per-branch reviews under
`docs/architecture-review/v15-reviews/` are the trees; this is the forest.

**Reviewed at:** 2026-05-09.

---

## 1. Overall verdict

V1.5 Section A delivers ten new typed actions plus one polish change to
`TextSplit`. Per-branch correctness is good — every action is sample-grounded,
every wire-format equivalence test passes against a real corpus action, and
the registry/discovery surface is clean. The implementations follow the V1
patterns where they apply.

But viewed across all eleven branches together, the work has three
cross-cutting weaknesses that the per-branch sonnet reviews underrated
because each looked at one tree:

1. **Test-helper duplication is widespread and was avoidable.** Six of
   eleven new test files copy `_load`, `_strip_output_uuids`, `_normalise`
   verbatim from `tests/test_wire_format_equivalence.py`. Two more files use
   trimmed variants. The pattern is now too entrenched to leave — extract a
   `tests/_wire_helpers.py` (or `conftest.py`) before merge or the duplication
   compounds with every future action.
2. **Pattern divergence is subtle but real.** Several new actions emit
   non-`WF`-prefixed wire keys (`Count.Input`, `ShowResult.Text`,
   `TextCombine.text`, `TextSplit.text`, `TextSplit.separator`, `TextCombine.Show-text`,
   `TextSplit.Show-text`). These quirks are individually documented but not
   inventoried anywhere. Future authors adding sibling actions will not know
   to check whether their action uses `WFInput` or `Input`. A short
   `docs/wire_format_quirks.md` (or a `BARE_KEY_ACTIONS` registry) would lock
   this in once.
3. **Factory-method discipline is uneven.** `AskForInput` (V1) has factories.
   `GetItemFromList` (V1.5) added factories. `Count`, `ChooseFromList`,
   `FilterCalendarEvents`, `AddNewReminder`, `TextCombine` all have dependent
   fields where factories would help, and didn't get them. There is no
   documented rule for when factories are warranted. The current heuristic
   ("when the agent feels like it") will produce inconsistent ergonomics across
   the surface.

The merge can proceed in the order the autonomous summary recommends. The
items below should be resolved as follow-ups, mostly inside the next batch of
v15 work.

### Theme verdicts

| # | Theme | Verdict | Rationale |
|---|---|---|---|
| 1 | Pattern consistency (Literal/coerce/post_init) | **Yellow** | Three actions skip `__post_init__` despite having Literal-able fields; one uses `field(default=...)` redundantly; default-output-name conventions split |
| 2 | Wire-format anomaly handling | **Yellow** | Each anomaly documented in its own file; no central inventory; future authors won't know to check |
| 3 | Test coverage adequacy | **Yellow** | Branch-level coverage is fine but cross-cutting gaps — no parametrized tests per action variant, no oracle-cross-check tests |
| 4 | Code-volume health | **Green** | Largest action 196 lines, all comfortably under 500-line ceiling |
| 5 | Sample-grounding discipline | **Green** | Every action has corpus citations; one `Literal` value (`"When I Leave"`) is speculative and flagged in the per-branch review |
| 6 | Factory-method scaling | **Yellow** | Inconsistent and undocumented; rule needed for V2 |
| 7 | Type-system completeness | **Yellow** | Several `str` fields where `Literal` is appropriate (`AddNewReminder.calendar` is correctly free `str`; `GetItemFromList.index`/`range_*` could be `int | ParamValue`) |
| 8 | Followups consolidated | **Yellow** | 18 follow-ups across the per-branch reviews; some are themes (variable-ref-into-bare-string slots, `raw_params` escape hatch) that should be lifted to V1.5/V2 backlog |

---

## 2. Pattern-consistency table

The ten new action classes plus the modified `TextSplit`. Outliers in
**bold**.

| Action | Lines | Literal types | Factory methods | `__post_init__` | `default_output_name` | Sample citation in source | Wire-equiv test | Notes |
|---|---|---|---|---|---|---|---|---|
| `TextSplit` (modified) | +6 | 1 (pre-existing) | None | Yes (pre-existing) | "Split Text" | Comments | Yes (xfail removed) | Field added to end of `_params()` — minimal |
| `FileRename` | 89 | 0 | None | Yes | "Renamed File" | Yes (extensive) | Yes | Tight. `__post_init__` only validates one cross-field rule |
| `TextCombine` | 85 | 1 | None | **Yes but only validates `separator` literal** | "Combined Text" | Yes | Yes (2x) | `custom_separator`-required check is in `_params()`, not `__post_init__` — split logic |
| `AddNewReminder` | 196 | 2 | None | Yes (3 checks) | "New Reminder" | Yes (extensive) | Yes (1x; 2nd test would help) | Largest. Required-field validation in `__post_init__`, optional-field validation lives there too. Could grow factories |
| `SendMessage` | 94 | 0 | None | Yes (1 check) | **None set** | Module-level note | Yes (2x) | No `default_output_name` — defensible (action has no output), but not stated in source |
| `PreviewDocument` | 35 | 0 | None | **No** | "Quick Look" | Comments | Yes | Smallest. No validation at all (`input` is the only field) |
| `FilterCalendarEvents` | 116 | 0 | None | **No** | "Calendar Events" | Yes (very thorough) | Yes | Pass-through dict. Per-branch review flagged missing `__post_init__` dict-type guard. **Confirmed not added** |
| `ShowResult` | 40 | 0 | None | **No** | **None set** | Comments | Yes (2x) | Single-field action. The `coerced != ""` pattern is borrowed from `ShowNotification` — good reuse |
| `ChooseFromList` | 64 | 0 | None | **No** | "Chosen Item" | In docstring | Yes (2x) | `select_all_initially` is Jellycore-only; comment is at class level only, not field level |
| `GetItemFromList` | 167 | 1 | **5 factories** | Yes (4 checks) | "Item from List" | Yes | Yes | The only V1.5 action with factories. `list_input` rename is a friction point |
| `Count` | 62 | 1 | **None** (could have one per `count_type`) | Yes (1 check) | "Count" | Yes | Yes (implicit via two unit tests) | No wire-equiv test against the corpus sample |
| `ShowAlert` | 51 | 0 | None | **No** | **None set** | Yes (in docstring) | Yes (2x) | Mirrors `ShowNotification` structure exactly. Best-aligned to existing pattern |

### Pattern outliers worth fixing before merge

**O1.** `TextCombine.__post_init__` validates `separator` against the
literal frozenset, but the *cross-field* check (`Custom` requires
`custom_separator`) lives inside `_params()`. The same split exists in
`TextSplit` (V1) — but inconsistency with `AddNewReminder` and
`GetItemFromList` (which do all validation in `__post_init__`) is now
visible. Decide whether the pattern is "validate-Literal-in-`__post_init__`,
validate-cross-field-in-`_params`" or "validate-both-in-`__post_init__`",
and apply uniformly. The latter is better — it surfaces invalid combinations
at construction time, which an LLM author can recover from synchronously.

**O2.** `FilterCalendarEvents` has no `__post_init__` despite accepting a
free-form dict. Per-branch review N1 flagged this — a non-dict input
silently produces broken wire output. Add the two-line guard:

```python
def __post_init__(self) -> None:
    if self.content_item_filter is not None and not isinstance(
        self.content_item_filter, dict
    ):
        raise SchemaError(
            f"content_item_filter must be a dict or None, "
            f"got {type(self.content_item_filter).__name__}"
        )
```

**O3.** `ChooseFromList` has the same problem: no `__post_init__` despite
`select_multiple` and `select_all_initially` having a documented
relationship (the latter only matters when the former is True). Either
enforce this with a `__post_init__` check (and surface the right
SchemaError) or delete the relationship from the docstring. Currently the
docstring claims the relationship exists and the schema doesn't verify it.

**O4.** `default_output_name` choices show subtle inconsistency. `SendMessage`,
`ShowResult`, and `ShowAlert` deliberately omit it (zero-output actions).
But the test `test_default_output_name` exists for `AddNewReminder`,
`GetItemFromList`, `ChooseFromList` and verifies a specific Apple-emitted
value — yet `SendMessage` has no analogous test asserting the absence. The
absence is itself a contract; assert it. Add `assert
SendMessage.default_output_name == ""` to `test_send_message_registered`.

**O5.** `field(default=None)` (with `from dataclasses import field`) is used
in `AddNewReminder`, `SendMessage`, `ShowResult`, `ShowAlert`, `FilterCalendarEvents`,
`GetItemFromList`. But `FileRename`, `PreviewDocument`, `ChooseFromList`,
`Count`, `TextCombine` use bare `= None`. The two are equivalent for
non-mutable defaults — pick one and stick to it. The bare form is shorter
and is the dominant V1 convention (`format_date.py` uses `field(default=...)`
for stylistic consistency only — the underlying values are immutable).
Recommendation: drop the `field(default=...)` wrapper everywhere except
mutable defaults (`field(default_factory=...)`).

---

## 3. Wire-format anomaly catalog

Apple's wire format is inconsistent. The V1.5 batch surfaces enough
exceptions that they deserve a single inventory. This is the catalog the
code lacks today; recommend lifting it into `docs/wire_format_quirks.md` or a
module-level `_QUIRKS` map.

### 3a. Bare (non-`WF`-prefixed) parameter keys

| Action | Bare key | Notes / Sample evidence |
|---|---|---|
| `is.workflow.actions.count` | `Input` | Confirmed in `combine_screenshots_and_share.xml` and `dictionary.xml`. The action's primary input slot uses `Input`, not `WFInput` |
| `is.workflow.actions.showresult` | `Text` | Confirmed in `start_pomodoro.xml[10]`. Capital T, no `WF` prefix. The only Title-Case bare key in the corpus |
| `is.workflow.actions.text.split` | `text`, `separator` | Lowercase. Confirmed in `batch_add_reminders.xml:9` etc |
| `is.workflow.actions.text.combine` | `text` | Lowercase. Confirmed in `dictionary.xml:40`, `sort_lines.xml:2` |
| `is.workflow.actions.text.split` | `Show-text` | Title-Case-with-hyphen. Confirmed in `sort_lines.xml`, `batch_add_reminders.xml:9` |
| `is.workflow.actions.text.combine` | `Show-text` | Same shape as `text.split.Show-text` |
| `is.workflow.actions.dictatetext` | `WFSpeechLanguage`, `WFDictateTextStopListening` | (V1, included for completeness) — these are `WF`-prefixed; *no* anomaly |

### 3b. Default-omission rules (Apple sometimes emits the default explicitly)

| Action | Slot | Default | Apple sometimes emits explicitly? |
|---|---|---|---|
| `text.split` | `separator` | "New Lines" | No (always omitted in observed samples) |
| `text.combine` | `WFTextSeparator` | "New Lines" | **Yes** — `daily_standup.xml` writes it explicitly; `dictionary.xml` and `sort_lines.xml` omit it. The schema chose the "always-omit" path; this loses round-trip fidelity for `daily_standup` |
| `getitemfromlist` | `WFItemSpecifier` | "First Item" | No (always omitted) |
| `count` | `WFCountType` | "Items" | **Yes** — `combine_screenshots_and_share.xml` writes "Items" explicitly; `dictionary.xml` omits. The schema chose "always-emit" |
| `addnewreminder` | `WFAlertEnabled` | (none) | n/a — sometimes absent, sometimes "Alert"/"No Alert" |
| `format.date` | `WFTimeFormatStyle` | (none) | n/a |

The inconsistency is real: `text.combine` chose always-omit (loses round-trip
on `daily_standup`); `count` chose always-emit (loses round-trip on
`dictionary` if anyone tries it). **Document the policy** ("we choose
minimal-output-when-Apple-allows-it") and accept that round-trip fidelity
will be imperfect for verbose Apple emissions. Or: introduce an
`emit_defaults: bool = False` constructor flag that toggles per-action.
The latter is the V2 escape hatch; the former is what V1.5 already does
implicitly. Codify it.

### 3c. Co-emission quirks (related fields appearing without their gating partner)

| Action | Quirk | Sample |
|---|---|---|
| `getitemfromlist` | `WFItemIndex="2"` co-emitted with `WFItemSpecifier="Last Item"` | `tile_last_2_windows.xml` second appearance. Schema drops `WFItemIndex` on round-trip — fidelity loss |
| `addnewreminder` | `WFAlertCondition="When I Arrive"` without `WFAlertEnabled` | `batch_add_reminders.xml:2`. Schema permits this (intentional, sample-grounded) |
| `addnewreminder` | `WFAlertLocationRadius` only with `WFAlertCondition="When I Arrive"`/"When I Leave" | One sample. Schema allows the radius without the condition (could enforce, didn't) |
| `sendmessage` | `IntentAppDefinition` present in some samples, absent in others | Per-branch review notes the comment says "runtime" but it's authoring-time. **Already filed as a docstring nit** |

### 3d. Recommendation: a quirks registry

Add `src/shortcut_lib/schema/quirks.py` with a `WIRE_QUIRKS` map keyed by
identifier, containing per-slot non-`WF`-prefixed keys (one entry per row of
§3a). Three benefits: (1) future authors see at a glance which keys to
expect; (2) a sanity test asserts every schema emitting a non-`WF`-prefixed
key is in the map, catching accidental deviations; (3) iOS-version drift
becomes a single-file diff. The same registry could grow `default_emission`
("omit"/"emit") fields per slot to formalise §3b.

---

## 4. Cross-cutting code smells

### 4a. Test helpers duplicated across eight files

`_load`, `_strip_output_uuids`, `_normalise`, `_find_action` are defined
verbatim (or near-verbatim, with one variant adding a `VariableUUID` strip)
in eight files: `tests/test_wire_format_equivalence.py` (canonical), and
seven of the new V1.5 test files (`file_rename`, `text_combine`,
`add_new_reminder`, `preview_document`, `show_result`, `choose_from_list`,
`alert`). The remaining three new test files (`send_message`,
`filter_calendar_events`, `count`) use a different pattern (inline `_params`
helper or none) — the split is itself worth fixing.

**Fix.** Extract `tests/_wire_helpers.py` exporting `load_decoded`,
`strip_output_uuids` (with the union of all variant strips, including
`VariableUUID`), `normalise_action`, and `find_action`. Update the
canonical equivalence file plus the seven new test files to import. This is
**the single highest-leverage change** in V1.5 Section A — every new action
in Section B onwards inherits it for free.

### 4b. Module-level constant `NEXT_7_DAYS_FILTER` is good — generalise the pattern

`FilterCalendarEvents` exports `NEXT_7_DAYS_FILTER` as a copy-paste starting
point for the most common filter. This is the right call. But it lives in the
action module — fine for one action, awkward when V2 adds the typed
`FilterPredicate` hierarchy that the per-branch review already flagged.

When V2 lands, move `NEXT_7_DAYS_FILTER` to a `presets` module
(`src/shortcut_lib/schema/presets.py`) with cross-action presets:
`NEXT_7_DAYS_DATE_FILTER` (calendar events), `LARGER_THAN_1MB_FILTER` (files),
`STARRED_FILTER` (reminders/notes/photos). The constant is already shaped
correctly for that future.

### 4c. The `coerce_text_field` empty-string check duplicated

`ShowAlert`, `ShowResult`, and `ShowNotification` each contain inline

```python
coerced = coerce_text_field(self.text)
if coerced != "":
    out["Text"] = coerced
```

Lift to `coerce_text_field_or_omit()` in `base.py` returning `None` on empty;
call sites omit the key when result is None. Marginal saving in lines, but
documents the pattern in one place.

### 4d. Speculative `Literal` values aren't flagged in source

`AddNewReminder.WFAlertCondition` includes `"When I Leave"` — zero corpus
evidence, included by symmetry with `"When I Arrive"`. The per-branch review
flagged this and the response was "low risk". That's defensible but the
source comment doesn't say so. Add a one-liner inline:

```python
WFAlertCondition = Literal[
    "At Time",
    "When I Arrive",
    # "When I Leave" — symmetric with "When I Arrive"; not yet in corpus.
    "When I Leave",
]
```

Same convention for any future Literal whose values aren't all sample-confirmed.

### 4e. `select_all_initially` Jellycore-only marker is at class-level only

`ChooseFromList.select_all_initially` is documented in the docstring as
"only meaningful alongside `select_multiple=True`" but not as
"Jellycore-only, no corpus evidence". The per-branch review flagged this
(M1) and the recommendation was a one-line inline comment:

```python
# WFChooseFromListActionSelectAll: Jellycore-only; absent from all corpus samples.
if self.select_all_initially is not None:
    out["WFChooseFromListActionSelectAll"] = self.select_all_initially
```

Apply.

### 4f. `GetItemFromList.index/range_start/range_end` typed too permissively

Currently `ParamValue`. Corpus only shows `int` values for `WFItemIndex`.
Tighten the factory signature to `int | ParamValue` — gives type-checker
support for the dominant call shape while preserving the chained-Output
escape hatch.

### 4g. Two raw-dict pass-throughs share a V2 fate

`AddNewReminder.alert_location_radius` (`WFQuantityFieldValue`) and
`FilterCalendarEvents.content_item_filter` (`WFContentPredicateTableTemplate`)
both punt to `dict[str, Any]`. When V2 introduces the typed `Quantity` value
type and the typed `FilterPredicate` hierarchy, both can adopt — track as
one V2 epic so the pair stays in sync.

---

## 5. Test-pattern gaps — what classes of bug would the current ~95 new tests fail to catch?

The per-branch reviews count 75-100 new tests. Verifying via `git diff
main..<branch> | grep -c "^+def test_"` for each branch: 2 (fu13) + 10
(file-rename) + 13 (text-combine) + 16 (addnewreminder) + 9 (sendmessage) +
7 (preview-document) + 13 (filter-calendarevents) + 9 (showresult) + 16
(choosefromlist) + 34 (list-helpers — both `Count` and `GetItemFromList`) +
11 (alert) = **140 new tests**. Notably more than the per-branch summaries
claim. The full count of *added* tests is healthy.

But classes of bugs the current pattern is structurally weak against:

### 5a. The empty-string vs None-vs-bare-string distinction

Several actions silently treat `""` and `None` differently
(`AddNewReminder.notes`, `AddNewReminder.url`, `ShowAlert.message`,
`ShowResult.text`). The tests cover `None → omit` and `"valid string" → emit`
but rarely cover `"" → ?`.

`ShowAlert.test_alert_omits_empty_message` covers it for one slot.
`ShowResult.test_show_result_empty_string_omits_key` covers it for one slot.
`AddNewReminder.notes=""` is *expected* to emit `""` based on the corpus and
the docstring — but no test asserts this. Add explicit `""` cases for every
text-token-string slot, parametrised:

```python
@pytest.mark.parametrize("value, expect_key", [
    (None,    False),  # omit
    ("",      True),   # emit empty (Apple's pattern)
    ("text",  True),   # emit string
])
def test_notes_emit_rules(value, expect_key) -> None: ...
```

### 5b. Closed-set Literal values: only happy-path tested

Each `Literal` field has `test_invalid_X_raises` (good) and tests for one or
two valid values (incomplete). No action has a parametrised test that
asserts every Literal value emits correctly. `Count` does the right thing —
parametrises over all five `count_type` values. None of the others do.

The bug that would slip through: `AddNewReminder.alert_condition="When I Leave"`
is in the Literal but never tested for emission. If the wire-key spelling was
wrong (`alert_condition="When I Leave"` emitting as `"When-I-Leave"` due to
a typo), no test catches it.

Mechanical fix: parametrise.

### 5c. No oracle cross-check tests for the new actions

`tests/test_envelope_oracle.py` checks every registered leaf action against
`data/observed_envelope_types.json`. New actions added by V1.5 will be
checked automatically (the oracle test discovers them via `_REGISTRY`), but
the oracle has zero observations for some new actions because the scanner
only surfaces actions that emit dict-shaped envelopes. `Count`, `ShowResult`,
`ShowAlert`, `PreviewDocument` will produce warnings (sparse coverage).
That's correct behaviour, but a maintainer reading the test output sees a
mountain of warnings and won't notice if a real divergence appears alongside.

Tighten the oracle output: distinguish "no observations recorded" from
"observations exist but schema emits nothing". Currently both produce a
single warn; the latter is significant, the former is noise.

### 5d. No round-trip-via-RawAction tests

The `tests/test_lift_round_trip.py` infrastructure verifies that decoded
samples can be lifted back into `Shortcut.from_workflow` and re-emitted.
None of the new actions add cases there. A `RawAction`-based round-trip would
be cheap insurance: lift a corpus sample for `AddNewReminder`, re-emit, assert
byte-equal (after UUID strip).

The `tests/test_round_trip.py` (which uses typed actions, not `RawAction`)
similarly hasn't been touched. Add cases per new action — one bare and one
populated — using the same corpus samples already cited in the equivalence
tests.

### 5e. Equivalence tests live in two places

`test_wire_format_equivalence.py` is the canonical home, but the V1.5
batches scattered equivalence tests across the per-action test files:

- `test_action_file_rename.py` has equivalence + the equivalence is *also*
  registered in `test_wire_format_equivalence.py` (per-branch review noted the
  duplication).
- `test_action_text_combine.py` has equivalence inline (not in canonical).
- `test_action_add_new_reminder.py` has equivalence inline (not in canonical).
- `test_action_send_message.py` has equivalence inline (not in canonical).
- `test_action_show_result.py` has equivalence inline.
- `test_action_choose_from_list.py` has equivalence inline.
- `test_action_filter_calendar_events.py` has equivalence inline.
- `test_action_alert.py` has equivalence inline.

Standardise. Either:

- **Option A (preferred):** all equivalence tests live in
  `test_wire_format_equivalence.py`. Per-action files contain only unit
  tests. The unit tests are easier to read; the equivalence file is the
  one-stop shop for "can the schema reproduce this real plist?".
- **Option B:** all equivalence tests live in their per-action file. The
  central file is deleted (or kept only for control-flow equivalence).

The current state is the worst of both — duplication in `file_rename`,
inconsistency everywhere else.

Adopt Option A. The benefit: when adding a new corpus sample, you grep the
equivalence file once.

### 5f. Tests do not cover registry collisions for new actions

`test_registry_visibility.py` has one collision test using a synthetic
`_Probe` class. There's no test asserting that adding a new action with an
already-registered identifier (typo) is caught. `register()` raises
`ValueError` — covered. But the auto-discovery in
`src/shortcut_lib/schema/actions/__init__.py` will re-import the module
silently if the file is duplicated. A defensive test that iterates
`list_actions()` and asserts unique identifiers would catch a copy-paste
mistake. Worth adding once.

---

## 6. Followups consolidated

Compiled from all eleven per-branch reviews + the cross-cutting issues
above, ranked by leverage:

### Blocking before v1.0

(none — V1.5 Section A is acceptable for an internal release)

### Should-fix before V1.5 closes

1. **Extract `tests/_wire_helpers.py`** — migrate the eight test files that
   duplicate `_load`/`_strip_output_uuids`/`_normalise` (§4a).
2. **Standardise equivalence-test home** to `test_wire_format_equivalence.py`;
   move inline equivalence tests out of per-action files (§5e).
3. **Add `__post_init__` dict-type guard** to `FilterCalendarEvents.content_item_filter` (§2 O2).
4. **Add `__post_init__` consistency guard** to `ChooseFromList` for the
   documented `select_all_initially`/`select_multiple` relationship — or
   delete the docstring claim (§2 O3).
5. **Move `TextCombine` cross-field check to `__post_init__`** (§2 O1).
6. **Add `# Jellycore-only` comments** for every speculative Literal value
   (`AddNewReminder."When I Leave"`, the unused `Count` types, etc.) (§4d, §4e).
7. **Tighten `IntentAppDefinition` test comment** in `test_action_send_message.py`
   (per-branch sendmessage §6 — say "shortcut-authoring time", not "runtime").
8. **Standardise `field(default=...)` vs bare-default usage** globally (§2 O5).
9. **Add `default_output_name=""` assertion test** for `SendMessage`,
   `ShowResult`, `ShowAlert` (§2 O4).
10. **Add parametrised empty-string vs None vs valid-string tests** for every
    text-token-string slot (§5a).
11. **Add parametrised tests over every Literal value** — `Count` already does
    this; copy the pattern to `AddNewReminder`, `GetItemFromList`,
    `TextCombine`, `TextSplit` (§5b).

### V1.5 / V2 follow-ups (track as backlog)

13. **`docs/wire_format_quirks.md` or `quirks.py`** — bare-key inventory from §3.
14. **`raw_params` escape hatch on `Action`** — solves the `WFItemIndex`
    co-emission issue generically. Per-branch list-helpers I1.
15. **Factory rule.** Document when factories are warranted. Suggested rule:
    when an action has at least one `Literal`-typed field that gates which
    other fields are valid (`AskForInput`, `GetItemFromList`), provide
    factories. Otherwise default to the bare constructor.
16. **Companion action `is.workflow.actions.properties.calendarevents`** —
    surfaced in `dictionary.xml` next to `filter.calendarevents`. Per-branch V2-2.
17. **Typed `FilterPredicate` hierarchy** for the shared `WFContentPredicateTableTemplate`
    envelope. Per-branch V2-1; pairs with #16.
18. **`Quantity` value type** for `WFQuantityFieldValue` — replaces the
    `dict[str, Any]` pass-through in `AddNewReminder.alert_location_radius`.
19. **`bool ↔ "Alert"/"No Alert"` translation layer** for `AddNewReminder.alert_enabled`.
20. **Tighten `int | ParamValue` annotations** for `GetItemFromList.index/range_start/range_end`. (§4f.)
21. **`coerce_text_field_or_omit` helper** in `base.py`. (§4c.)
22. **Sample for `WFItemSpecifier="Item At Index"`** — schema supports it but no
    corpus sample uses it; equivalence test impossible until a sample lands.
23. **`alert_condition` ↔ `alert_location_radius` co-occurrence rule** — decide:
    enforce or document.
24. **Promote `NEXT_7_DAYS_FILTER`** to a shared `presets.py` once V2 has a typed
    predicate model. (§4b.)
25. **Tighten oracle test output** — distinguish "no observations" from
    "observations exist, schema emits nothing". (§5c.)
26. **`xfail` audit** — two remain (RepeatCount, ChooseFromMenu). Confirm
    non-blocking for v1.0.
27. **Add `default_output_name` assertion tests** for the actions that lack one.
    (§4f rolled into §2 O4.)
28. **Cross-link the `Count.Input` and `text.combine` Jellycore notes.**
    Per-branch list-helpers I3.
29. **Document the emit-defaults vs omit-defaults policy.** §3b.

Split: mechanical (1–9, 27), test-discipline (10–11, 25), documentation
(13, 15, 28–29), V2 substantive (14, 16–21, 24), sample-dependent (22–23, 26).

---

## 7. Merge-order note

The `_SUMMARY.md` proposes batches 1 → 4. That order is fine for action
correctness because the new action files are non-overlapping. The actual
merge-conflict surface is:

### Files modified by multiple branches

**`docs/known_identifiers.md`** — modified by `model-file-rename`,
`model-text-combine`, `model-addnewreminder`, `model-sendmessage`, and
`model-choosefromlist` within Section A. **And** modified to a *different*
state by four out-of-section branches (`fu10`, `fu12`,
`note-to-github-modernize`, `readme-release-notes`).

SHA-256 verification:

| Branch | Hash | Group |
|---|---|---|
| `v15/model-file-rename` | `ea99b712…` | Section A |
| `v15/model-text-combine` | `ea99b712…` | Section A |
| `v15/model-addnewreminder` | `ea99b712…` | Section A |
| `v15/model-sendmessage` | `ea99b712…` | Section A |
| `v15/model-choosefromlist` | `ea99b712…` | Section A |
| `v15/schema-gaps-inventory` | `ea99b712…` | Out-of-section, *aligned with A* |
| `v15/fu10-downloadurl-factories` | `1c2d9afe…` | Out-of-section, **divergent** |
| `v15/fu12-validate-workflow` | `1c2d9afe…` | Out-of-section, **divergent** |
| `v15/note-to-github-modernize` | `1c2d9afe…` | Out-of-section, **divergent** |
| `v15/readme-release-notes` | `1c2d9afe…` | Out-of-section, **divergent** |

This is a **real merge conflict** between the two groups. All five Section A
branches carry an identical regeneration (the `ea99b712` hash); merging them
in any order is silent auto-resolution. But after the first Section A branch
lands, *each of the four `1c2d9afe`-group branches will conflict on
`docs/known_identifiers.md`* on merge — they'll try to undo the corpus
regeneration that Section A introduced.

**Recommendation:** merge the four divergent branches **first**
(`fu10`, `fu12`, `note-to-github-modernize`, `readme-release-notes`) so the
corpus baseline they assume is still on `main`. Then merge any one Section A
branch; git will silently auto-resolve the corpus regeneration into `main`.
Then merge the remaining Section A branches (silent auto-resolve) and
`schema-gaps-inventory` (silent auto-resolve, same hash as Section A).

If you instead merge a Section A branch first, expect to hand-resolve four
conflicts — each conflict will be the same: keep the Section A regeneration,
discard the older content from the four out-of-section branches.

This is the **single concrete merge-order constraint** in the autonomous
batch, and the `_SUMMARY.md` does not flag it. The summary recommends
"Batch 1 first" — that's the right call but for a different reason than the
summary states. Batch 1 contains all four divergent branches; merging Batch 1
first puts the older corpus on `main`, which Section A then cleanly
overwrites.

(Verified by running `git show <branch>:docs/known_identifiers.md |
sha256sum` for each branch in scope.)

**`tests/test_wire_format_equivalence.py`** — modified by `fu13-textsplit-showtext`
(removes the `xfail` decorator and updates the `text_split` test) and by
`model-file-rename` (appends `test_file_rename_wire_format`). Different
hunks, no overlap. Clean merge.

`v15/fu13-textsplit-showtext` should merge **before** any future V1.5
Section A test cleanup that adopts §4a's `_wire_helpers.py` extraction —
the cleanup PR will conflict massively with anything that touches the
canonical equivalence file.

### Test-helper duplication: merge order interaction

Once §4a is applied (extract `tests/_wire_helpers.py`), every per-action
test file that currently duplicates the helpers will need updating. **Do the
extraction in a single dedicated PR after merging all of Section A.** Do not
try to bundle the extraction into one of the per-action branches — it
touches eight files and would conflict with all of the others.

The clean order is therefore:

1. Merge all 11 Section A branches in the `_SUMMARY.md`-recommended order.
2. Run the test suite once to confirm no regressions.
3. **Then** open a single follow-up PR doing the test-helper extraction +
   the equivalence-test consolidation (§5e Option A).

Doing it the other way around (extract first, merge each branch later) will
require you to re-resolve helper-import conflicts in each branch. Avoid.

### `_SUMMARY.md` deletions across branches

Every Section A branch has a stat line like:

```
docs/architecture-review/v15-reviews/_SUMMARY.md   |  99 -------
```

This is because each branch was created **before** the per-branch reviews
were committed to `main`. The branches don't carry the review docs; the
union (review docs + each branch's source/tests) is what `main` will hold
after each merge. Git's three-way merge handles this correctly: the file
exists on `main` (added by the review-commit), the file is absent on the
branch (no change to make), so `main`'s version wins after merge.

**Verify** by dry-running the merge of any one branch:

```sh
git merge --no-commit --no-ff v15/model-file-rename
# Expect: 4 files changed, +420/−11. The 99-line _SUMMARY.md deletion does NOT
# appear because it was only "deleted" relative to the branch's outdated base.
git merge --abort
```

---

## 8. Concluding remarks

V1.5 Section A is good work. Three cross-cutting improvements stand out:

- **§4a — extract test helpers.** Eight files duplicate the same ~30 lines.
  Single highest-leverage change.
- **§3 — wire-format quirks inventory.** Apple's keys are inconsistent
  enough that a one-page reference is worth its weight.
- **§4b/§5 — equivalence-test consolidation.** The current inline-vs-canonical
  split is the worst of both worlds.

After those three, Section A is ready for release. The remaining 24 follow-ups
are real but none blocks v1.0 — most are V2 substantive work rightly deferred.

The biggest remaining gap is the typed `FilterPredicate` hierarchy (V2-1):
every `filter.*` action will need that envelope, and the typed model wants
to derive from at least 4–5 concrete predicate shapes the corpus does not
yet carry. Section B may need sample-collection work before it can model
the next tier.

The fact that the per-branch reviews independently arrived at GREEN
verdicts, and the cross-cutting issues here are mostly *consistency / DRY*
rather than *correctness*, is a strong signal that the V1 patterns
generalised well. The shape of `Action` and `coerce_text_field` is doing
real work; the hardest part of V1.5 was deciding *what to model* (the
`filter_predicate` punt, the `recipients` punt, the `alert_location_radius`
punt), not *how to write the code*. Good place to be heading into v1.0.
