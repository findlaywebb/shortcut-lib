# Architecture Review — Round 2: Pythonic API (Cross-Commentary)

**Lens**: Declarative, annotation-driven Python. Re-reading R1 through the other agents' findings.

---

## 1. Strong Agreement

### Type-System Hawk Proposal 1 — `Literal` migration for `frozenset` validators

Full endorsement. The Hawk's table in §1.1 lists fifteen runtime exceptions that should be
type errors. My R1 Proposal 2 (`Annotated[ParamValue, SlotKind]`) depends on the field
types being narrowed first — you can't put useful `Annotated` metadata on `str` and expect
the LLM or the type checker to benefit. The `Literal` migration is the precondition for
almost everything else in the Pythonic proposal set. The ordering is clear: Hawk Proposal
1 first, then my Proposal 2, then my Proposal 3. Do not attempt to layer `Annotated` slot
metadata on top of raw `str` fields.

### LLM-UX Designer Proposal 1 — Semantic-required markers in `describe_action`

The UX designer's §1.2 diagnosis that `has_default=True` lies to the LLM about whether
`url` is optional is exactly the same observation I made about `DownloadURL.url: ParamValue`
carrying no semantic signal. Their concrete fix — a `_REQUIRED_PARAMS: ClassVar[frozenset]`
per action class — is pragmatic. It is not my preferred path (I would rather the type
narrowing make `url: URLParam = ...` require a value at construction rather than at emit),
but it is additive, non-breaking, and addressable this week while the type narrowing is
staged. The two approaches are complementary, not alternatives: narrow types solve it
statically; the semantic-required marker solves it in the runtime `describe_action` surface.
Both are needed because the LLM calls `describe_action` at runtime, not `pyright`.

### Tests Engineer Proposal 1 — Wire-format equivalence sweep to all 21 leaf actions

This is the only proposal in any R1 document that directly addresses the FU-7 failure class
at its root. The Tests engineer's framing is exactly right: you could delete `coerce_text_field`
and 277 tests would still pass. That is a structural gap in the test suite, not a coverage
gap. My `Annotated[ParamValue, TextTokenSlot]` proposal (R1 Proposal 2) is a build-time
enforcement mechanism for the same correctness property — but it requires the pattern to be
applied to all 21 actions to be trustworthy. The equivalence sweep is the empirical
validation that tells us whether the `Annotated` migration is complete and correct. The two
proposals should be developed in lockstep: migrate an action to `Annotated` slots, then
confirm it still passes its wire-format equivalence test. Tests Proposal 1 is the CI gate
that validates my Proposal 2.

### Wire-Format Pragmatist Proposal 3 — Envelope-type scanner as a living CI artefact

The scanner script (§3, Proposal 3) produces `data/observed_envelope_types.json` — a
machine-readable record of which serialisation type Apple uses per `(identifier, param_key)`
pair. This is directly load-bearing for my `Annotated` proposal: the slot metadata I want
to encode in `Annotated` (e.g., `TextTokenSlot` vs `ValueSlot`) should be derived from
the scanner's empirical record, not from Jellycore hints or from memory. Without the
scanner's output as a reference, the `Annotated` metadata is a guess. With it, the
migration is grounded. The scanner is the missing data source for my Proposal 2.

### Strategy Agent — Three real targets in priority order

The Strategy document confirms that the three near-term targets (Voice Note re-author,
Quick Task → Daily Note, Share-Sheet → Vault Inbox) each stress exactly the parts of
the schema that most need the typed improvements: `FormatDate`, `DownloadURL`, `Base64Encode`,
`ChooseFromMenu`. The Pythonic proposals are not theoretical niceness — they have concrete
payoff in the three targets the Strategy agent says to build first. Target B (Quick Task →
Daily Note) directly exercises `FormatDate` with the `YYYY-MM-DD-EEEE` pattern, which is
the same action that the FU-7 bug affected. Getting Target B right without a proper
wire-format equivalence test for `FormatDate` would be repeating the same mistake.

