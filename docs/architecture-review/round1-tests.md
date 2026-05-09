# Round 1 Architecture Review — Test & Validation Engineer

**Reviewer lens**: test architecture, failure-space coverage, validation pipeline.
**Date**: 2026-05-09

---

## 1. Current-state critique

### What the test suite covers

277 tests, zero Hypothesis. The coverage is sample-driven and mostly
example-based. Breaking it down:

- **Round-trip identity** (`test_round_trip.py`): every committed
  `.shortcut` sample survives `decode → encode → decode`. This is a
  good structural anchor — it proves `plistlib` serialisation is stable
  and `decode/encode` are genuine inverses. It does *not* exercise the
  schema layer at all.

- **Lift round-trip** (`test_lift_round_trip.py`): every sample lifts
  via `Shortcut.from_workflow` and re-emits via `to_workflow`, asserting
  full top-level key equality with an explicit allowlist. This is the
  strongest single test in the file — it surfaced B5 (metadata loss)
  and would catch most future metadata regressions. Scope is still
  bounded to the committed samples.

- **Wire-format equivalence** (`test_wire_format_equivalence.py`): 7
  action tests, each comparing `schema.to_action_dict()` against the
  first matching action in a specific decoded sample. Strong technique;
  shallow coverage. 21 leaf actions exist, 7 are pinned. The remaining
  14 are unchecked by this method.

- **Envelope regression** (`test_envelope_text_token_string.py`): added
  post-FU-7, pins the 9 parameter slots that must emit
  `WFTextTokenString`. Exemplary targeted test — narrow scope, precise
  assertion, low maintenance.

- **Action unit tests** (18 `test_action_*.py` files): happy-path and
  validation-error cases per action. Good coverage of `SchemaError`
  raise paths. Mostly example-based, not adversarial.

- **Schema tier-0** (`test_schema_tier0.py`): 39 named tests covering
  control-flow emit, Text template arithmetic, magic-variable tokens,
  `Self` sentinel binding, registry visibility, `Shortcut.add`
  guards. The most complete single file. Still example-based.

- **No Hypothesis anywhere.** `hypothesis` does not appear in
  `pyproject.toml`, the test files, or the dev-dependencies.

### The FU-7 post-mortem

The envelope bug had three instances (`WFURL`, JSON body values,
`WFDate`). All three shared the same root cause: `coerce_value` for an
`Action`/`Value` produces `WFTextTokenAttachment`, but Apple's runtime
reads those slots as `WFTextTokenString` and silently presents a
disconnected field (empty URL, empty date, unlinked variable).

What the 277 tests missed:

1. **No wire-format equivalence test for `FormatDate`**. If there had
   been one — comparing the schema's `WFDate` emission against the
   decoded sample — it would have failed the moment `coerce_text_field`
   was missing. There was no such test.

2. **The `test_round_trip.py` oracle is blind to this class of bug.**
   Round-trip tests assert `decode(encode(decode(s))) == decode(s)`.
   They say nothing about whether the *emitted* wire format for
   schema-authored shortcuts matches Apple's expectations. A shortcut
   that contains a bare `WFTextTokenAttachment` in a
   `WFTextTokenString`-only slot round-trips happily in Python — the
   plist is well-formed, `plistlib` doesn't care — but Apple's iOS
   runtime silently ignores it.

3. **The build/sign step succeeds with invalid semantics.** `shortcuts
   sign` accepts any well-formed plist. A signed shortcut with wrong
   envelope shapes is fully valid at the AEA layer. There is no build-
   time validation step that inspects semantic structure.

The lesson is not that someone should have written the specific test
that catches the specific bug. The lesson is that **the test suite
creates a false sense of coverage for schema-authored shortcuts**. The
round-trip tests operate on decoded real samples. They cannot catch bugs
in how the schema *generates* action dicts, because the schema doesn't
participate in decoding. The wire-format equivalence tests *can* catch
this class of bug, but they covered 7 of 21 actions, missing the three
that were broken.

