# Architecture Review Round 2 — LLM-Author UX Cross-Commentary

**Reviewer perspective:** LLM-Author UX Designer
**Date:** 2026-05-09
**Responding to:** round1-pythonic.md, round1-types.md, round1-wire.md,
round1-tests.md, round1-strategy.md, round1-evangelist.md

---

## 1. Strong Agreement

### Type-Hawk's `Literal` migration is the single highest-ROI move for LLM authoring

I flagged this in R1 as Gap 2. Type-Hawk's Proposal 1 (migrate all `frozenset`
validators to `Literal` type annotations, one commit, eight fields) directly
addresses the second most common first-shot failure I observe: Claude writing
`FormatDate(date_style="custom")` (lowercase), `AskForInput(input_type="text")`
(lowercase), or `TextSplit(separator="newlines")` (wrong word). None of these
are caught until `__post_init__` fires — after construction, which in a multi-step
shortcut builder means after several other actions have already been added. The LLM
then has to re-read the error, re-trace which line was wrong, and re-issue the
constructor call.

With `Literal`, a modern IDE (or pyright running in the pre-commit hook) flags the
wrong string at write time, before the LLM has committed any subsequent actions.
More importantly: the LLM, when it queries `describe_action`, will see
`Literal["None", "Short", "Medium", "Long", "Custom", ...]` in the parameter
signature, not `str`. That is enough information to fill the slot correctly on the
first try.

The `UseModel.model` field already proves this works — it is typed `WFLLMModel`
(a `Literal` alias), and I have never seen Claude guess a wrong model name for
`UseModel`, whereas I have seen it guess wrong values for every other closed-set
field. That one data point is strong evidence that `Literal` in the registry output
pays off immediately. Type-Hawk is right to prioritise this above their more
ambitious proposals.

### Wire-Pragmatist's envelope scanner directly solves the most dangerous silent failure I catalogued

My R1 silent-failure taxonomy lists `WFTextTokenAttachment` in a
`WFTextTokenString` slot as the most dangerous class: produces a valid bplist, signs
cleanly, imports without complaint, silently shows a blank field on iOS. An LLM sees
success at every prior check and has no signal to correct on.

Wire-Pragmatist's Proposal 3 (envelope-type scanner, `observed_envelope_types.json`,
CI test) would have caught all six FU-7 regressions at the pre-commit layer. For
LLM-authored shortcuts specifically, this is transformative: the LLM's first-shot
correctness improves only as fast as the feedback loop tightens. Today the loop is:
write Python, run `save_signed`, import on device, observe blank field. With the
scanner baked into CI, the loop becomes: write Python, run `pytest -m validate`,
see a failing test that says "schema emits `WFTextTokenAttachment` but sample shows
`WFTextTokenString` for `WFURL`." That is exactly the error shape I proposed for
`SchemaError` messages in R1 — not "something is wrong" but "this slot expects this
envelope, you gave it that one." The scanner closes the gap that error messages alone
cannot close, because it fires at the structural layer before the LLM's code even
runs.

### Pythonic's `Annotated[ParamValue, TextTokenSlot]` surfaces the coerce-path contract

R1 flagged the `coerce_text_field` vs `coerce_value` distinction as "entirely
invisible to the authoring LLM." Pythonic's Proposal 2 fixes this structurally: slot
markers in `Annotated` metadata, surfaced via `describe_action` via
`get_type_hints(include_extras=True)`. The LLM would see `url: TextTokenSlot` instead
of `url: ParamValue` and understand that this slot has a specific envelope
requirement. It would never need to reason about `coerce_text_field` by name —
the slot annotation is the contract.

This is a clean example of where a structural fix solves an LLM-UX failure mode I
identified but could not fix at the error-message layer. Error messages only help
after the mistake is made. The `Annotated` slot metadata prevents the mistake by
giving the LLM the right constraint at discovery time.

---

## 2. Disagreements and Pushback

### Pythonic's `@block` decorator is structurally correct but wrong for a zero-shot LLM

The `@block` decorator pattern in Pythonic's Proposal 1 is the right abstraction for
a human developer or for a session where the LLM has been primed on the full API.
For a zero-shot LLM encountering this library for the first time, it introduces a
new vocabulary term (`@block`, `Var[T]`, `ShortcutBuilder`) on top of an already
unfamiliar domain. The LLM's first question becomes "what is `@block` and how does
it differ from a plain function?" rather than "what actions do I need for this
shortcut?"

The practical cost: `@block` wraps a function that calls `s.add(...)` and returns
`Var[T]`. That is not hard, but the `Var[T]` return type requires the LLM to know
that (a) it should not call `NamedVar` directly anymore, (b) the typed handle is
what gets threaded between blocks, and (c) the block's `ShortcutBuilder` argument
has a slightly different API than the `Shortcut` instance in examples. This is a
learning cliff exactly where the LLM needs ground to stand on.

A more LLM-friendly version of the same improvement: keep plain Python functions
with explicit `Var[str]` returns, but do not make `@block` mandatory. Let the LLM
use the block pattern as a recommendation in `SKILL.md` examples without it being
the only correct form. The stringly-typed `NamedVar` coupling is the real bug;
the typed threading of `Var[T]` objects solves it without requiring the LLM to
understand a new decorator.