---

## 2. Disagreements and Pushback

### Type-System Hawk Proposal 2 (TypedDict envelopes) — right idea, wrong priority

The Hawk's §2.4 proposes TypedDict definitions for `WFTextTokenAttachment`,
`WFTextTokenString`, and `WFDictionaryFieldValue`, arguing that narrowing `coerce_value`'s
return type would have caught FU-7. That is technically true. But the Hawk understates the
cascade cost: narrowing `coerce_value` to return `WFTextTokenString | WFTextTokenAttachment
| str | int | float | bool | None` instead of `Any` will ripple into every action's
`_params()` method. That is 21 methods, most of which were written to accept `Any` from
the coerce helpers. The Hawk budgets "a half-day of pyright error triage" — this is
optimistic by a factor of 3 to 5. Every `_params()` override that does anything interesting
with the return value (branching on type, constructing nested dicts) will produce pyright
errors that require genuine logic inspection, not mechanical annotation changes.

The right sequencing is: TypedDict envelopes come *after* the `Annotated` slot dispatch
(my R1 Proposal 2) is complete. Once `emit_params()` is the central dispatch function and
most actions no longer have hand-written `_params()` overrides, the TypedDict narrowing
is a single-site change with a predictable blast radius. Doing it before the dispatch
centralisation means the cascade multiplies across 21 methods instead of 1. Do not rush
this.

### Type-System Hawk Proposal 3 (dependent `@overload` for `AskForInput`) — factory
functions, not overloads on dataclasses

The Hawk's §2.3 and Proposal 3 recommend `@overload` variants for `AskForInput`, noting
that overloads can't be placed on `__init__` directly for dataclasses and then suggesting
a factory function fallback. The factory function is actually the better answer outright.
`AskForInput.number(prompt="How many?", allows_decimal=False)` is unambiguous at the
call site — no LLM needs to remember which overload fires. But the Hawk's proposed
deprecation of the original constructor with a docstring note is not enough. Deprecated
constructors accumulate; LLMs trained on examples that show
`AskForInput(input_type="Number", ...)` will generate that pattern indefinitely. The
right move is to make the factory methods the *only* documented path in `describe_action`
output, without formally deprecating the original constructor (which breaks existing code).
The factory methods should be surfaced by `describe_action` as the primary usage, and the
base constructor should silently continue to work.

The dataclass `@overload` pattern also has a fundamental problem with `@dataclass_transform`
(my R1 Proposal 3): if you add `@overload` signatures to a dataclass and then wrap the
class with `@action` (which calls `dataclass()` internally), the overloads are replaced by
the synthesised `__init__`. The two proposals conflict. Factory methods have no such
conflict — they are class methods on a normal `@action`-decorated class.

### LLM-UX Designer Proposal 3 (`find_action_by_intent`) — defer until 50+ actions

The UX designer places this at "Medium" priority; I'd push it further out. At 24 actions
the cognitive cost to the LLM of scanning the full `print_actions.py` output is negligible.
The real cost in the current system is not finding the right action — it is passing the
right arguments to the right action. The UX designer's own Proposals 1 and 2 address that
directly; Proposal 3 addresses a problem that is not yet painful. The keyword-matching
approach with an alias vocabulary dict is genuinely cheap, but the 20 lines of alias
maintenance is a recurring cost each time an action is added. The priority should be:
Proposals 1 and 2 fully shipped, 50-action threshold reached, then revisit. Before 50
actions, the gains are in the noise.

### Wire-Format Pragmatist Proposal 2 (model top 5 unmodelled actions) — sequence matters