### The false-confidence asymmetry

The test architecture contains an implicit claim: "if all round-trips
pass, the lib is correct." That claim is false for a specific but
important class of bugs — envelope shape errors in schema-authored
parameters. The round-trip oracle only exercises the decode→encode
pipeline on real Apple data. It is silent on the schema→emit pipeline,
which is the entire purpose of the library.

Concretely: you could delete `coerce_text_field` entirely and all 277
tests would still pass. The FU-7 bug was invisible to every test until
the shortcut ran on device. That asymmetry is the core problem.

---

## 2. Ideal-state thesis

The validation engine should be layered. Each layer catches a distinct
class of failure, with increasing cost and specificity. The contract
between layers is: a bug caught at layer N should not require layer N+1
to be present.

### Layer 0 — Static type check (`ty`/`pyright`)

**What it catches**: incorrect argument types passed to action
constructors; `None` passed to a required slot; wrong return type from
`_params()`; missing method implementations.

**What it misses**: semantic wire-format errors, envelope shapes,
runtime iOS behaviour.

**Current state**: `ty` runs in `prek` (`uv run ty check`). The
`ParamValue` type alias is defined but most action fields are still
typed `Any`. The type system is present but underpowered for catching
schema misuse.

**Investment needed**: narrowing `Any` slots to `ParamValue`
progressively (SF-batch7 starts this). The real return on static
typing comes when parameter slots carry enough type information that
passing the wrong kind of value is a type error, not a runtime failure.
This is the cheapest layer once the annotations are correct.

### Layer 1 — Build validation

**What it catches**: structural errors at schema emit time — missing
required fields, unknown enum values, `SchemaError` raises. This is
what `__post_init__` validators and `_params()` guards provide.

**What it misses**: silent acceptance of wrong-shaped envelopes (the
FU-7 class), semantic correctness of parameter values at the iOS level.

**Current state**: `__post_init__` validates closed sets for `AskForInput`,
`If.op`, `FormatDate.date_style`, etc. Guards raise `SchemaError` with
diagnostic messages. Coverage is uneven — SF-batch4 is open precisely
because several actions have no validation at all.

**Investment needed**: completing SF-batch4, and — more importantly —
making the *envelope shape itself* part of the build contract. The
`coerce_text_field` helper already does this for known slots. The gap
is identifying all remaining slots that need it (FU-3 extension work).

### Layer 2 — Sample-grounded wire-format equivalence

**What it catches**: the exact FU-7 class of bug. When the schema emits
a shape that differs from what Apple's Shortcuts.app actually produces,
the equivalence test fails.

**What it misses**: action permutations not covered by existing samples,
novel parameter combinations.

**Current state**: 7 of 21 leaf actions covered. Good pattern, weak
coverage. The `test_wire_format_equivalence.py` design is correct and
maintainable.

**Investment needed**: extend to all 21 leaf actions, plus control-flow
constructs, plus the `Text` value (which is load-bearing in every
non-trivial shortcut). This is the single highest-ROI investment in
the current codebase. It directly targets the class of bug that has
already escaped to device.

### Layer 3 — Property-based tests (Hypothesis)

**What it catches**: edge cases in the generate→encode pipeline not
represented by existing samples — empty strings, Unicode surrogates,
very long templates, action graphs with no outputs, control-flow with
empty bodies. Also catches encode/decode asymmetry: if
`decode(encode(x)) != decode(x)` for some generated `x`, it fails.

**What it misses**: iOS semantic correctness (requires device execution).
The iOS runtime has behaviour that no amount of Python-side property
testing can observe.

**Current state**: zero. Not installed.

**Investment needed**: moderate. `hypothesis` is a `pip install` plus
roughly 150 lines of strategy code. The strategies write themselves
naturally given the schema structure. The key strategies are:

