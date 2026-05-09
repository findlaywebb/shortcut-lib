# Round 2 Architecture Review — Test & Validation Engineer (Cross-Commentary)

**Reviewer lens**: test architecture, failure-space coverage, validation pipeline.
**Date**: 2026-05-09
**Reading**: all six R1 documents.

---

## 1. Strong agreement — proposals that move work into static or build time

### Type-Hawk's Literal migration is Layer 0 made real

The most important single sentence in round 1 comes from the Type-System Hawk:
"every `SchemaError` in `_params` methods is a type-system failure." That framing
is exactly right from a test architecture perspective. Every `SchemaError` that
fires at runtime is a test I have to write. When the Hawk migrates `FormatDate.date_style:
str` to `DateStyle = Literal[...]` and `ty` catches `FormatDate(date_style="custm")`
at import time, my Layer 2 wire-format equivalence test for `FormatDate` no longer
needs to defend the "wrong enum value" case — it can focus entirely on the envelope
shape question that actually caused FU-7. The two layers stop defending the same
ground.

The eight `frozenset` validator migrations the Hawk lists are the highest-density
test-debt reduction I see across all six documents. Each one converts a class of
test I'd otherwise need to write (call-site tests verifying that bad enum values
raise the right error) into dead code, replaced by a red underline in the IDE.
Proposal 1 from the Hawk costs nothing from my perspective and removes work from
mine.

### Pythonic's `Annotated` slot markers and `emit_params` dispatch

Pythonic's Proposal 2 (`Annotated[ParamValue, TextTokenSlot(...)]` plus a shared
`emit_params` dispatch) is the architectural change I most want to see happen,
because it converts the FU-7 root cause from a per-action implementation decision
into a structural invariant enforced at emit time. Once `emit_params` dispatches
coercion based on slot metadata, a new action author cannot introduce a
`WFTextTokenAttachment`-where-Apple-expects-`WFTextTokenString` bug by accident —
they would have to deliberately annotate the slot as `ValueSlot` when it should be
`TextTokenSlot`. That is a code-review catch, not a device-run catch.

The test impact: my Layer 2 wire-format equivalence tests would still exist (they
pin sample-grounded behaviour), but they would stop being the *only* defence against
the FU-7 class. The equivalence tests become regression guards for "the dispatch
assigned the right slot kind," not primary detectors of the bug class. That is the
correct role for Layer 2 — a regression pin, not a discovery mechanism.

### Pythonic's frozen dataclasses close the post-construction mutation gap

Pythonic notes that `fd = FormatDate(date_style="Short"); fd.date_style = "Custom"`
bypasses `__post_init__` validation. From a test perspective, this is a gap I had
not fully reckoned with in R1. If actions are frozen, `__post_init__` validation is
the only path, and it runs at construction — which means my Layer 1 build-validation
tests are sufficient. If actions are mutable, I would need to add mutation tests,
which are unpleasant to write and maintain. Frozen-by-default via `@action` is a
gift to test architecture.

### Wire-Pragmatist's envelope-type scanner (Proposal 3) is Layer 2 done right

The Wire-Pragmatist's `scan_envelope_types.py` proposal — decode all samples, record
`(identifier, param_key, WFSerializationType)` triples, compare against what the
typed schema emits — is essentially the infrastructure for my Layer 2, operationalised
as a data-driven artefact rather than a manually-written test per action. My R1
Proposal 1 (complete wire-format equivalence for all 21 leaf actions) and the
Pragmatist's Proposal 3 are compatible and composing: the scanner produces
`data/observed_envelope_types.json`; my Layer 2 tests consume it as the oracle
rather than duplicating the inspection per-test. This is a better architecture than
my original, and I am endorsing the Pragmatist's formulation over my own.

---

## 2. Disagreements and pushback

### Pythonic's Annotated metadata: decoration or generator?

Pythonic's `Annotated[ParamValue, TextTokenSlot("WFTextActionText")]` proposal is
attractive, but there is a gap between "the slot knows its coercion path" and "I
can generate the validation engine from the slot metadata." Specifically: the
`TextTokenSlot` marker tells `emit_params` which coercion function to call, but it
does not tell the test harness what the correct oracle is. The oracle is the sample.

Concretely: if I want to automatically generate Layer 2 equivalence tests from the
`Annotated` metadata, I need each slot to carry not just `wf_key: str` and a
coercion tag, but also a reference to which sample and action-index demonstrate the
correct wire form. `TextTokenSlot("WFTextActionText")` plus nothing is decorative.
`TextTokenSlot("WFTextActionText", sample="get_text.xml", action_index=0)` is a
test generator.

