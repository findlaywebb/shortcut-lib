# Architecture Review — Round 2: Type-System Hawk Cross-Commentary

**Reviewer**: Type-System Hawk
**Round**: 2 — cross-commentary on peer R1 documents
**Date**: 2026-05-09

---

## 1. Strong Agreement

### Wire Pragmatist: the `observed_envelope_types.json` scanner is a type-system win in disguise

The Wire Pragmatist's Proposal 3 — a scanner that builds `data/observed_envelope_types.json`
from decoded samples and asserts schema emit matches observed types — is, mechanically, a
runtime type registry. I endorse it unconditionally, but I want to make the connection
explicit: this JSON file is exactly the evidence base that would justify the `WFTextTokenString`
vs `WFTextTokenAttachment` TypedDict split I proposed in R1 (§2.4). The scanner produces the
empirical record; the TypedDicts encode it in Python's static layer. The two proposals are
complementary, not redundant. Do the scanner first (2 hours, immediate payoff), then make each
observed envelope type a TypedDict (the static layer). The scanner's output is the spec; the
TypedDicts are the implementation. Running pyright over the TypedDicts with the scanner as
ground truth gives you a closed loop: if a new action uses a wrong envelope type, the scanner
flags it AND pyright catches it at the call site where the dict is constructed.

### Test Engineer: Layer 0 framing is correct but the investment ordering is right

The layered validation model in `round1-tests.md` has Layer 0 as static type checking,
correctly identified as "present but underpowered." The Test Engineer then says: do Layer 2
(wire-format equivalence) first, then Layer 3 (Hypothesis). I agree with that ordering for
pragmatic reasons, but I want to strengthen the Layer 0 diagnosis. The Tests engineer writes
"the real return on static typing comes when parameter slots carry enough type information
that passing the wrong kind of value is a type error." That is the entire thesis of my R1.
We are in violent agreement.

Where I actively endorse the Test Engineer's analysis: the observation that "you could delete
`coerce_text_field` entirely and all 277 tests would still pass" is one of the sharpest
sentences in the round. This is not a test coverage problem — it is a type-system poverty
problem. The tests are silent on envelope shape because `coerce_text_field` returns `Any` and
passes through `dict[str, Any]`. Once the TypedDicts land (my Proposal 2), that deletion would
immediately surface as a pyright error at the return type, before any test runs. The layers
reinforce each other: narrower types catch the bug at write time; wire-format equivalence tests
catch it at commit time. Neither alone is sufficient; together they cover the gap.

### Pythonic Architect: `dataclass_transform` and frozen-by-default

I endorse Pythonic Proposal 3 (`@action` decorator with `dataclass_transform`, `frozen=True`
by default) with one caveat noted below. The frozen-by-default position directly addresses
the post-construction mutation footgun the Pythonic agent correctly identifies:
`fd = FormatDate(date_style="Short"); fd.date_style = "Custom"` silently emits a broken
shortcut today. Frozen dataclasses make that a `FrozenInstanceError` at the mutation site —
which is a runtime error, not a type error, but it is immediate and unambiguous rather than
silent until iOS runtime. From the type-system perspective, frozen also enables pyright to
treat the instance as immutable after construction, which improves narrowing in branches that
test a field value.

The `dataclass_transform` annotation is well-specified in PEP 681 and supported in pyright
1.1.350+ and basedpyright. The synthesised `__init__` signature is what makes the type-check
work — without it, every `@register @dataclass` action class gets a generic `__init__(**kwargs)`
from pyright's perspective, which is why pyright currently shrugs at action constructors.
`dataclass_transform` is the mechanism that makes Proposal 1 (Literal migration) actually
visible to callers in IDEs and pyright runs. These two proposals must ship together to realise
their full benefit: Literal field types mean nothing if the `__init__` signature isn't typed.

### LLM-UX Designer: error messages as training signal, but wrong about `_REQUIRED_PARAMS`

