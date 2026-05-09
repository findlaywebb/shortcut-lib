# Round 2 — Wire-Format Pragmatist Cross-Commentary

_Agent: Wire-Format Pragmatist. Persona: Apple's wire format is the source of
truth. Abstractions that don't survive contact with a new sample are technical
debt waiting to bite._

_Re-reading R1: the core thesis holds. 7 of 28 modelled actions have sample-
grounded equivalence tests; the other 21 operate on faith. FU-7 proved faith
is wrong on a known-bad rate of roughly 6/28 slots. The gap is the central
risk in the codebase._

---

## 1. Strong Agreement

### Tests Engineer: wire-format equivalence sweep is the right anchor

The Tests Engineer and I are pointing at the same gap from different angles —
R1-tests §1 names the "false-confidence asymmetry" explicitly: "you could delete
`coerce_text_field` entirely and all 277 tests would still pass." That is an
exact restatement of the tautology problem from R1-wire §1.1.

Strong agreement on sequencing: the Tests Engineer correctly places Layer 2
(wire-format equivalence) before Layer 3 (Hypothesis). This is the right order.
Hypothesis testing random `Shortcut` objects tells you whether the generate→encode
pipeline is structurally stable; it says nothing about whether the emitted
envelope types are what Apple expects. Those are orthogonal questions. Close the
14 uncovered equivalence tests before adding combinatorial pressure over them.

Strong agreement on the `validate-shortcut` mark (R1-tests Proposal 3). A
`pytest -m validate` command that is fast, platform-independent, and covers
structural correctness is exactly the kind of artefact that makes the scanner
idea from R1-wire Proposal 3 (`scripts/scan_envelope_types.py`) testable in CI.
The two proposals compose: the scanner populates `data/observed_envelope_types.json`
and a `@pytest.mark.validate` test asserts the schema's emit matches it.

### Type-System Hawk: TypedDict envelopes are the right structural prevention

R1-types §2.4 proposes TypedDicts for `WFTextTokenString`, `WFTextTokenAttachment`,
and `WFDictionaryFieldValueItem`. This is the correct long-term fix for the FU-7
class of bug. A `WFKey` typo becoming a pyright error rather than a silent iOS
failure is the right direction.

One wire-format note that strengthens this proposal: the TypedDicts need to be
derived from sample evidence, not invented. The `WFTextTokenStringValue` shape
(`{string: str, attachmentsByRange: dict[str, dict[str, Any]]}`) should be
confirmed against a decoded sample before it is frozen into a TypedDict
definition. R1-types proposes this shape but does not cite a sample. I have
confirmed it against multiple samples (the `is.workflow.actions.gettext` and
`is.workflow.actions.shownotification` instances in the decoded XML). The shape
is correct. But every TypedDict field should carry a sample citation as a
comment, or you are hardcoding a structure that only Apple can change without
your knowledge.

### LLM-UX: the `coerce_text_field` invisibility is a real authoring failure

R1-llm-ux §1.3 names the silent-failure taxonomy and puts the `WFTextTokenAttachment`
in a `WFTextTokenString`-only slot at the top of the danger table: "Silent:
field appears blank or 'No URL Specified'". This is the exact FU-7 failure mode.
The LLM-UX framing — that the wire-format distinction is invisible at the `ParamValue`
surface — is the right diagnosis. Every `ParamValue`-typed field looks identical
in `describe_action` output, but some call `coerce_text_field` and some call
`coerce_value` at emit time, and the difference is catastrophic for variable
references.

The Pythonic and Type-Hawk proposals for `Annotated` slot metadata and `Literal`
migration are both correct responses to this diagnosis. My concern is about
sequencing (see §2 below), not direction.

---

## 2. Disagreements and Pushback

### Pythonic: `Annotated` slot metadata *encodes* wire-format facts only if it's sample-grounded

R1-pythonic Proposal 2 introduces `TextTokenSlot` and `ValueSlot` as `Annotated`
markers, and proposes that `_params()` logic be replaced by a shared dispatch:

```python
elif isinstance(slot, TextTokenSlot):
    out[slot.wf_key] = coerce_text_field(value)
```

The mechanism is correct. The risk is in *who assigns the marker*.

