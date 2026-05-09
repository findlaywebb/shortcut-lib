# Architecture Review Round 2 — Product Evangelist

**Reviewer perspective:** Product Lead / Greenfield Evangelist
**Date:** 2026-05-09
**Scope:** Cross-commentary on R1+R2 from the other six agents, plus answers to
the direction questions they posed. Bias toward decisions.

---

## 1. Strong Agreement — Load-bearing infrastructure for "the SDK that ships to iPhone"

Not every proposal is equal. Some are housekeeping. A few are genuinely load-bearing
for the audacious version of the thesis. Those are the ones I want to name explicitly.

### The Literal migration is the multiplier, not just a cleanup

Type-Hawk Proposal 1 — eight `frozenset` validators replaced by `Literal` type aliases
— is the highest-density prerequisite in any of the six documents. Every agent agrees
on it. I want to add a dimension they understated: it is not just a type-safety win.
It is what makes the MCP server's JSON schema correct for free.

Type-Hawk R2 makes this explicit: if `input_type: str` remains in the Python schema,
then `pydantic.model_json_schema()` generates `"input_type": {"type": "string"}` with
no enum constraint in the MCP tool definition. The MCP client accepts `"input_type":
"bad_value"`, the lib accepts it, and the error surfaces on iOS. If `input_type:
Literal["Text", "URL", "Number", "Date", "Time", "Date and Time"]` is the field type,
the JSON schema is `"type": "string", "enum": [...]` automatically. Every Literal
migration in the Python schema is free MCP validation. The eight fields the Hawk
lists are eight holes in the MCP layer that close for the cost of one afternoon's work.

This is the single highest-ratio investment in the codebase. Do it first, before any
other V1 or V2 work starts.

### The wire-format equivalence sweep is the V1 safety gate — full stop

Tests Engineer Proposal 1 and Wire Pragmatist Proposal 1 converge: extend
`test_wire_format_equivalence.py` to all 21 leaf actions before anything public ships.
The FU-7 lesson: a shortcut can be syntactically correct, successfully signed, and
cleanly imported while silently failing for variable references on iOS. That class of
bug is invisible to 277 tests and visible only to the wire-format equivalence tests —
which cover 7 of 21 leaf actions today. Publishing the MCP server before this sweep is
complete means publishing a tool that generates broken shortcuts with no way to explain
why. The sweep takes three to four hours. That is a three-to-four-hour gate on the move
that defines the lib's public reputation.

The Wire Pragmatist's envelope scanner (`scan_envelope_types.py` →
`data/observed_envelope_types.json`) converts this into a living CI artefact. When iOS
27 ships and changes a slot envelope, the scanner makes the regression detectable before
it reaches a user's device. This is "obvious load-bearing infrastructure in retrospect."
Build it alongside the sweep.

### FU-9 (Setup section) is the user-experience gate on shareability

FU-9 (`WFWorkflowImportQuestions`) is the difference between "drag in and run" and
"drag in, open the editor, replace placeholder strings, close, then run." Every real
target requires credentials; without the Setup section every shared shortcut is a DIY
kit. Implement FU-9 alongside Target B as the Strategist recommends. The MCP server's
pitch — "one command, one drag-and-drop, done" — is hollow without it. FU-9 belongs
in the V1 definition.

### Var[T] typed variable coupling is the one V2-era change that pays now

Pythonic Proposal 1 — `Var[T]` typed wrapper around `NamedVar`, threaded through
function signatures — is additive, backward-compatible, and directly prevents the
most dangerous silent failure mode in the voice note builder. Target A has two
sequential GitHub PUTs with audio binary payload; a misspelled `NamedVar` across
those steps produces a silent empty commit on iOS. `Var[T]` threading makes that a
structural Python mistake before any device run. It does not change SKILL.md
conventions, does not require the LLM to learn a new decorator, and does not conflict
with `vault_note_to_git.py`. Include it in the V1 sprint, not V2.