- `st.builds(GetText, text=st.text() | named_var_strategy())`
- `st.one_of(*[st.builds(Cls, ...) for Cls in leaf_action_classes])`
- `shortcut_strategy()` — builds a `Shortcut` with 1–10 randomly
  chosen actions, using outputs chained between actions.

The core invariant to test:

```python
@given(shortcut_strategy())
def test_round_trip_property(sc: Shortcut) -> None:
    bplist = sc.to_bplist()
    decoded = plistlib.loads(bplist)
    re_encoded = encode_to_bplist(decoded)
    assert plistlib.loads(re_encoded) == decoded
```

This property test does *not* require device execution. It catches
malformed plist output, broken UTF-16 offset arithmetic, and schema
bugs that cause serialisation errors, across the full combinatorial
space of action combinations — not just the 21 committed samples.

**Note on scope**: Hypothesis is genuinely valuable here, but it should
be **the third investment**, not the first. Wire-format equivalence for
14 uncovered actions (Layer 2) will catch more real bugs per hour of
work than property testing. Hypothesis becomes transformative once
Layer 2 is complete — it tests the *combinations* of the actions whose
individual wire formats are already pinned.

### Layer 4 — macOS smoke test (`shortcuts run`)

**What it catches**: sign failures, bplist rejection at the AEA layer,
and — with careful test shortcut design — simple runtime behaviours like
"this shortcut sets a variable and returns it."

**What it misses**: anything requiring human-in-the-loop (notifications,
clipboard read/write outside a sandboxed context, AI model calls). Most
of the interesting actions in this library are side-effectful.

**Current state**: `test_sign_to_file_round_trips` exercises `shortcuts
sign` and decodes the result. This is the minimal smoke test; it proves
the AEA pipeline works but doesn't run any action logic.

**Investment needed**: A `shortcuts run` test is feasible on macOS but
heavily constrained. The test would need a shortcut that exercises a
headless-safe action path (e.g., a chain of `GetText → SetVariable →
GetVariable → return`). This is not a general-purpose validator. It
is worth one reference test that verifies the sign→run pipeline, but
the return on investment drops sharply beyond that — most runtime
failures are already observable in the FU-7 class, which Layer 2 catches.

**CI shape**: macOS GitHub Actions runners are available and, as of
2026 pricing, their hosted cost has dropped. But running `shortcuts run`
in CI requires a full macOS environment with Shortcuts.app installed;
this works on `macos-latest` but adds 2–4 minutes per run. Gate it
on a `[macos-smoke]` label or run it nightly, not on every PR. For a
personal repo with no remote CI configured today, this is a future
concern.

### Layer 5 — Mock-runtime interpreter (feasibility assessment)

**The idea**: a Python interpreter that walks the action graph with
synthetic inputs, evaluates dataflow (every variable reference
resolves, every `RepeatItem` is in scope, every `RunWorkflow` target
exists), and reports failures without touching a device.

**Verdict: high-cost, low-ROI, do not pursue now.**

The analogy to dbt's DAG validator or Apache Beam's `TestPipeline` is
instructive. Those work because the DSL maps directly to a Python object
graph that is fully inspectable at Python runtime (before submission to
the cluster). Apple Shortcuts does not have this property. The action
identifiers, their input/output schemas, their type constraints, their
dataflow semantics — none of this is exposed in a machine-readable form
that a Python interpreter could consume. The only authoritative source
is Apple's iOS runtime.

A partial mock-runtime — one that validates only dataflow for the subset
of actions with modelled parameters — is implementable but provides
diminishing returns. The bugs it would catch (using `RepeatItem` outside
a `RepeatEach`, referencing an undeclared variable) are already caught
by Layer 1 guards in well-written action code. The bugs it would miss
(wrong envelope shape, wrong wire-format key name, iOS version
incompatibility) are precisely the bugs that escape to device. It
would add significant complexity for incomplete coverage.

If the action library grows to 100+ actions with modelled type
information and a proper schema for input/output types, revisit. At 21
leaf actions with `Any`-typed parameters, the interpreter would be
emulating a type system the schema doesn't yet have.