The Wire Pragmatist flags `file.rename`, `text.combine`, `addnewreminder`,
`previewdocument`, and `filter.calendarevents` as the high-frequency unmodelled targets.
I endorse this for `text.combine` and `previewdocument` — simple parameter shapes,
sample evidence in hand. For `addnewreminder`, I disagree with modelling it as a typed
schema action at this stage. The Pragmatist's own §1.2 notes that `WFCalendarItemTitle`
requires `WFQuantityFieldValue` with a string `Magnitude` — an easy gotcha. More
importantly, none of the three near-term targets (Strategy agent's priority stack)
require `addnewreminder`. Adding it requires full wire-format equivalence test coverage
before I'd trust it for variable references. The opportunity cost of modelling
`addnewreminder` vs. completing the equivalence sweep for the 14 uncovered actions that
*are* already used in examples is unfavourable. Do the sweep first (Tests Proposal 1);
then add new actions only when they unblock a concrete target.

### Evangelist Move 2 (rename to `shortcuts-sdk`) — premature signal

The Evangelist makes a compelling case for the competitive positioning of the lib. The
competitive gap table (§Appendix) is real and accurate. But Move 2 (rename now) puts a
brand claim ahead of technical substance. An SDK without TypedDict envelopes for its
wire format, without a wire-format equivalence test for 14 of its 21 modelled actions,
without typed variable coupling — that is not yet an SDK in the sense that developers
who compare it to `anthropic-sdk` or `google-genai` will expect. The rename signals
promise the lib hasn't yet fully kept. Make the promise-keeping changes first. The
Pythonic and type improvements (three to four weeks of work) turn the lib into
something that deserves the `sdk` name. Rename after the foundation is solid.

---

## 3. Synergies and Conflicts

### Synergy: Type-Hawk Literal migration + my `@action` decorator (Proposal 3)

The Hawk's Proposal 1 (Literal migration, 8 fields) and my Proposal 3 (`@action` +
`dataclass_transform`) have a natural sequencing. The `@action` decorator collapses
`@register @dataclass` and sets `frozen=True` by default. Once all field annotations are
proper `Literal` types (not `str`), the synthesised `__init__` pyright sees via
`@dataclass_transform` will give IDE red-underlines at call sites for invalid enum
strings. Neither proposal delivers full static checking alone; together they do:
`Literal` defines the valid set, `dataclass_transform` ensures pyright checks the
call sites against it. These two should ship in the same PR or back-to-back.

### Synergy: Wire-format scanner (Wire Pragmatist 3) + `Annotated` slot metadata (my Proposal 2)

I flagged this in the Agreement section. The dependency is explicit: the scanner's
`observed_envelope_types.json` is the authoritative source for which slots need
`TextTokenSlot` vs `ValueSlot` markers. Without the scanner, slot-metadata assignment
is a manual, error-prone judgment. With the scanner, it is a lookup. Write the scanner
first (estimated 2 hours per Pragmatist §3), commit `observed_envelope_types.json`, then
use it as the reference during the `Annotated` slot migration. This turns a risky
migration into a mechanical one.

### Synergy: UX Proposal 1 (semantic-required markers) + my `Var[T]` typed variable
coupling (R1 Proposal 1)

The UX designer wants `describe_action` to surface `semantic_required: True` for
parameters like `DownloadURL.url`. My `Var[T]` proposal is complementary: once named
variables are explicit `Var[str]` objects threaded through function signatures, the
`describe_action` output for blocks can surface the *types* of variables they consume and
produce — not just "this parameter is required" but "this parameter must be a `Var[str]`
returned from a prior block." The UX improvement is richer once the block abstraction
exists. Implement `semantic_required` first (additive, non-breaking); add the block-level
variable type disclosure when `Var[T]` blocks are in place.

### Conflict: Tests Proposal 1 sequencing vs. Strategy Agent's "ship Target A first"

The Tests engineer argues (correctly) that the wire-format equivalence sweep is the
highest-ROI investment and should precede Hypothesis. The Strategy agent argues that
Target A (Voice Note re-author) is Priority 1 because it directly serves the user's
daily workflow.