---

## 2. Disagreements and Pushback

### "Personal-tool-first" is a phase, not an identity

The Strategist's pushback on MCP timing is correct. Where I push back: "personal-tool-
first" can calcify into "personal tool forever" if it becomes the project's identity
rather than a phase. Every micro-decision — whether to expose the validation engine as
a lib-level function, whether to invest in factory methods — should be made with the
SDK user in mind even during the personal-tool phase. The reframe: "personal-tool-first
in timeline, SDK-quality in every commit."

### The TypedDict envelope sweep is over-gated, not wrong

Strategy R2 calls TypedDict envelopes "the right idea in the wrong sprint" and every
agent sequences it after the equivalence sweep. I agree on sequence, not framing. The
TypedDict work is not optional in the SDK story. The envelope scanner catches drift
empirically; TypedDicts catch it at pyright time for new code. Both are needed for a
lib that deserves the SDK name. The correct schedule: equivalence sweep complete →
TypedDict migration in the sprint immediately after V1-done, before V2 ambitions.
Not deferred to "someday."

### The `@block` decorator is premature for a specific reason

`@block` is the correct long-term abstraction, but it introduces new vocabulary
(`ShortcutBuilder`, `Var[T]` as return type, the decorator itself) before the existing
vocabulary is stable. Target A will reveal whether the current
`_add_config / _add_polish / _add_push` pattern breaks under real load. If it does,
the pain will indicate the right shape for `@block`. If it does not, `@block` may not
be necessary. Build Target A with the current pattern plus `Var[T]` threading; let
actual friction decide.

### The `@overload` path is a trap; factory methods are the answer

LLM-UX R2's pushback on Type-Hawk's `@overload` for `AskForInput` is correct. Pyright
overload mismatch errors are optimised for human IDEs, not for LLMs parsing error text.
`AskForInput.number(prompt=..., allows_decimal=False)` and `AskForInput.text(prompt=...)`
are better on every axis: the constraint is in the method name, discoverable via
`describe_action`, and errors are the normal missing-argument path, not the opaque
overload-mismatch path. Make factory methods the primary documented form while the
original constructor remains silently functional for back-compat.

`find_action_by_intent` is correctly deferred at 24 actions — revisit at 50. The cheap
alias vocabulary dict ("http" → "DownloadURL") is worth adding now.

---

## 3. Synergies That Compound

### Scanner + TypedDict + Hypothesis: the closed audit loop

No single agent fully articulated this triple compound. The Wire Pragmatist's scanner
produces `observed_envelope_types.json` — empirical record of what Apple emits. The
Type-Hawk's TypedDicts encode that record in Python's static layer. Tests Engineer's
Hypothesis strategies, once `@dataclass_transform` makes Literal fields drive
type-constrained generation, test the full combination space of valid inputs. Together:
the scanner is the oracle, TypedDicts encode it statically, Hypothesis exercises the
combination space against it. Any future action that miscategorises a slot type gets
caught at two independent gates before reaching a user's device. None of the three
proposals is transformative alone; all three form the quality floor that justifies
the SDK label.

### Var[T] + emit-time binding check + LLM-UX error template: from silent to named

`NamedVar` coupling is invisible at every diagnostic layer today. `Var[T]` threading
(Pythonic P1) + emit-time binding check (Types §2.5 Option B) + the LLM-UX standard
error template compose into a complete solution: the variable exists as a Python object,
the emit validates every read has a corresponding write, and the failure message says
"variable 'Polisehd' was referenced but never set" rather than emitting silently. This
is the full solution to an invisible class of iOS runtime failure.

### Target A + FU-9 as the V1 talk-abstract proof point