The LLM-UX agent correctly identifies that `url: ParamValue, has_default=True` misleads the
LLM into thinking the field is optional. The proposed fix — `_REQUIRED_PARAMS: ClassVar[frozenset[str]]`
as a new class-level attribute — is a reasonable band-aid but I want to endorse the stronger
path: the `has_default` lie disappears entirely when `url: URLParam` has no default, because
pyright will synthesise `url: URLParam` as a required argument in `__init__`. The LLM-UX
description of the ideal `describe_action` output, where `url` shows as `required`, is
achievable by type-narrowing alone — no `_REQUIRED_PARAMS` set needed. The `SlotMeta(required=True)`
annotation from my R1 §2.6 carries the same information through the existing `Annotated`
channel, keeping the requirement co-located with the type rather than in a separate ClassVar.
I endorse the UX outcome; I disagree with the mechanism.

---

## 2. Disagreements and Pushback

### Test Engineer: Hypothesis is not a substitute for the missing type layer

The Test Engineer's Layer 3 (Hypothesis) proposal is correct and well-scoped, but there is a
subtle overreach in framing it as a solution to the combination-space problem. The property test
described:

```python
@given(shortcut_strategy())
def test_schema_to_bplist_never_raises(sc: Shortcut) -> None:
    bplist = sc.to_bplist()
    assert isinstance(bplist, bytes)
```

This test will pass for `GetText(text=42)` — because `text: ParamValue` accepts `int`, pyright
is silent, and `coerce_text_field(42)` will produce something plistlib can serialise. The test
passes. The shortcut is wrong. Hypothesis cannot catch this because the property is "doesn't
raise" — and incorrect types don't raise today, they emit silently wrong wire format. Hypothesis
catches encode/decode asymmetry; it does not catch semantic incorrectness in action parameters.

The fix is not better Hypothesis strategies — it is narrower types. Once `text: TextParam`
only accepts `str | Text | Output | NamedVar | MagicVar`, Hypothesis cannot generate
`text=42` for `GetText` because the strategy would need to produce a `TextParam`. The
strategies would naturally constrain to valid inputs because the types constrain them.
Hypothesis is most powerful when the types are narrow enough to drive meaningful shrinking.
At the current `ParamValue` breadth, Hypothesis strategies are just "generate anything and
hope for a raise." After Literal migration and slot-typed fields, Hypothesis strategies
become "generate any valid input and verify the invariant holds across the valid space."

The sequencing matters: narrow types first, then Hypothesis. Not the other way around.

### Pythonic Architect: `Annotated[ParamValue, TextTokenSlot]` under-delivers vs. actual narrow types

The Pythonic agent's Proposal 2 — slot-kind markers as `Annotated` metadata — is architecturally
sound for the coercion-dispatch problem (eliminating per-action `_params()` duplication).
I use the same `Annotated` channel in my R1 §2.6 for `SlotMeta`. But for the type-checking
problem, `Annotated[ParamValue, TextTokenSlot]` is weaker than it looks. Pyright's type
narrowing on the field still sees `ParamValue` — the full `str | int | float | bool | None |
Action | Value | dict | list` union. The `TextTokenSlot` marker is opaque metadata; pyright
does not narrow on it. So `DownloadURL(url=42)` is still not a pyright error under the
Annotated approach, because `42` is `int` and `int` is in `ParamValue`.

The coercion-dispatch benefit is real and I endorse it. But do not conflate "dispatch is now
automatic" with "invalid inputs are now caught statically." For static catching, you need
`url: URLParam` where `URLParam = str | Text | Output | NamedVar | MagicVar` — which
excludes `int`, `dict`, and `list` explicitly. The Pythonic agent's `TextParam` alias from
their block composition proposal is the right thing; applying `TextParam` at the slot level
delivers the static benefit. `Annotated[ParamValue, TextTokenSlot]` is the dispatch metadata;
`TextParam` (or `URLParam`) is the type constraint. Both are needed; they are different
concerns; conflating them loses the static benefit.

### LLM-UX Designer: the error fires in the wrong place, not just with the wrong message

The LLM-UX agent's §1.3 silent failure taxonomy is the best thing in the round. The grade-C
and grade-D error messages are correctly identified. But the analysis accepts the premise that
errors should fire at `__post_init__` or `_params()` time — it just wants better message
content at those sites. I disagree with the premise.