---

## 3. Top 3 concrete proposals

### Proposal 1 — Complete wire-format equivalence for all 21 leaf actions

**Priority**: 1. Directly targets the FU-7 failure class.
**Size**: ~4 hours. Add one `test_<action>_wire_format` case per action.

For each of the 14 uncovered actions, find (or create) a decoded sample
that exercises the action, then:

1. Extract the first matching action dict from the sample.
2. Normalise (strip UUID, CustomOutputName, OutputUUID).
3. Construct the schema action with parameters that reproduce the sample.
4. Assert dict equality.

When a test fails, it surfaces a real schema bug before it reaches a
device. When it passes, it pins the wire format as a regression barrier.

The 14 uncovered actions are: `AppendVariable`, `Base64Encode`,
`Comment`, `DictateText`, `ExitShortcut`, `FormatDate`, `GetClipboard`,
`GetVariable`, `RecordAudio`, `TextReplace`, `TextSplit`,
`TranscribeAudio`, `UseModel`, `WritingTools` (plus `If`, `RepeatCount`,
`RepeatEach`, `ChooseFromMenu` for control-flow).

Key observation: `FormatDate` would have been caught immediately if a
wire-format equivalence test had existed. The same sample logic that
revealed the bug (`note_.md` instead of `note_<stamp>.md`) would have
been visible as a failing equivalence test in CI before the shortcut
ever touched a device.

**Success criteria**: `test_wire_format_equivalence.py` covers all 21
leaf actions plus the four control-flow constructs. Any regression to
envelope shape, key naming, or parameter structure fails CI before
reaching the sign step.

---

### Proposal 2 — Introduce Hypothesis with a `shortcut_strategy()`

**Priority**: 2. Catches combination-space bugs and encode/decode
asymmetry; makes the "modelled actions are correct in isolation" claim
also apply to "modelled actions compose correctly."
**Size**: ~2–3 hours to introduce, ongoing as new actions are added.

Add `hypothesis` to dev-dependencies and a new file
`tests/test_property_round_trip.py`.

The core strategies:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

# Leaf value strategies
_named_var = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,15}", fullmatch=True).map(NamedVar)
_plain_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), max_size=80
)
_param_value = st.one_of(_plain_text, _named_var)

# Per-action strategies (one per leaf action)
_get_text_strategy = st.builds(GetText, text=_param_value)
_show_notification_strategy = st.builds(
    ShowNotification,
    title=st.one_of(st.none(), _param_value),
    body=_param_value,
)
# ... one per action ...

# Top-level shortcut strategy: 1–8 actions, no inter-action output
# chaining in this first pass (chaining requires knowing action
# output names, add in a second pass)
_any_action = st.one_of(
    _get_text_strategy,
    _show_notification_strategy,
    # ... all action strategies ...
)

_shortcut_strategy = st.builds(
    Shortcut,
    name=st.text(min_size=1, max_size=32),
    actions=st.lists(_any_action, min_size=0, max_size=8),
)
```

Property tests:

```python
@given(_shortcut_strategy)
def test_schema_to_bplist_never_raises(sc: Shortcut) -> None:
    """Any valid Shortcut must produce a well-formed bplist without raising."""
    bplist = sc.to_bplist()
    assert isinstance(bplist, bytes)


@given(_shortcut_strategy)
def test_bplist_round_trip_property(sc: Shortcut) -> None:
    """encode then decode preserves the workflow dict."""
    import plistlib
    workflow = sc.to_workflow()
    decoded = plistlib.loads(encode_to_bplist(workflow))
    assert decoded == workflow