Together these produce the blog-post sentence: "I described what I wanted, the lib
authored a Shortcuts file, I dragged it onto my phone, filled in one form, and it
worked." That sentence is the talk-proposal abstract for "Your AI Agent Can Now Ship
to iPhone." Everything else is supporting material. Neither alone delivers it: Target A
without FU-9 requires Shortcuts-editor surgery; FU-9 without a compelling target is
infrastructure without a story.

---

## 4. Direction-Question Answers

Every question from every agent's R2 doc, by attribution. Where two agents asked
overlapping questions, answered once with a cross-reference.

---

**Strategy R2 Q1: Personal-tool-first or SDK-first — and is the answer permanent?**

Decision: personal-tool-first in timeline; SDK-quality in every commit. The answer is
not permanent — it is a phase lasting until V1-done (defined in section 5 below). After
V1-done, the MCP server ships and the answer flips. Before that: three real targets, FU-9,
wire-format equivalence for all 21 leaf actions. Not because the SDK vision is wrong but
because a broken first impression in the MCP directory is worse than a later polished
entry. The "personal-tool-first" framing must not slide into "never public" — that
would be the wrong call given the genuine competitive gap. The constraint is time-bounded,
not permanent.

---

**Strategy R2 Q2: What is the minimum bar for "shareable"?**

Decision: the Strategist's higher bar is the right bar. Shareable means: FU-9 Setup
section working (no post-import credential surgery), wire-format equivalence for all 21
leaf actions (no silent iOS failures), and the stale SKILL.md fixed (no contradictory
composition docs). The Evangelist's R1 bar (MCP server, rename, three examples) is the
right marketing bar but the wrong quality bar. A shared shortcut that requires Shortcuts
editor surgery is not shareable in any meaningful sense. FU-9 is a hard prerequisite
for the MCP server, not a nice-to-have.

---

**Strategy R2 Q3: How much does GPL-3.0 constrain the SDK play?**

Decision: GPL-3.0 is compatible with the MCP server strategy but potentially incompatible
with the commercial embedding story. Here is the analysis: an MCP server that users invoke
as a subprocess or network tool is not creating a derivative work of the lib — the callers
are not subject to GPL-3.0. Claude Desktop running `shortcuts-mcp` as an MCP server is not
a GPL violation. However, if the lib is ever used as a library dependency in a commercial
product (embedded in another agent, imported by a SaaS tool), GPL-3.0 requires that
product to be GPL-licensed too. That is the constraint the Strategist correctly flagged.

The decision: GPL-3.0 is the right licence for now. The personal-tool phase and the MCP
server strategy are both fully compatible with it. If the V2 ambition (commercial
embedding in third-party agents) materialises, relicensing to Apache-2.0 or MIT is a
one-commit change before that point. Do not relicense prematurely — GPL-3.0 is a signal
that the lib is built with integrity and not optimised for extraction. Change the licence
when there is a concrete reason to, not in anticipation.

---

**LLM-UX R2 Q1: MCP server discovery surface — JSON spec or Python API?**

Decision: the MCP server exposes a JSON workflow spec as the `build_shortcut` input, not
raw Python code. The spec is a thin declarative layer: `{"actions": [{"type": "AskForInput",
"prompt": "...", "input_type": "Text"}, ...]}`. The lib converts the spec into `s.add(...)`
calls internally. This is the correct design because: (a) it gives Claude Desktop users
(non-Python) a legible representation; (b) the JSON schema for the spec derives from Python
types via `pydantic.model_json_schema()`, so every Literal migration in the Python schema
tightens the MCP input validation automatically; (c) the spec layer is thin — it is a
1:1 mapping of action class names and constructor arguments, not a new semantic layer.

The LLM-UX improvements (Literal enums in `describe_action`, semantic-required markers)
are primarily for the Python/Claude Code authoring path. The MCP spec layer gets the same
constraints automatically via JSON schema derivation. No duplication needed.

---

**LLM-UX R2 Q2: How does `shortcut-audit` communicate the 38% coverage floor?**