`AskForInput.__post_init__` (grade A in the audit) raises:
```
AskForInput.input_type='URL2' is not a valid Apple input type.
Use one of ['Date', 'Date and Time', 'Number', 'Text', 'Time', 'URL'].
```

This is a good runtime error message. It is also entirely redundant once `input_type:
Literal["Text", "URL", "Number", "Date", "Time", "Date and Time"]` is the field type,
because the IDE red-underlines `input_type='URL2'` before the code runs. The LLM author
sees the error in the tool response from pyright, not from a Python exception. The "error
as training signal" design principle is best served when the signal fires at generation
time, not at runtime — the LLM corrects before the code is even executed. The UX agent is
right that messages should be good; I am saying the best version of this design eliminates
most of these errors from the runtime entirely by making them type errors.

The remaining errors — the ones that genuinely cannot be caught statically, like `url is None`
at `_params()` time for a caller using `Any`-typed code — should absolutely have grade-A
messages. But the goal is to shrink that residual set, not just improve messages in it.

### Evangelist: MCP server's JSON schema surface needs to be driven from Python types

This is addressed separately in §4, but the architecture point belongs here: the Evangelist's
MCP server vision assumes a "schema serialisation layer that converts workflow specs from
Claude's JSON tool calls into Shortcut builder calls." That serialisation layer is the type
system in another form. If `AskForInput`'s `input_type` field is typed as `str` in Python,
then the JSON schema for the MCP tool's `build_shortcut` will accept `"input_type": "bad_value"`
with no validation error — the MCP client will accept it, the lib will accept it, and the error
will surface at iOS runtime. If the Python field is `Literal["Text", "URL", "Number", ...]`,
then `pydantic.model_json_schema()` (or equivalent) generates a JSON schema with `enum:
["Text", "URL", "Number", ...]` that the MCP client validates at protocol level. The type
system's correctness propagates into the MCP wire format automatically. Every lazy `str` in
the Python schema is a hole in the MCP server's validation layer.

---

## 3. Synergies and Conflicts

### TypedDict envelopes + wire-format equivalence scanner = closed audit loop

The most powerful synergy in the round: the Wire Pragmatist's scanner produces
`data/observed_envelope_types.json` empirically. My TypedDict proposal (R1 Proposal 2)
encodes that knowledge statically. The Tests Engineer's Layer 2 (wire-format equivalence
tests) verifies it at commit time. These three form a closed loop:

```
Decoder samples → scanner → observed_envelope_types.json
                          ↓
               TypedDicts encode the observations statically
                          ↓
          pyright catches deviations at write time
                          ↓
       wire-format equivalence tests catch deviations at commit time
```

Any future action addition that misclassifies a slot type gets caught at two independent
gates. This is the architecture that prevents the next FU-7. The three agents who independently
converge on "FU-7 class of bug is the highest-risk open problem" are all correct — and their
individual proposals are individually incomplete. Together they are a defence-in-depth.

### `Var[T]` (Pythonic) + emit-time binding check (Types R1 §2.5 Option B) = correct tradeoff

The Pythonic agent's `Var[T]` generic proposal and my Option B (emit-time variable binding
registry) are the same idea approached from different angles. `Var[T]` is the typed object
that carries the variable reference; the emit-time check is the registry that verifies every
`Var[T]` read has a corresponding write. They compose naturally: the registry uses the `Var`
object's `.name` as the key (rather than a bare string), and can additionally check that the
phantom type `T` matches the write-site type (at least defensively at emit time). This is
not a conflict — it is the complete solution. Either alone is partial.

### `dataclass_transform` + Literal fields = Hypothesis strategies write themselves

Once frozen actions with Literal fields land, the Test Engineer's Hypothesis strategies
collapse from "enumerate all plausible values" to "use `st.from_type(FormatDate)`". Hypothesis
can generate from PEP 681-synthesised `__init__` signatures via `st.builds(FormatDate, ...)`,
and with Literal field types, it will automatically constrain to valid `date_style` values.
The Pythonic `@action` decorator and the Literal migration together make the test strategies
dramatically simpler to write and more semantically correct. This is a genuine force-multiplier.