**Concrete recommendation:** Adopt `Var[T]` as Pythonic proposes. Ship `@block` as
an optional decorator in the reference examples but keep plain functions with
`Var[T]` returns as the documented canonical pattern. Make `SKILL.md` show the
plain-function form first.

### Type-Hawk's dependent overloads (`@overload` on `AskForInput`) will produce worse errors than today's `SchemaError`

This is the most important pushback in this document.

Type-Hawk's Proposal 3 introduces `@overload` signatures for `AskForInput` to
express that `allows_decimal` is only valid when `input_type="Number"`. Structurally
correct. The problem is what the LLM sees when it misuses the overload.

Pyright's error message on overload mismatch is notoriously poor. When the LLM
writes `AskForInput(input_type="Text", allows_decimal=True)`, pyright produces
something like:

```
No overloads for "AskForInput" match the provided arguments
Overload 1:   (prompt, input_type: Literal["Number"], ..., allows_decimal: bool | None, ...) -> None
Overload 2:   (prompt, input_type: Literal["Text", "URL", "Date", "Time", "Date and Time"], ...) -> None
```

The LLM now has to diff two overload signatures, determine which arguments it
provided and which overload those map to, and infer the constraint from the absence
of `allows_decimal` in Overload 2. That is a multi-step inference problem presented
as undifferentiated text.

Compare today's `__post_init__` message:

```
AskForInput: allows_decimal is only valid when input_type="Number". Current
input_type="Text". Remove allows_decimal or change input_type to "Number".
```

That message is a single sentence with the constraint stated, the current value
named, and the fix offered. It is better for the LLM than the pyright overload error,
even though it fires later in the build.

Type-Hawk's own alternative suggestion — factory methods (`AskForInput.number(...)`,
`AskForInput.text(...)`) — avoids this problem entirely. Factory methods appear in
`describe_action` output naturally, they don't rely on pyright's overload error
messages, and they tell the LLM "there are two modes, here are their names." This is
the right call for LLM ergonomics. The `@overload` path is a trap that looks correct
from the type-system perspective but degrades the error signal the LLM actually
receives.

**Concrete recommendation:** Adopt factory methods, not `@overload`, for the
dependent-parameter cases. The factory method docstrings and their presence in
`describe_action` output replace the validation error message. The `@overload`
pattern is correct for human IDEs; factory methods are correct for LLM authoring.

### Test-Engineer's Layer 3 (Hypothesis) should not wait behind Layer 2 for LLM-authored shortcuts

Test-Engineer's sequencing is correct for the general case: fill Layer 2 (wire-format
equivalence) before introducing Hypothesis. But for LLM-authored shortcuts
specifically, the Hypothesis `test_schema_to_bplist_never_raises` property is worth
introducing now, before Layer 2 is complete, because it catches a class of failure
the LLM generates that sample-based tests cannot.

The LLM frequently produces unusual parameter combinations: `Text("", substitutions=
{})` (empty template, empty substitutions), `DownloadURL(url=Text("https://example.
com", substitutions={}), body={"key": NamedVar("X")})` (nested structure), or a
`Shortcut` with no actions. These are valid-ish constructions that don't correspond
to any existing sample. Hypothesis will find exactly these edge cases by construction.
The wire-format equivalence tests (Layer 2) test "does this specific action emit
correctly?" — Hypothesis tests "does any combination of actions produce a valid
bplist?" Those are complementary, not sequential.

**Concrete recommendation:** Introduce the minimal Hypothesis suite (the
`test_schema_to_bplist_never_raises` and `test_bplist_round_trip_property` tests)
in parallel with Layer 2 completion, not after. They are independent tests with
different oracles. The LLM-generated failure cases Hypothesis finds will accelerate
the Layer 2 work by surfacing edge cases in uncovered actions.

---

## 3. Synergies and Conflicts

### The triple-layer feedback loop: Wire scanner + Hypothesis + error message rewrite

The strongest compound improvement for LLM authoring is the combination of three
proposals:

1. Wire-Pragmatist's envelope scanner (observed_envelope_types.json + CI test) — fires
   when a *schema class* emits the wrong envelope type for a slot
2. Test-Engineer's Hypothesis `test_bplist_round_trip_property` — fires when a
   *parameter combination* produces a malformed plist
3. My R1 Proposal 1 (SchemaError rewrite to standard template) — fires when the LLM
   passes a wrong value and needs corrective signal to fix it

These three layers now cover the full failure space with consistent signal quality.
The envelope scanner catches structural mistakes before the LLM even runs a shortcut.
Hypothesis catches combinatorial edge cases. The SchemaError rewrite ensures that
when a runtime check fires, the message tells the LLM what to change. None of these
three proposals conflicts with the others; all three together mean the LLM gets
feedback at the right layer with consistent shape: test ID + what was wrong + what
to fix. This is the "errors as training signal" design principle extended to every
layer of the stack.

### The Strategist's voice-note re-author is the acid test for the new API