```

The second test is the key one. It asserts that the schema's output
survives the encode→decode cycle — that is, plist serialisation is
stable for any schema-generated workflow, not just the 21 committed
samples. This catches malformed UTF-16 offset arithmetic (a real edge
case in `Text` with surrogate-adjacent Unicode), dict key type
mismatches that plistlib rejects, and action `_params()` methods that
return non-serialisable types.

**Note on false positives**: Hypothesis shrinks failing examples to the
minimal case. When it finds a failure, the output is a 5-line minimal
reproducer that goes directly into a regression test. This is the
opposite of the FU-7 class of failure, where the bug lived in device
behaviour. Hypothesis failures are Python-observable, so the signal-to-
noise ratio is high.

**Note on scope**: do not attempt to test iOS semantic correctness with
Hypothesis. The strategy space for "produces a shortcut that behaves
correctly on iOS" is not modelable in Python. Scope Hypothesis strictly
to the Python-observable invariants: schema doesn't raise, bplist is
well-formed, workflow dict round-trips.

---

### Proposal 3 — `validate-shortcut` pre-flight command in CI

**Priority**: 3. Elevates the wire-format + build checks to a named
boundary that CI can enforce.
**Size**: ~1–2 hours.

Today there is no single command that a CI pipeline can run to say
"this schema change has not introduced a regression." `pytest` runs all
tests including the macOS-only sign test (which silently skips on Linux
via `shutil.which` probes). `prek` runs lint and type checks. There is
no command that runs *only the structural validation tests* — round-trip,
wire-format equivalence, envelope regression — without the sign/run
smoke tests.

Proposal: add a `pytest` mark `@pytest.mark.validate` to every test
that is (a) platform-independent and (b) tests structural correctness
of schema-generated output. Add a `Makefile` target or `[tool.taskipy]`
script:

```
validate-shortcut: uv run pytest -q -m validate
```

This target is fast (~2 seconds, no shell-outs to `shortcuts`), runs on
Linux, and is the command a CI job runs on every push. The macOS smoke
tests run separately under `@pytest.mark.smoke` and are gated on a
`macos-only` CI job that runs nightly or on `[smoke]` PR label.

This proposal has an important secondary effect: it creates explicit
documentation of which tests constitute the structural safety net. When
a new action is added, the author knows they must add at least one
`@pytest.mark.validate` test — the wire-format equivalence test — to
complete the contribution. Without this explicit contract, new actions
arrive without equivalence tests (as the current 14 uncovered actions
demonstrate).

**Success criteria**:

- `uv run pytest -q -m validate` completes in under 5 seconds on any
  platform without requiring macOS tools.
- `uv run pytest -q -m smoke` covers `shortcuts sign` and `shortcuts
  run` and is marked macOS-only with `@pytest.mark.skipif(...)`.
- All future action additions require a wire-format equivalence test
  tagged `@pytest.mark.validate` — enforced by convention, documented
  in `CONTRIBUTING.md` or `docs/handoff.md`.

---

## Summary table

| Layer | Technique | Catches | Current state | ROI |
|---|---|---|---|---|
| 0 | Static type (`ty`) | Wrong arg types | Present, underpowered | High after SF-batch7 |
| 1 | Build validation (`SchemaError`) | Bad parameter values | Uneven | High; SF-batch4 closes gaps |
| 2 | Wire-format equivalence | FU-7 class (envelope shape, key names) | 7/21 actions | **Highest now** |
| 3 | Property-based (Hypothesis) | Combination bugs, encode/decode asymmetry | Zero | High after Layer 2 |
| 4 | macOS smoke (`shortcuts run`) | Sign/AEA failures, simple runtime | Sign only | Low; one reference test |
| 5 | Mock-runtime interpreter | Dataflow, variable scope | — | Low; do not pursue |

The FU-7 bug was a Layer 2 failure. It produced the right plist
structure, the right AEA signature, and correct Python behaviour. The
only place it was visible was in the semantic interpretation of a
specific parameter slot on iOS. Wire-format equivalence is the only
test technique in the above table that operates at that layer — checking
"does the schema emit exactly what Apple's Shortcuts.app emits for this
action?" — and it was not applied to `FormatDate`. That gap cost a
device run.

Close Layer 2 first. Then Layer 3.