These are in tension. Target A requires `RecordAudio`, `TranscribeAudio`, and
`Base64Encode` — three of the 14 actions without equivalence tests. If we ship Target A
before the sweep, we repeat the FU-7 pattern: a shortcut that works for literal strings
but silently breaks for variable references. The right resolution is: do not ship Target A
to device before its constituent actions have equivalence tests. Write the three equivalence
tests for `RecordAudio`, `TranscribeAudio`, and `Base64Encode` as part of the Target A
build, not before it. This is faster than a wholesale sweep first, and it ensures the sweep
covers precisely the actions that matter for the near-term targets. The Strategy agent's
priority ordering is preserved; the Tests engineer's equivalence discipline is preserved.
The sweep-first vs. build-first tension resolves to: build and sweep together, action by
action, target by target.

### Conflict: My Proposal 3 (`@action` + frozen) vs. `_bind_self` mutation in `RunWorkflow`

I noted this in R1: the `@action(frozen=True)` default is blocked on B7+E1 resolving the
`_bind_self` mutation. The Evangelist's Move 1 (MCP server) and the Strategy agent's
three targets all implicitly assume `RunWorkflow` works correctly for the iCloud-share
composition story. The B7+E1 resolution — making `RunWorkflow.target` a constructor
argument resolved at `add()` time by constructing a new bound instance — is the same change
that unblocks `frozen=True`. This is a genuine dependency: the `@action` decorator
migration cannot be completed until B7+E1 lands. Calling out this explicit blocking
relationship avoids anyone starting the `@action` migration and then discovering they
can't freeze `RunWorkflow` halfway through.

---

## 4. Direction Questions for the Evangelist

**Q1 — MCP server vs. internal-tooling-first?**

The Evangelist's Move 1 is to publish `shortcuts-mcp` as the first public signal. The
Pythonic, Type-Hawk, and Tests proposals collectively need three to four weeks of
unglamorous work before the lib's internals justify that signal. Is the MCP server a
parallel build (thin wrapper over an imperfect lib, shipped to claim the space) or a
consequence (ship when the lib deserves the "SDK" name)? The answer changes the work
ordering significantly. If parallel, we split attention and accept that the MCP server's
first version has known internal deficiencies. If consequence, the three foundational
proposals (Literal migration, equivalence sweep, `Annotated` slots) are explicitly on
the critical path for the MCP ship date.

**Q2 — Who is the second user?**

The Evangelist frames the thesis around "1.5 billion devices" and a `RoutineHub`
community audience. The Strategy agent frames it around Findlay's three personal daily
workflows. These audiences have different tolerances for rough edges: Findlay will file
issues; RoutineHub users will abandon. The `Annotated` slot metadata, the `Var[T]` typed
coupling, the factory methods on `AskForInput` — these are high-value for an LLM
author who builds complex multi-step shortcuts. They are invisible to a RoutineHub user
who downloads a pre-built file. Which audience gates the v1 ship decision? The answer
determines which of the three Pythonic proposals are blockers vs. nice-to-haves before
Move 1.

**Q3 — Does the cross-platform DSL (Greenfield 2.4) change the `Action` base-class contract?**

The Evangelist's Greenfield 2.4 (Raycast/n8n targets via a `Target` protocol) is the most
architecturally consequential of the five greenfield candidates. If it is a genuine
strategic direction, then `Action.to_action_dict()` cannot remain the sole emit path —
`Action` would need a `CodegenBackend` argument or a visitor pattern. The `Annotated`
slot metadata (my Proposal 2) is a natural fit for a multi-backend emit: each backend reads
the slot markers and applies its own coercion. But if the cross-platform DSL is a "maybe
someday" rather than a near-term commitment, the backend abstraction adds complexity
before it adds value. I need to know whether to design `Annotated` slot metadata as a
single-backend optimisation (Apple only) or as a backend-agnostic descriptor vocabulary
(foundation for multi-target).