Under the proposed dispatch, the marker on a field (`TextTokenSlot` vs `ValueSlot`)
*is* the wire-format claim. If a developer annotates `WFInput` as `ValueSlot`
when the sample shows it should be `TextTokenSlot`, the dispatch emits the wrong
envelope and the test suite passes (because the test checks the schema's output
against the schema's marker, not against a sample). The Annotated-dispatch
approach does not eliminate the need for sample-grounded equivalence tests; it
moves the error from "hardcoded coerce call" to "hardcoded Annotated marker".

The proposal obscures this by making the wire-format claim implicit in a Python
annotation rather than explicit in an inline comment citing a sample file. In the
current codebase, reading `actions/download_url.py` you see `coerce_text_field(self.url)`
directly — that is the claim, visible at the call site. With `Annotated[ParamValue,
TextTokenSlot("WFURL")]`, the claim is in a field annotation that requires reading
through the dispatch machinery to understand.

This is not a reason to reject the proposal. It is a reason to require that every
`TextTokenSlot` or `ValueSlot` annotation include a sample citation in its
`wf_key` docstring or an adjacent inline comment:
`# samples/decoded/download_url.xml line 47: WFURL is WFTextTokenString`. Without
that citation, the Annotated marker is just as hypothetical as the `frozenset`
validators the Type-Hawk correctly wants to eliminate.

### Type-System Hawk: TypedDict envelopes may freeze a schema that drifts

R1-types §2.4 proposes frozen TypedDicts for the wire-format envelope layer. The
`WFTextTokenString` TypedDict has `Value: WFTextTokenStringValue` and
`WFSerializationType: Literal["WFTextTokenString"]`. This is correct for the
current iOS corpus.

The problem: Apple changes these shapes. Not often, but they do. The `WFControlFlowMode`
field already exists in two forms — strings in older shortcuts-js-era shortcuts,
integers in current iOS. If `WFTextTokenString.Value` gains a new required key in
iOS 28 (or renames `attachmentsByRange` to `attachments`), a TypedDict with
`total=True` will cause every `coerce_text_field` call to fail the type checker,
not just the changed slot. The cascade is proportional to how many call sites use
the narrowed return type.

This is not an argument against TypedDicts. It is an argument for `total=False`
with `Required` on the keys that are empirically always present, leaving optional
room for drift. And critically: every TypedDict key should be annotated with the
iOS version range in which it has been observed, so that when a new sample arrives
from a future iOS version the diff to `observed_envelope_types.json` is immediately
interpretable.

The TypedDict layer is the right long-term fix but it is a *brittle* fix unless
it is maintained as a living record, not a static definition.

### Strategist: the iCloud-UUID preservation claim needs verification before B7 is redesigned

R1-strategy §"On iCloud-share and RunWorkflow revival" states: "The research
finding is that iCloud-shared shortcuts *do* preserve UUIDs on share (unlike
locally-signed imports, which get new UUIDs assigned at import). If this is
validated, it would enable genuine multi-shortcut composition for distributed
libraries."

I want to be direct: this claim is unverified in the current corpus. No sample
in the 21 decoded files is an iCloud-imported shortcut. The statement is sourced
from R1-strategy's own footnote ("If this is validated" — the condition has not
been met). The strategic implications are real (deterministic UUIDs for cross-
shortcut composition), but the premise is a hypothesis.

Until a test is done — share a shortcut from a device via iCloud, import it on
a second device, decode the imported file, compare `WFWorkflowIdentifier` against
the original — the B7 `workflow_identifier` determinism work should be scoped to
"correct behaviour" (deterministic from name), not to "unlocks RunWorkflow
composition". The composition story is a bonus if iCloud preserves UUIDs; it is
not a reason to design B7 around that assumption.

The ten-minute test the Strategist describes is worth doing. The result should
be a decoded sample in `samples/decoded/icloud_imported_test.xml` with a comment
noting whether `WFWorkflowIdentifier` was preserved. That sample is either a
green light for composition or a documented proof that the assumption is wrong.
Either outcome is better than building on an unverified research finding.

---

## 3. Synergies and Conflicts

### Synergy: Pythonic slot metadata + Wire scanner = machine-readable source of truth

R1-pythonic Proposal 2 proposes `Annotated[ParamValue, TextTokenSlot("WFURL")]`
as slot metadata. R1-wire Proposal 3 proposes `scripts/scan_envelope_types.py`
that outputs `data/observed_envelope_types.json` as the empirical record.

These two proposals compose into something stronger than either alone: the scanner
produces `{"is.workflow.actions.downloadurl": {"WFURL": "WFTextTokenString"}}` from
sample evidence; the Annotated marker claims the same fact in the type system; a
CI test asserts that every `TextTokenSlot("key")` annotation has a matching entry
in the observed types JSON with the same serialization type. The scanner is the
oracle. The annotation is the in-code claim. The CI test is the bridge.

This means Pythonic's slot metadata proposal is not useful without the scanner,
and the scanner is not actionable without something to assert against. They should
be developed together, in this order: (1) scanner → JSON, (2) write equivalence
tests against the JSON for the 14 uncovered actions, (3) introduce Annotated
markers with dispatch, with the CI test asserting marker-vs-JSON consistency.

### Conflict: don't ship the MCP server before Layer 2 is closed

R1-evangelist Move 1 proposes shipping an MCP server (`shortcuts-mcp`) as the
first public-facing strategic move. The MCP server exposes the lib's authoring
surface — `build_shortcut`, `validate_shortcut` — to any Claude Desktop user.

The conflict: the lib's authoring surface currently has 14 modelled actions with
unverified wire formats. The FU-7 class of bug — correct Python, correct sign,
silent iOS failure for variable references — is undetected for those 14 actions.
If an external Claude Desktop user constructs a `FormatDate` action with a
variable reference in the `WFDate` slot, the shortcut imports successfully, the
`validate_shortcut` tool returns no errors, and the shortcut silently fails on
device. From the user's perspective, `shortcuts-mcp` produced a broken shortcut.
That is a worse first impression than "lib is personal, not yet published."