I am not saying the Pythonic proposal is wrong — it is a large improvement over
the status quo. I am saying the wire-format validation engine can only be
*generated* from the metadata if the metadata contains the sample reference. Without
that, we still have to write the equivalence tests manually, one per action, just as
my R1 Proposal 1 prescribes. The Annotated approach makes it marginally easier (the
oracle is in the metadata rather than in the test file), but it does not eliminate
the per-action test authoring.

**Resolution**: accept Pythonic's `Annotated` pattern, but argue for adding a
`sample: str | None` field to `TextTokenSlot` and `ValueSlot`. The scanner
(Wire-Pragmatist Proposal 3) populates this field from `observed_envelope_types.json`
during a post-sweep refactor step. Then a test generator can produce equivalence
tests automatically for any slot whose `sample` field is non-None.

### Wire-Pragmatist's Proposal 3 (`observed_envelope_types.json`) is distinct from my Layer 2 — and the difference matters

The Pragmatist's scanner builds a JSON file from the sample corpus. My Layer 2 tests
assert that the schema's emit matches the JSON file. These are two separate artefacts
with distinct roles:

- The JSON file is a *record of what Apple actually emits*. It is authoritative for
  the decode direction.
- My Layer 2 test is an *assertion that the schema's authored output matches what
  Apple emits*. It is authoritative for the encode direction.

The distinction matters because they can diverge. If the Pragmatist's scanner runs
against a new iOS 27 sample and updates `observed_envelope_types.json` to show a
different envelope type for `WFURL`, my Layer 2 test will now *fail* — which is the
correct behaviour. The failure signals that the schema needs to be updated to match
the new Apple behaviour. If the JSON file and the Layer 2 test were the same
artefact, that signal would be lost.

What the Pragmatist's Proposal 3 does *not* replace is the full assertion in my test.
The JSON records `(identifier, param_key, WFSerializationType)`. My Layer 2 test
asserts the entire normalised action dict — not just the serialisation type of each
slot, but the full key set, the structure of the Value dict, the presence/absence of
optional keys (e.g. `WFHTTPMethod` suppression for GET). The scanner is a faster
first-pass detector; the full equivalence test is the regression pin. Both are needed.

### LLM-UX's error-message rewrite is valuable but not a substitute for build-time catches

The LLM-UX agent's Proposal 1 is correct and I have no objection to it. The error
message audit is good work. My pushback is narrower: the framing "every SchemaError
is training signal" is right for errors that *should* be runtime — errors the LLM
caused by misunderstanding the API. It is wrong for errors that represent schema
bugs, like the FU-7 class. A `SchemaError("WFDate slot was emitted as
WFTextTokenAttachment; expected WFTextTokenString")` is not training signal for
the LLM author. It is a bug in the schema. The LLM cannot fix it by changing its
call. The fix requires a patch to the action's `_params` method.

The LLM-UX proposal treats all `SchemaError`s as equal; my test architecture treats
them as two distinct classes: (a) authoring errors the LLM can fix by changing
parameters (train the error message for these), and (b) schema implementation bugs
the LLM cannot fix (catch these in Layer 2, not at runtime). Conflating the two
classes leads to error messages that direct the LLM to change its call site when
the real fix is in the schema.

**Resolution**: in the `SchemaError` message template, add a `schema_bug: bool`
field (or a separate exception subclass `SchemaImplementationError`). When the
build-validate layer catches an envelope mismatch, it raises `SchemaImplementationError`
with a message that says "this is a library bug, not an authoring error." The LLM
then knows not to retry with different parameters.

### Strategist's voice-note re-author is an integration test, not a validation layer

The Strategist (Target A) frames the voice-note re-author as a validation exercise:
"decode it, compare buzz output against what the lib emits, iterate until they match
in intent if not in UUID." That is a useful sanity check, but it is not a Layer 2
wire-format equivalence test. The buzz format comparison is coarse — it checks
that the action list looks similar, not that every parameter slot has the correct
serialisation type. The `FormatDate` bug would not have been caught by comparing buzz
output between the hand-built shortcut and the schema-built one, because buzz renders
variable references as `${Name}` regardless of whether the underlying envelope is
`WFTextTokenAttachment` or `WFTextTokenString`.

More specifically: a voice-note shortcut with `TranscribeAudio` and `RecordAudio`
would exercise two of the 14 uncovered actions in my Layer 2 list. But "the shortcut
behaves correctly on a device" is not the same as "the wire-format equivalence test
passes." The device test gives me a pass/fail on the whole shortcut. The equivalence
test gives me a pass/fail per slot. I need the per-slot test to prevent the next
FU-7. The integration test is not a substitute.