Decision: tiered confidence in every audit output, non-negotiable. The audit CLI outputs
three tiers per action: "known" (modelled with wire-format equivalence test), "observed"
(identifier in corpus but not fully modelled — analysis is sample-grounded but heuristic),
and "inferred" (identifier not in corpus — analysis is identifier-name heuristics only).
The overall trust rating (green / yellow / red) weights by the worst tier in any
security-relevant action. A shortcut with one "inferred" action in a data-flow position
gets no better than yellow. The README section "What the audit tool knows and doesn't"
explains this plainly with an example.

This is not an erosion of trust — it is the correct framing. A tool that says "I found no
problems" without caveating its coverage is dangerous. A tool that says "I checked 28 of
the actions this shortcut uses with high confidence; the other 6 were analyzed heuristically"
is honest and more useful.

---

**LLM-UX R2 Q3: iOS version drift and the update path for non-developer MCP users?**

Decision: this is the most important question with the fewest satisfying answers right now.
Here is what I will commit to: before `shortcuts-mcp` is published, the lib ships a
`--check-version` flag on the main CLI that compares `_CLIENT_VERSION` against a pinned
constant in a tiny `versions.yaml` file checked into the repo. When Apple ships iOS 27,
the wire-format scanner runs against new samples, any envelope-type changes are flagged,
the lib is patched, a new version is tagged, and the MCP server directory entry points
to the versioned release. Non-developer users who `claude mcp add shortcuts-mcp` get the
latest stable release, not HEAD.

What I genuinely do not know: whether the MCP directory supports version pinning well
enough to make the update path reliable. This needs a user decision before the MCP server
is published. I am flagging it as an open item, not a blocker to starting the work.

---

**Pythonic R2 Q1: MCP server — parallel build or consequence?**

Decision: consequence, not parallel. The Pythonic, Type-Hawk, and Tests proposals need
approximately three to four weeks of work before the lib's internals justify the SDK
signal. Building the MCP server as a thin wrapper over an imperfect lib and shipping it
to claim the space is the move that produces support tickets. Ship when the lib deserves
the label. The MCP work can be drafted in parallel (writing the server scaffold is a
week), but it should not be published until the Literal migration, equivalence sweep,
FU-9, and at least Target A are complete.

---

**Pythonic R2 Q2: Who is the second user?**

Decision: the second user is a developer who already uses Claude Code and has heard
about Apple Shortcuts automation. Not a RoutineHub power user; not a non-developer.
The second user installs the lib, runs the `make-shortcut` skill, and writes a shortcut
that does something they care about. The `Var[T]` typed coupling, the factory methods,
the `Annotated` slot metadata — all are visible and load-bearing for this user. The
RoutineHub mass audience is the third wave, reached through the `shortcut-audit` CLI
as an on-ramp. The SDK features are not invisible to the second user; they are exactly
what the second user encounters.

This means the Pythonic proposals are blockers for V1, not nice-to-haves. The second
user deserves a lib where `describe_action("AskForInput")` shows `Literal["Text",
"URL", ...]` not `str`, where the error message for a wrong enum value names the
constraint and the fix, and where variable references are structurally typed. That is
the difference between "interesting project" and "I'm using this for real."

---

**Pythonic R2 Q3: Does the cross-platform DSL change the `Action` base-class contract?**

Decision: the cross-platform DSL (Greenfield 2.4) is a V3-era vision, not a V2
direction. I am withdrawing it as a near-term architectural commitment. The Wire
Pragmatist's R2 question is decisive: the current builder is tightly coupled to Apple's
wire format at every layer. A genuinely platform-neutral IR above the current builder
would require a new abstraction layer that makes the Apple backend one implementation
among several. That is a correct architecture but a large scope expansion. Build
`Annotated` slot metadata as a single-backend optimisation (Apple only). If and when
the Raycast/n8n target is seriously pursued, the slot metadata is already the right
foundation for a `CodegenBackend` visitor — but do not design it for that now.

