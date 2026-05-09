# Review: v15/model-filter-calendarevents

**Verdict: green with one nice-to-have and one V2 handoff to file**
**Branch:** `v15/model-filter-calendarevents` (head: 0a173a3)
**Reviewer:** Claude Sonnet 4.6 (autonomous, 2026-05-09)

---

## Test result

13/13 passed, 0 failures, 0 skipped. Full pre-commit suite green: ruff lint,
ruff format, ty, uv-lock all pass.

---

## What landed

Two files, 477 lines total:

- `src/shortcut_lib/schema/actions/filter_calendar_events.py` — 116 lines.
  `FilterCalendarEvents` dataclass, 2 modelled fields, module-level
  `NEXT_7_DAYS_FILTER` constant, sample-cited module docstring.
- `tests/test_action_filter_calendar_events.py` — 361 lines. 13 tests
  covering bare invocation, filter-only, filter + input, wire-format
  equivalence (daily_standup second appearance), constant structure,
  registry lookup, default output name, downstream chaining, raw dict
  pass-through with enumeration predicates, identifier, custom output name,
  and explicit `None` for both fields.

---

## Corpus count verified

4 appearances across 3 files, exactly as reported. Breakdown:

| File | Appearances | Has filter | Has input |
|---|---|---|---|
| `daily_standup.xml` | 2 (CF17C893, 5EE01323) | Both | Both |
| `running_late.xml` | 1 (7BB4AD62) | Yes | No |
| `dictionary.xml` | 1 (4710B912) | No | No |

The agent's "3 filter-bearing / 4 total" split is correct: `dictionary.xml`
carries only a UUID — no filter, no input — making it the lone bare/
unconfigured invocation. No other corpus files contain this action identifier.

No `WFContentItemSortProperty`, `WFContentItemSortOrder`, or
`WFContentItemLimitNumber` keys appear in any of the four appearances.
The decision not to model them is well-grounded.

---

## Path B decision

Raw dict pass-through is the right call for V1.5. The predicate envelope
(`WFContentPredicateTableTemplate`) is shared by every `filter.*` action in
the corpus; typing it properly requires cross-validating at minimum five
predicate shapes across multiple actions, none of which has been decoded yet.
Attempting that here would introduce speculative structure from a single
action's data.

The `content_item_filter: dict[str, Any] | None` type annotation is honest
about what the field is, and the module docstring explains the V1.5 decision
clearly. The `NEXT_7_DAYS_FILTER` constant bridges the gap by giving callers
a copy-paste starting point that is directly grounded in real samples.

The `_params()` method does not validate the dict's internal shape — it emits
whatever the caller passes. This is the correct behaviour for a pass-through:
validation without a typed predicate model would be either too loose (checking
a couple of keys) or fabricated (inventing a schema that hasn't been derived
from corpus data). The docstring is explicit that callers should start from
the constant or a decoded sample.

---

## `NEXT_7_DAYS_FILTER` constant

Structurally matches what is observed in the corpus. The constant uses
`WFActionParameterFilterPrefix = 1` (match ALL predicates), which corresponds
to two of the three filter-bearing appearances (`running_late.xml` and
`daily_standup.xml` second appearance, 5EE01323). The first `daily_standup`
appearance (CF17C893) uses `prefix = 0` (match ANY), but that is the outlier
carrying calendar-name enumeration predicates — a more complex use case. The
constant correctly defaults to the simpler, more broadly useful match-ALL
form.

The constant comment above the definition cites all three source files and
explains the prefix semantics. It also carries a shape reference comment
pointing at `daily_standup.xml` second appearance. Sample-citation discipline
is satisfied.

---

## Issues

### Blockers

None.

### Nice-to-have

**N1 — No `__post_init__` dict-type guard on `content_item_filter`.**
Passing a non-dict (e.g. a bare string or a list) to `content_item_filter`
will silently emit garbage wire output — the string lands under
`WFContentItemFilter` and the shortcut will likely crash at runtime on device.
A two-line guard in `__post_init__` would catch this early:

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

This is the same discipline applied in other actions that accept raw
pass-through dicts. Absence here is a minor inconsistency, not a design
error. The existing type annotation (`dict[str, Any] | None`) covers the
static-analysis case, but there is no runtime guard for dynamically-typed
callers. Recommend adding before or shortly after merge.

### V2 handoff

**V2-1 — Typed predicate model for the shared `WFContentPredicateTableTemplate` envelope.**
All `filter.*` actions (calendar events, contacts, files, photos, reminders,
and others in the corpus) share the same `WFContentPredicateTableTemplate`
wrapper and the same set of predicate shape variants (bounded date, enumeration,
bool, string equality, etc.). Modelling this once as a typed `FilterPredicate`
hierarchy and a `ContentPredicateTable` container would unlock type-safe filter
authoring across every filter action in the library. This work was correctly
deferred from V1.5; it belongs on the V2 backlog as a cross-action schema task,
not a per-action fix.

**V2-2 — `is.workflow.actions.properties.calendarevents` companion action.**
`dictionary.xml` shows this identifier appearing immediately after the bare
`filter.calendarevents` invocation. It is not referenced or flagged anywhere
in the `filter_calendar_events.py` source, and it has no model of its own.
The companion is in-corpus and will be needed for workflows that extract
calendar event properties (title, start date, location, etc.) after filtering.
Flag for modelling in the next schema coverage pass.

Neither V2 item was filed as a tracked issue in `docs/issues/` (no issues dir
exists in the repo yet). The V2 predicate model note lives only in the module
docstring. The companion action is not flagged at all in code — it was noted
in the agent's report but did not make it into source comments or docs.
Recommend a follow-up to either create `docs/issues/` and file both items,
or add a `# TODO(V2): model properties.calendarevents companion` comment in
the source so a future agent can pick it up from a grep.

---

## Merge recommendation

Merge. The implementation is clean, sample-grounded, and disciplined: the two
observed fields are modelled, three unobserved fields are explicitly excluded
with justification, the module docstring is the most thorough corpus-citation
in the schema layer so far, and all 13 tests pass against real wire shapes.

Address N1 (the `__post_init__` guard) as a follow-up before or shortly after
merge — it is not blocking but it closes the only meaningful safety gap in the
design. File the V2 predicate model and companion-action items so they are
trackable and not just in prose.
