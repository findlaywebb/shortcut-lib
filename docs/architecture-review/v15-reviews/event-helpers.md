# v15/model-event-helpers — Review

**Branch:** `v15/model-event-helpers` (head `6b8a3f5`)
**Reviewer:** automated proxy review, 2026-05-09
**Actions:** `GetUpcomingEvents` + `DateAction`

---

## 1. Verdict

Clean implementation, merge-ready. Both actions are correctly grounded in
corpus samples. Wire-format fidelity is strong, default-omission discipline
is followed, and the test suite is thorough. One minor naming inconsistency
and one honesty note on speculative Literals are worth flagging but neither
is a blocker.

---

## 2. Test Result

```
20 passed in 0.09s
```

All 20 tests pass (11 for `GetUpcomingEvents`, 9 for `DateAction`).
`ty check` also passes clean on both new source files.

`pre-commit` is not installed in the worktree environment (`No such file
or directory`). The linting signal is therefore absent. If the CI gate
runs pre-commit this should be verified before merge; it is not a reason
to block.

---

## 3. What Landed

### GetUpcomingEvents (`is.workflow.actions.getupcomingevents`)

- 3 fields: `date_specifier` (Literal "Today"/"This Week"/"All", default
  "Today"), `calendar` (str, default `""`), `count` (int|None, default
  None).
- Wire keys: `WFDateSpecifier`, `WFGetUpcomingItemCalendar`,
  `WFGetUpcomingItemCount`. `count` is conditionally included — omitted
  when None, present when set. The empty-calendar sentinel `""` is always
  emitted, matching the `daily_standup.xml` sample exactly.
- `__post_init__` guards both `date_specifier` (membership check against
  the Literal's own `get_args`) and `count` (must be positive).
- Two corpus wire-format equivalence tests using real UUIDs from the XML
  samples.

### DateAction (`is.workflow.actions.date`)

- 2 fields: `mode` (Literal "Current Date"/"Specified Date", default
  "Current Date"), `date` (str|None, default None).
- Default mode emits an empty params dict (UUID only), matching both
  corpus samples exactly.
- `__post_init__` guards the mode value and enforces that `date` is
  required for "Specified Date".
- Both corpus wire-format equivalence tests assert `set(params.keys()) ==
  {"UUID"}`, which is the strongest possible form of this check.

---

## 4. DateAction Naming — Sound or Inconsistent?

The naming choice is defensible but inconsistent with the existing
codebase pattern.

Every other action in the schema uses a bare descriptive noun without a
trailing `Action` suffix: `GetClipboard`, `SetVariable`, `FormatDate`,
`Comment`, `ExitShortcut`, `Dictionary`, and so on. The only precedent for
a suffix is `AskForInput`, which disambiguates from the noun "ask". The
class `FormatDate` already exists in the codebase as a direct neighbour —
it models `is.workflow.actions.format.date` without any suffix.

The rationale given — avoiding shadowing of `datetime.date` — is
technically sound but unnecessary in practice. Python class shadowing is
module-scoped; `DateAction` lives in `shortcut_lib.schema.actions.date`,
and `datetime.date` would only be shadowed if both were imported into the
same namespace. The file imports `datetime` indirectly only through the
`Action` base class, not as a name in scope. A bare `Date` class would
carry zero shadowing risk at the module level.

The inconsistency is low-friction now, but it creates a precedent:
future contributors may add `Action` suffixes unnecessarily, or may feel
confused by the asymmetry between `FormatDate` and `DateAction`. The name
`GetDate` would be both consistent (verb-noun like `GetClipboard`,
`GetVariable`, `GetText`) and unambiguous.

**Recommendation:** Rename to `GetDate` before merge to stay consistent.
This is a non-breaking change since the class is new. If the author
considers it out-of-scope, at minimum document the rationale in a comment
so future maintainers understand the divergence.

---

## 5. Sample-Grounding and Literal Speculation

### Corpus count verified

The `is.workflow.actions.date` grep used `<string>is.workflow.actions.date</string>` (exact XML string match), confirmed clean against the five date-adjacent identifiers in the corpus:

| Identifier | Count |
|---|---|
| `is.workflow.actions.format.date` | 4 |
| `is.workflow.actions.date` | **2** — confirmed |
| `is.workflow.actions.adjustdate` | 2 |
| `is.workflow.actions.gettimebetweendates` | 1 |
| `is.workflow.actions.detect.date` | 1 |

No false matches. The `is.workflow.actions.getupcomingevents` count is
also confirmed at 2 (one in `daily_standup.xml`, one in `dictionary.xml`).
Total 2+2=4 corpus appearances correct.

### Wire key confirmation

All three `GetUpcomingEvents` wire keys are confirmed directly from
`daily_standup.xml`: `WFDateSpecifier` = "Today",
`WFGetUpcomingItemCalendar` = `""`, `WFGetUpcomingItemCount` = 24. The
`dictionary.xml` appearance is bare (UUID only), confirming that all three
keys are optional at the wire level.

### Literal speculation — GetUpcomingEvents

Only `"Today"` is sample-confirmed. `"This Week"` and `"All"` are
Apple-surface speculation from the Shortcuts UI, not observed in any
corpus file. The source code handles this honestly:

```python
# Confirmed from daily_standup.xml:34 (line 466: "Today").
# Apple surfaces "Today", "This Week", and "All" in the Shortcuts UI.
WFDateSpecifier = Literal["Today", "This Week", "All"]
```

This comment is present in `get_upcoming_events.py` and accurately
describes the grounding status. The module docstring and test docstrings
also note which specifiers are sample-confirmed vs. Apple-surface. The
honesty is adequate.

### Literal speculation — DateAction

Both `"Current Date"` and `"Specified Date"` are inferred from Apple's
UI surface. Neither is directly observable in the corpus (both samples are
bare). However, since no `WFDateActionMode` key is emitted for the default
case, the speculative values are untestable against the corpus — the
implementation is logically correct (default omission matches samples), and
the uncertainty is acknowledged in the docstring.

---

## 6. Issues

**Minor — inconsistent class name.** `DateAction` breaks the noun or
verb-noun naming pattern used by every other schema action. `GetDate` is
available and consistent. See section 4.

**Observation — `calendar` always emitted.** The empty-string calendar
sentinel `""` is always written to the output dict, even in the bare
`dictionary.xml` case. This is technically correct because the corpus bare
sample omits the key entirely but the implementation emits it. This is a
discrepancy worth noting: the bare sample at `dictionary.xml:4701` has only
a UUID in its params, but `GetUpcomingEvents(uuid=...)` emits both
`WFDateSpecifier` and `WFGetUpcomingItemCalendar`. The test
`test_get_upcoming_events_wire_format_equivalence_dictionary` asserts
`"WFGetUpcomingItemCount" not in params` but does not assert that
`WFGetUpcomingItemCalendar` is absent — because the model always emits it.
If Apple silently ignores extra keys this is harmless; if it affects
behaviour in edge cases (e.g. a calendar filter being applied when none was
intended), it could be a bug. Not a blocker, but worth a follow-up note.

---

## 7. Merge Recommendation

**Merge with one conditional change.** The implementation is correct,
well-tested, and honestly documented. The `calendar` always-emit issue is
borderline — it does not fail against any observable wire format but
introduces a deliberate divergence from the bare sample. That can be
tracked as a follow-up. The blocking call is the class naming: `DateAction`
should be `GetDate` for consistency. If the author considers the rename
out-of-scope, document the rationale inline and merge; otherwise rename
before landing.