---

**Type-Hawk R2 Q1: MCP tool schemas — Python types → JSON schema, or hand-authored?**

Decision: Python types → JSON schema, always. The `pydantic.model_json_schema()` path
(or equivalent) is the only defensible architecture. Hand-authored JSON schemas are
guaranteed to diverge from Python types within two months. The entire point of the
Literal migration is that it has zero-cost propagation: Python `Literal["Text", "URL"]`
becomes JSON `"enum": ["Text", "URL"]` automatically. Every lazy `str` in the Python
schema is a hole in the MCP wire validation. This is not a decision I am equivocating
on: the schema serialisation layer in the MCP server wraps the Python action registry
and generates tool schemas from it programmatically.

---

**Type-Hawk R2 Q2: Correctness bar for `RawAction` parameter introspection in the audit tool?**

Decision: heuristic scanning over `raw_params` is acceptable for the 365 unmodelled
identifiers, with the tiered confidence framework from LLM-UX R2 Q2 making the
limitation explicit. The audit tool does not require expanding typed schema coverage
to be useful. A `HardcodedCredential` finder that walks `raw_params` for string values
matching token patterns (`ghp_`, `xoxb-`, bearer-token shapes) is correct and valuable
even without full type information. The type-system investment is on the critical path
for the authoring surface; it is parallel-path for the audit surface. Do not hold the
audit tool on type completeness — hold it on honest confidence communication.

---

**Type-Hawk R2 Q3: At what typed-schema coverage does the natural-language compiler become viable?**

Decision: the natural-language compiler (Greenfield 2.2) requires at minimum: Literal
field types for all closed-set parameters (the eight fields from the Hawk's Proposal 1,
plus all new action fields), factory methods for dependent-type constructions
(AskForInput.number, etc.), and slot-type metadata for coercion dispatch. That is
roughly the completion of the Pythonic + Type-Hawk V1 proposals. At that coverage
level, the compiler can use the action registry as a validation oracle: generate a
candidate action call as structured output, validate against the schema's type
information, and retry with the `SchemaError` embedded in the prompt. Below that
coverage — with `ParamValue` and bare `str` fields — the compiler is blind slot-filling
and will silently produce broken shortcuts. The compiler is not viable until the type
infrastructure is complete. This is not a blocker to starting the compiler design; it is
a gate on shipping it.

---

**Tests R2 Q1: Does `shortcuts-mcp` ship with a pinned lib version or HEAD?**

Decision: pinned versioned release, not HEAD. See answer to LLM-UX R2 Q3 above. The
validation engine is part of the MCP tool's public contract; failing a Layer 2
equivalence test after a lib update is a breaking change to `validate_shortcut` output.
The MCP server ships against a specific tagged lib version. When the lib version is
bumped (typically after an iOS update forces a schema change), the MCP server
dependency is updated and a new release is tagged. This requires the lib to be
versioned — which it currently is not, beyond git tags. Before publishing the MCP
server: add `__version__` to the lib, tag a v1.0.0 release, point the MCP server's
dependency at that tag.

---

**Tests R2 Q2: Does the audit CLI use the same validation engine, or a separate analysis pass?**

Decision: one validation engine, consumed by two surfaces. The lib exports
`validate_workflow(workflow: dict) -> list[ValidationFinding]`. The MCP
`validate_shortcut` tool calls it. The audit CLI calls it for the modelled-action
subset and the `Analyser` class (security findings, external calls) runs as a separate
pass over the full decoded action list including `RawAction` passthrough. The two
surfaces compose: the audit output contains both structural findings (from the shared
engine) and security findings (from the Analyser). No diverging implementations.

---

**Tests R2 Q3: Is the audit tool's security posture aspirational or implemented?**