### Conflict: `_REQUIRED_PARAMS: ClassVar[frozenset]` (LLM-UX) vs. no-default required fields (Types)

The LLM-UX Proposal 1 introduces `_REQUIRED_PARAMS` as a ClassVar to drive `semantic_required`
in `describe_action`. This is in direct conflict with the approach of removing defaults
from required fields. Both cannot be correct simultaneously. If `url: URLParam` has no
dataclass default (my approach), then `has_default` is already `False` and `describe_action`
already knows it is required — no ClassVar needed. If we add `_REQUIRED_PARAMS` alongside
a defaulted `url: URLParam = None`, we have two sources of truth for the same fact and
a maintenance hazard. Resolve this conflict by adopting the no-default path for genuinely
required fields. `_REQUIRED_PARAMS` should be deprecated before it's introduced.

---

## 4. Direction Questions for the Evangelist

**Q1 — MCP tools: do JSON schemas for `build_shortcut` derive from Python types, or are they hand-authored?**

If the MCP server's tool schemas are hand-authored JSON, every `Literal` migration in the
Python schema must also be manually replicated in the MCP tool schema — two places to
maintain, guaranteed to diverge. If they derive from Python types (via `pydantic.model_json_schema`
or similar), then the Literal migration effort has a multiplied payoff: every tighter Python
type automatically tightens the MCP input validation for free, at both the protocol layer
and the LLM-author layer. The Evangelist's "schema serialisation layer that converts workflow
specs from Claude's JSON tool calls" is the pivot point. Which direction does the type
information flow — Python → JSON schema, or JSON schema → Python validation?

**Q2 — If the audit tool decodes arbitrary RoutineHub shortcuts, what is the correctness bar for `RawAction` parameter introspection?**

The audit tool (Greenfield 2.3) needs to emit typed findings: `ExternalCall`, `HardcodedCredential`,
`DataPath`. For typed actions (28 modelled), the `_params` structure is known. For `RawAction`
passthrough (393 − 28 = 365 unmodelled identifiers), the parameters are `dict[str, Any]` with
no type information. The `HardcodedCredential` finder needs to walk parameter values looking
for strings that look like tokens or URLs — which is regex heuristics over `Any`-typed dicts,
not type-safe inspection. Does the strategic vision for the audit tool require expanding the
typed schema coverage to support it, or is heuristic scanning over `raw_params` acceptable?
The answer determines whether the type-system investment is on the critical path for the audit
tool, or whether the audit tool is possible without it.

**Q3 — At what typed-schema coverage does the natural-language compiler (Greenfield 2.2) become viable?**

The compiler front end maps a natural-language intent to action constructors. If the action
constructors have `ParamValue` fields typed as `Any`, the compiler has no structural signal
about whether its generated call is valid — it passes anything and waits for a `SchemaError`.
If the fields are narrowly typed, the compiler can use the schema as a validation oracle:
generate a candidate call, run pyright programmatically (or use runtime type introspection),
get back a structured error if the types don't match, and retry with correction. This is the
"structured output with retry" pattern that instructor and PydanticAI use. What coverage
threshold does the Evangelist consider the minimum viable type richness for the compiler
front end to be something other than blind slot-filling?

---

## Summary

The type-system failures in the current codebase are not isolated — they are the load-bearing
failures that every other agent's proposals depend on to work. The LLM-UX agent's error
messages get more powerful when the errors are type errors. The Test Engineer's Hypothesis
strategies get more meaningful when the strategies are constrained by narrow types. The
Pythonic agent's `Var[T]` and `@action` decorator proposals land cleanly only when
`dataclass_transform` makes the synthesised `__init__` visible to type checkers. The Wire
Pragmatist's envelope scanner produces the evidence base for the TypedDicts. The Evangelist's
MCP server propagates Python type constraints into JSON Schema validation automatically —
but only if the Python types are tight enough to propagate.

The Literal migration (eight fields, one commit) is not a housekeeping task. It is the
prerequisite for almost everything else in this round to deliver its stated value. Do it first.