The sequencing rule: close Layer 2 (equivalence sweep for all 21 leaf actions)
before any public-facing surface is exposed. The MCP server is the right move;
the timing is wrong until the correctness guarantees exist. This is not a
permanent block — the equivalence sweep is estimated at 3–4 hours (R1-wire
Proposal 1). It is a short gate, not a long one.

### Conflict: Hypothesis before equivalence sweep is wasteful

R1-tests Proposal 2 introduces Hypothesis property testing. The Tests Engineer
correctly notes this should be the second investment, not the first. I want to
sharpen this: Hypothesis testing over `_shortcut_strategy()` without complete
wire-format equivalence coverage does not improve correctness — it improves
confidence in the wrong thing. A Hypothesis run over `FormatDate` with random
`date_style` values would tell you the schema doesn't raise for any string in the
closed set. It would not tell you that `WFDate` is emitted as `WFTextTokenString`
not `WFTextTokenAttachment`. The FU-7 class of bug is invisible to Hypothesis.
Add Hypothesis after Layer 2 is complete. Before that it is noise in the CI
budget.

### Synergy: LLM-UX's `semantic_required` + Wire's `RawAction` UUID gap share a fix

R1-llm-ux §1.3 identifies `RawAction.to_action_dict` as a Grade-D error message:
"RawAction needs raw_identifier." R1-wire §1.3 identifies a deeper problem with
freshly-authored `RawAction`s: if `raw_params` does not contain a `UUID` key,
the `self.uuid` field is emitted via `to_action_dict`'s base path — except it
isn't, because `RawAction.to_action_dict` bypasses that base path and emits
`raw_params` as-is. A freshly-authored `RawAction` without a UUID key will produce
a dangling output reference when `.output()` is called.

The LLM-UX fix (improve the error message) and the Wire fix (document and guard
the UUID asymmetry) are both needed and should be done together. The improved
error message for `RawAction` should read:

> `RawAction` requires `raw_identifier` (the Apple action string, e.g.
> `"is.workflow.actions.file.rename"`) and `raw_params` (the decoded wire dict).
> If authoring a new action (not lifting from a decoded shortcut), include a
> `"UUID"` key in `raw_params` to make output references work.
> Example: `RawAction(raw_identifier="...", raw_params={"UUID": str(uuid4()), ...})`

This is one four-line change that closes both the UX gap and the wire-format
gap simultaneously.

---

## 4. Direction Questions for the Evangelist

**1. If `shortcuts-mcp` is published and Apple changes a slot's wire format in
a future iOS release, what is the update and communication path?**

The Evangelist frames the MCP server as "a week of work" (R1-evangelist §2.1).
That week produces the server, but it does not answer: who monitors iOS release
notes for breaking wire-format changes? Who runs the equivalence sweep against
new samples when iOS 27 ships? Who publishes a new server version and how quickly?
The lib is currently a personal tool where the cost of a silent iOS failure is
one bad shortcut on one device. As public infrastructure, a silent failure affects
every Claude Desktop user who has run `claude mcp add shortcuts-mcp`. The
maintenance surface is not additive; it is multiplicative with the number of users.
What is the policy?

**2. The cross-platform DSL (Greenfield 2.4) assumes the lib's Python builder
is a stable intermediate representation. Is it?**

The `Target` protocol proposal assumes that `Shortcut` + action builders are a
runtime-independent IR that a `RaycastBackend` or `N8nBackend` can consume. But
the current builder is tightly coupled to Apple's wire format: `coerce_text_field`
exists because of Apple's runtime semantics, `WFWorkflowTypes` is an Apple enum,
`ShortcutInput` is an Apple magic variable. A Raycast backend does not have
`WFTextTokenString`. Building a cross-platform DSL on top of an Apple-specific
builder means either (a) the backends ignore most of the builder's semantic
machinery, or (b) you introduce a new abstraction layer above the current builder
that is genuinely platform-neutral, making the current builder one backend
implementation rather than the foundation. Which architecture is the Evangelist
proposing?

**3. The `shortcut-audit` tool (Move 3) needs a `RawAction`-grounded analysis
for the 365 unmodelled identifiers. How should it handle actions it cannot
model?**

R1-evangelist §2.3 describes the auditor as walking the decoded action list and
emitting typed findings (ExternalCall, HardcodedCredential, DataPath). For the 28
modelled actions this is feasible — the schema knows what each parameter slot does.
For the 365 unmodelled identifiers (the `is.workflow.actions.file.rename`,
`is.workflow.actions.sendmessage`, and 363 others in `RawAction`), the auditor
must decide: skip them, flag them as "unknown action", or attempt heuristic
analysis of their `raw_params`. Given that `sendmessage` carries contact references
and `addnewreminder` carries location data, skipping the unmodelled 93% of
real-world shortcuts is not a viable "trust rating" strategy. What is the
auditor's stated scope, and how is that scope communicated to the user?

---

_Total: approximately 1,350 words._