The Strategy reviewer identified Target A (voice note re-author) as Priority 1.
From the LLM-author UX perspective, Target A is more than a useful shortcut — it
is the litmus test for whether the new API improvements actually reduce first-shot
failure rates in practice. Specifically:

- It exercises `ChooseFromMenu` (control-flow, currently no worked example — my Gap 6)
- It exercises sequential GitHub PUTs with output chaining (the most complex
  dataflow pattern in the current codebase)
- It exercises `Base64Encode` with binary input (not yet wire-format tested)
- It requires the `Var[T]` / `@block` pattern for threading audio output through
  multiple steps

If Claude can author the voice-note shortcut cleanly from scratch, given the
improved `describe_action` output, the `Literal` enum annotations, and the
control-flow example I proposed in R1 Proposal 2, then the API improvements are
validated. If Claude still requires multiple correction turns, those turns identify
exactly which gaps remain.

**Concrete recommendation:** Write Target A explicitly as a benchmark alongside its
useful-shortcut goal. Measure: how many correction turns does Claude need? Which
errors fire? This is the minimum viable user study for the LLM-UX improvements
across all six reviewers.

### Conflict: Pythonic's frozen dataclasses vs. error-message quality

Pythonic's Proposal 3 (`@action` decorator with `frozen=True` by default) is the
right structural move for the general codebase. But it introduces a subtle
LLM-author regression: frozen dataclasses produce `FrozenInstanceError` when the
LLM attempts post-construction mutation, and `FrozenInstanceError` is one of
Python's least informative exceptions for a domain beginner.

The LLM sometimes mutates an action field after construction as a debugging step:
`ask = AskForInput(input_type="Text"); ask.prompt = "Enter value"`. With frozen
dataclasses, this raises `FrozenInstanceError: cannot assign to field 'prompt'`.
The LLM then spends a turn figuring out what frozen means, rather than understanding
that it should just include `prompt` in the constructor call.

The fix is to intercept `FrozenInstanceError` in the `Shortcut.add` path (or in a
custom `__setattr__` on `Action`) and convert it to a `SchemaError` with the
standard template:

```
Action fields are immutable after construction. To change prompt, construct a new
AskForInput with the updated value:
    AskForInput(prompt="Enter value", input_type="Text")
```

This converts a Python implementation detail (frozen dataclass) into a domain-level
message the LLM can act on. It's a small wrapper — ten lines — and it should land
alongside the frozen-default change in Proposal 3.

---

## 4. Direction Questions for the Evangelist

**1. In the MCP server design, what is the discovery surface — and does it need to be
different from what an LLM-in-Python already sees?**

The MCP server exposes tools: `list_available_actions`, `build_shortcut`,
`validate_shortcut`. But "build_shortcut" requires the LLM to specify a workflow
somehow — either as a JSON spec or as Python code. If it is a JSON spec, the spec
needs a schema. If it is Python code, the LLM is back to writing `s.add(...)` calls,
which is what the skills already handle. The question is: for MCP users (Claude
Desktop, not Claude Code), which representation is legible? A JSON spec of action
names and parameters is more discoverable than Python calls, but it requires defining
a new schema layer on top of the Python schema. Does the Evangelist intend the MCP
server to expose the Python API surface directly (via a code-gen tool), or a separate
declarative JSON surface? The answer determines whether the LLM-UX improvements we
are designing (Literal types, semantic-required markers, slot annotations) need to
be duplicated in a JSON schema format, or whether they are already serving the MCP
case via the Python registry.

**2. If `shortcut-audit` becomes a public-facing tool that runs on arbitrary
RoutineHub shortcuts, how does the project communicate the 38% coverage floor to
end users without eroding trust?**

The Wire-Pragmatist established that 38% of identifiers in samples are unmodelled.
For the auditing use case, the lib decodes a stranger's shortcut containing actions
the schema has never seen. The LLM-powered explanation will describe what `RawAction`
passthroughs do based on their identifier names and raw parameter keys — which is
better than nothing but is hypothesis rather than sample-grounded knowledge. For a
security auditor role, the gap between "we know this action does X" and "we infer
this action probably does X based on its identifier string" is significant. What is
the plan for communicating confidence tiers to a non-developer user who is using the
tool to decide whether to run a shortcut from a stranger?

**3. What is the versioning story when Apple ships iOS 27 and changes an envelope
type?**

The Evangelist proposes publishing `shortcuts-mcp` to the MCP directory and renaming
to `shortcuts-sdk`. Both moves create public API commitments. The Wire-Pragmatist
notes that `WFWorkflowClientVersion` is hardcoded and that iOS 26 added 25+ new
actions with zero sample coverage. When Apple changes a wire format in a future iOS
release, MCP server users who have `shortcuts-sdk` added to Claude Desktop will
silently produce broken shortcuts until the lib is updated. The lib does not currently
have a version pinning or deprecation story — it has `_CLIENT_VERSION = "4033.0.4.3"`
in `builder.py`. Before the lib acquires public users via MCP, what is the mechanism
for notifying users that the wire format has drifted, and what does the update path
look like for a non-developer who added the MCP server via `claude mcp add`?