**Resolution**: when Target A is authored, pair it with the addition of
`RecordAudio` and `TranscribeAudio` wire-format equivalence tests to
`test_wire_format_equivalence.py`. The private sample (`voice_note_to_github.shortcut`)
is a direct source for the oracle. The strategy of "use real targets to drive test
coverage" is good — but the coverage must be wired in explicitly, not assumed as a
side-effect of device runs.

---

## 3. Synergies and conflicts

### Wire scanner + Hypothesis = property-based testing grounded in observed evidence

The most important synergy across all six documents: Wire-Pragmatist's
`observed_envelope_types.json` (scanner output) combined with my R1 Hypothesis
strategies (Layer 3) produces a test invariant that neither approach achieves alone.

The scanner tells us: "for `GetText.WFTextActionText`, the observed type in all
samples is `WFTextTokenString`." My Hypothesis strategy generates random `GetText`
instances with random parameter values. The combined property test asserts:

```python
@given(_get_text_strategy)
def test_get_text_slot_type_matches_observed_evidence(action: GetText) -> None:
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    slot = params["WFTextActionText"]
    assert slot["WFSerializationType"] == observed_types["is.workflow.actions.gettext"]["WFTextActionText"]
```

This is strictly stronger than either approach alone. The scanner tells us the
oracle for each slot. Hypothesis exercises every reachable combination of parameter
values, not just the sample cases. The combined test would have caught FU-7 for any
`GetText`-alike action across the full combinatorial space — not just for the sample
values I happen to have.

The conflict: this synergy only exists once (a) the scanner has run and populated
`observed_envelope_types.json` and (b) Hypothesis is installed. Currently both are
zero. The correct order is: scanner first (Wire-Pragmatist Proposal 3), then manual
equivalence tests for all 21 actions (my R1 Proposal 1 / Wire-Pragmatist Proposal
1), then Hypothesis strategies that consume the JSON oracle (my R1 Proposal 2).
The scanner produces the oracle; the manual tests pin it; Hypothesis explores the
combination space.

### LLM-UX error rewrite + build-validate layer = LLM sees constraint and canonical fix together

The LLM-UX agent's error message template:

```
{ClassName}.{field} = {bad_value!r}
{What the constraint is}
{What the correct value should be}
Example: {ClassName}({field}={correct_example!r})
```

This is exactly the shape I want my Layer 1 build-validate step to emit when an
authoring error is detected. The trace that reaches the LLM in a `make-shortcut`
session should contain both the constraint (from the Annotated metadata, via the
`Literal` type) and the canonical fix (from the error message template). This
composites cleanly: when `ty` catches `FormatDate(date_style="custm")` at type-check
time, Pyright surfaces the `Literal["None","Short",...,"ISO 8601"]` constraint
inline. When the error escapes to runtime (e.g. via `Any`-typed call), the
`SchemaError` message gives the same information in text form. The LLM receives the
same training signal whether the error is caught statically or at build time.

The conflict arises if the Literal migration (Type-Hawk Proposal 1) and the error
message rewrite (LLM-UX Proposal 1) happen at different times. After the Literal
migration, the `__post_init__` validators for the eight migrated fields become
redundant but harmless. If the error message rewrite improves those same validators
before the Literal migration happens, the improved messages become dead code
immediately after. Sequence matters: do Literal migration first, then tidy the
residual `__post_init__` messages that remain for complex dependent-type cases
(`FormatDate` Custom mode, `AskForInput` Number mode) where static types can't fully
capture the constraint.

### Pythonic's `@action` decorator + my `@pytest.mark.validate` contract

Pythonic's Proposal 3 (`@action("identifier", output="Text")` as the single decorator
for all action classes) has a test-architecture benefit I did not call out in R1: if
the `@action` decorator validates the identifier at class-definition time and raises
on empty identifiers, then the "import the module" step in my test suite becomes a
validation layer for free. Any action module that passes `from
shortcut_lib.schema.actions import *` without raising has a valid identifier. Today,
`Action.identifier = ""` is a valid base-class state; the validation fires only at
`to_action_dict()` call time. Moving the check to import time means my Layer 0 (the
`ty` run) is supplemented by a Python-observable module import check — cheap, fast,
runs on every platform.

### Conflict: Evangelist's MCP server and validation engine ownership

The Evangelist's MCP server proposal wraps the lib's authoring surface as Claude
tools. The `validate_shortcut` tool in that surface is listed as one of the four
MCP tools. This creates an ownership question my R1 did not address: does the
validation engine live in the lib (and the MCP server calls it), or does the MCP
server layer add its own validation on top? If the MCP server adds its own
validation, there are two diverging implementations. If the lib owns the full
validation engine (my Layer 1 + Layer 2, as `validate_shortcut(workflow) -> list[ValidationResult]`), the MCP server gets a correct, maintained validator for free.