Decision: the V1 audit tool implements security analysis as a distinct named tier,
separate from the structural validation engine. The `Analyser` class walks decoded
action dicts and emits `ExternalCall` (any `DownloadURL` action with a hardcoded URL),
`HardcodedCredential` (string values matching known token patterns), and `DataPath`
(variables containing clipboard content, microphone input, or contact data that flow
into an external call). This is implemented, not aspirational — it is achievable with
regex heuristics over the decoded wire dicts without requiring full type modelling. The
README section "Before you run a shortcut from the internet" names these three finding
types explicitly and explains that `HardcodedCredential` detection is pattern-based
and not exhaustive.

---

**Wire R2 Q1: Update and communication path when Apple changes a wire format?**

Decision: the update path is: (1) new iOS release triggers a manual scan run against
at least one freshly-decoded shortcut built on the new iOS; (2) the scanner
`observed_envelope_types.json` diff reveals any envelope-type changes; (3) if changes
exist, a tagged lib release with the fix ships within one week; (4) the MCP server
dependency is updated and re-published. Communication to users: the MCP server README
lists the iOS version range it has been validated against. Users running `claude mcp
add shortcuts-mcp` get the latest validated release. This policy requires me to run
the scanner within one week of any major iOS release. That is a manual commitment I am
willing to make.

---

**Wire R2 Q2: Is the Python builder a stable IR for a cross-platform DSL?**

Decision: no, it is not, and I was wrong to propose the cross-platform DSL as a
near-term direction. See Pythonic R2 Q3 answer above. The current builder is an
Apple-specific codec, not a platform-neutral IR. The cross-platform vision requires
a new abstraction layer that I am not committing to build before V2.

---

**Wire R2 Q3: How should `shortcut-audit` handle unmodelled identifiers?**

See Type-Hawk R2 Q2 answer above. Heuristic analysis with explicit tiered confidence
communication. "Skip" is not acceptable; "inferred analysis, low confidence" is.

---

## 5. The Minimum Bar — V1 done, V2 starts, what the next 8 weeks look like

V1 is done when: the Literal migration is complete (eight fields, one afternoon, week
of May 12); the envelope-type scanner exists and `observed_envelope_types.json` is
committed (week of May 19); wire-format equivalence tests cover all 21 leaf actions
(week of May 26); FU-9 Setup section is implemented alongside Target B (week of June
2); Targets A, B, and C are authored, imported, and running on device (by June 23);
SKILL.md stale-docs are fixed (this week, not blocked on anything); and `Var[T]`
typed variable coupling is in place before Target A starts.

That is a seven-week V1. By June 23, the lib has: three real distinct-surface shortcuts
as examples, a wire-format equivalence safety net, typed variable coupling, Literal
enum types throughout, and a Setup section that makes every shared shortcut importable
without editor surgery. At that point, the blog post can be written honestly: "here is
what the lib can do, here are its limits, here is the competitive gap it fills."

The MCP server work begins in week three (scaffold, tool definitions, JSON schema
derivation from Python types) but does not ship until the week after June 23 — after
V1 is done. The rename to `shortcuts-sdk` (or `apple-shortcuts-sdk`) can happen at the
same time as the MCP server publication: one README update, one GitHub repo rename, one
MCP directory submission. The rename without the MCP server is noise; the rename with it
is a signal.

V2 ambition starts the week of June 30: the TypedDict envelope layer, the `@action`
decorator with `dataclass_transform`, the `Annotated` slot metadata with dispatch, and
the Hypothesis property-test suite. These are two to three weeks of infrastructure work
that turns the lib from "correct" into "correct and statically verifiable." After V2,
the natural-language compiler (Greenfield 2.2) and the `shortcut-audit` standalone CLI
(Move 3) are the natural next projects — both depend on the type infrastructure being
solid.

The App Intents bridge (Greenfield 2.6) and the cross-platform DSL (Greenfield 2.4)
are deferred indefinitely until the core platform is proven at scale. They are worth
keeping on the public roadmap as vision statements, not work items.