The right architecture: the lib exports a `validate_workflow(workflow: dict[str, Any])
-> list[ValidationFinding]` function (or a `Shortcut.validate()` method) that runs
all structural checks — envelope types, required fields, closed-set values — and
returns structured findings. The MCP `validate_shortcut` tool calls this function.
The audit CLI (Evangelist Proposal 3) calls the same function. There is one
implementation, exercised by my test suite, consumed by two surfaces.

---

## 4. Direction questions for the Evangelist

**Question 1.** If `shortcuts-mcp` is consumed by any Claude agent (not just Claude
Code on this machine), the validation engine becomes part of the public contract of
the MCP tool. A `validate_shortcut` tool that returns different results depending
on whether the caller is using the latest lib version vs. a pinned version creates
silent divergence. Does `shortcuts-mcp` ship with a pinned lib version (stable,
versioned, published), or does it always use `HEAD` of `shortcut-lib`? The answer
determines whether my Layer 2 tests need to be versioned as a contract — failing a
Layer 2 test would be a breaking change to the MCP tool's `validate_shortcut`
output.

**Question 2.** The audit CLI (Evangelist Proposal 3 — `shortcut-audit`) is framed
as a read-only, decode-and-analyse tool targeting arbitrary shortcuts from the
internet. That means it must handle `RawAction` passthrough for the 365+ unmodelled
identifiers robustly. Does the audit CLI use my validation engine (Layer 1 + 2
checks on modelled actions only) for the subset it can check, or does it apply a
different analysis pass to unmodelled actions? If it uses the same validators, my
Layer 2 coverage gaps (14 uncovered actions) translate directly into audit CLI
blind spots. If it uses a different pass, there are two analysis implementations
to maintain. I need to know which architecture the Evangelist intends before I
scope the Layer 2 sweep.

**Question 3.** The Evangelist's Proposal 3 tagline is "Before you run a shortcut
from the internet." That is a security posture, not just a correctness posture.
A shortcut that passes all my Layer 1 and Layer 2 structural checks can still exfiltrate
clipboard contents to an attacker-controlled URL — that is a correctly-formed shortcut
that is malicious. Does the audit CLI's scope include security analysis (which my
validation engine does not touch — it is a correctness engine), or is the security
posture aspirational framing for a tool that actually only detects structural
malformation? If security analysis is in scope, it belongs to the `Analyser` class
the Evangelist describes, not to my validation layers, and the two must not be
conflated in the CLI's output or in test coverage.

---

## Summary of positions

| R1 proposal | Test/Val verdict | Reason |
|---|---|---|
| Type-Hawk: Literal migration | Strong yes | Removes 8 test cases I'd otherwise need; gives Layer 0 real teeth |
| Type-Hawk: TypedDict envelopes | Yes, deferred | Addresses FU-7 class at type layer; scope is medium; do after Layer 2 |
| Pythonic: Annotated slot metadata | Conditional yes | Decoration only unless `sample:` reference is added to markers |
| Pythonic: frozen dataclasses | Yes | Closes post-construction mutation gap; simplifies Layer 1 |
| Pythonic: `@action` decorator | Yes | Import-time identifier validation adds free Layer 0 check |
| Wire-Pragmatist: equivalence sweep (Prop 1) | Yes (same as my R1 P1) | Highest ROI; my and Pragmatist's proposals converge here |
| Wire-Pragmatist: envelope scanner JSON (Prop 3) | Yes, adopt as oracle | Distinct from my Layer 2 tests; must remain separate artefacts |
| LLM-UX: error message rewrite | Yes, sequenced after Literal | Messages for dependent-type cases remain load-bearing; others become belt-and-suspenders |
| Strategist: device runs as validation | Reject as Layer 2 substitute | Coarse signal; does not catch per-slot envelope errors |
| Evangelist: MCP `validate_shortcut` tool | Lib-owns-engine pattern | One validation implementation, consumed by two surfaces |

The throughline: the proposals that push validation earlier in the pipeline (static
type checks, `Annotated` metadata dispatch, import-time identifier validation) reduce
the scope of what my runtime test layers need to catch. The proposals that add new
surfaces (MCP server, audit CLI) must consume the same validation engine rather than
layering new checks on top of it. The scanner JSON and the Hypothesis strategies
compose into the strongest property-based test the lib can have — but only after the
manual equivalence tests for all 21 actions are in place as the oracle foundation.
