# Architecture Review — Round 2: Product / Use-Case Strategist

_Reviewer: Product / Use-Case Strategist_
_Date: 2026-05-09_
_Context: Cross-commentary on Round 1 documents from the other six agents._

---

## 1. Strong Agreement

### Type-Hawk's Literal migration is a genuine prerequisite for Target A

The eight `frozenset`-to-`Literal` migrations (Type-Hawk Proposal 1) are small,
mechanical, and directly load-bearing for the voice note re-author. The Target A
builder script will call `FormatDate`, `AskForInput`, and `Base64Encode` — all
three of which currently have the `frozenset` validator antipattern. When the LLM
is authoring a voice note shortcut and writes `FormatDate(date_style="custom")` (a
one-character typo from the valid value), the current system raises a `SchemaError`
at emit time in the middle of a build session. With Literals, pyright catches it
inline and the LLM gets a red underline. That is the difference between a failed
build and a never-written bug. This migration costs one focused afternoon and should
run before Target A starts, not after.

Same logic applies to `Base64Encode.mode`. The Target A audio pipeline uses
`Base64Encode` in decode mode to unpack audio data — getting the `mode` literal
right on first attempt matters. Literal types here cost nothing and prevent one of
the most likely Target A authoring mistakes.

### Tests Engineer's wire-format equivalence sweep is the V1 safety gate

The Test Engineer's Proposal 1 — extending `test_wire_format_equivalence.py` to
all 21 leaf actions — is the single most important technical proposal in any of the
six documents, judged by the question "what prevents the next target from shipping
with a hidden iOS failure?"

Target A needs `RecordAudio`, `TranscribeAudio`, and `Base64Encode` equivalence
tests. Target B needs `FormatDate` (already identified as a past failure), `AskForInput`,
and the GET-then-PUT `DownloadURL` pattern. Target C needs the `ShortcutInput` magic
variable handling and `If` conditional branching. Without equivalence tests for these
specific actions, each target ships with silent iOS failure risk — which is exactly
what happened with FU-7. The Wire-Format Pragmatist's Proposal 3 (envelope-type
scanner) amplifies this: a pre-flight scanner that validates envelope types before
`save_signed` is a genuine force-multiplier for all three targets, and I want it in
place before Target A's first device test.

The Test Engineer is right that wire-format equivalence comes before Hypothesis.
I'd go further: equivalence for Target A's specific actions (RecordAudio,
TranscribeAudio, Base64Encode, ChooseFromMenu) should be a gate on merging Target A's
builder script, not an afterthought. This is the one piece of infrastructure I'd
hold a target delivery for.

### LLM-UX's stale SKILL.md fix is a blocker today

LLM-UX Proposal 2, Part A — fixing the stale RunWorkflow composition pattern in
`make-shortcut/SKILL.md` — is not optional. The skill currently contradicts the
decisions log. Any make-shortcut session today could produce a multi-shortcut
composition that requires manual re-wiring after iOS import. That is a
user-experience failure that will happen on the first attempt at Target B or C,
where the user asks Claude to author a new shortcut from scratch. Fix the stale
SKILL.md before any of the three targets begin. It is twenty minutes of editing, not
a proposal.

The control-flow example (LLM-UX Proposal 2, Part B) directly enables Target C's
`If` conditional on input type — the share-sheet shortcut needs to branch on whether
it received a URL or text. Without a worked `If` example in the examples directory,
the LLM will construct that branch cold and probably get the `GroupingIdentifier`
pairing wrong. One canonical `control_flow_demo.py` eliminates the most failure-prone
piece of Target C.

### Wire Pragmatist's `text.combine` model unblocks the regression target

The Wire Pragmatist flags `text.combine` (5 sample appearances, unmodelled) as one
of the high-frequency gaps. My R1 identified re-authoring `daily_standup` as a
medium-value regression target — and `text.combine` is the only schema blocker on
that path. The Wire Pragmatist already has the sample evidence (`sort_lines.xml`) and
the envelope type analysis. Modelling `text.combine` is one action file, ~30 lines,
with a wire-format equivalence test alongside. This is a 90-minute task that completes
the regression target I wanted and satisfies the Wire Pragmatist's Proposal 2 for
that specific identifier.

---

## 2. Disagreements and Pushback

### The Pythonic `@block` decorator is over-engineered for the next three targets

The Pythonic Architect's most ambitious proposal — the `@block` decorator with
`Var[T]` typed returns and a `ShortcutBuilder` context — is the right long-term
direction for the API but the wrong thing to build now. Here is the concrete
problem: Target A's builder script (`voice_note_to_vault.py`) will be authored by
Claude Code using the `make-shortcut` skill. The skill needs the authoring surface
to be stable, documented in SKILL.md, and consistent with the existing `vault_note_to_git.py`
example that Claude Code already knows. Introducing `@block` means: new decorator
pattern in SKILL.md, new builder API, new conventions for how functions compose, all
of which differ from the existing example. The LLM now has two composition patterns
to disambiguate and none of the existing example code to copy from.

The `Var[T]` typed variable wrapper (Pythonic Proposal 1) is a lighter lift and
worth doing — it is additive and backward-compatible. The stringly-typed `NamedVar`
coupling is a real footgun. But the full `@block` decorator stack (Proposal 3 gated
on `B7+E1`) should be scheduled after Target A ships, not before. The ratio of
architectural improvement to target-slippage risk is unfavourable right now. Build
Target A with the current pattern; let the pain of two sequential PUTs with binary
payloads reveal whether `@block` actually reduces friction or just moves it.

### The Evangelist's MCP server and rename are premature for exactly one reason

The Evangelist's Move 1 (publish `shortcuts-mcp`) and Move 2 (rename to
`shortcuts-sdk`) are the right moves for the right product. My objection is timing,
not direction.

The MCP server proposal assumes the lib's authoring surface is stable enough to
expose publicly. Right now it is not: the `make-shortcut` skill requires manual
post-import credential injection (FU-9 is open), `text.combine` and `addnewreminder`
are unmodelled despite being needed by two of the three targets, and the wire-format
equivalence tests cover only 7 of 21 actions. Publishing an MCP server that emits
shortcuts with 14 unvalidated action wire formats is not a signal of quality — it is
a support ticket waiting to happen. The first MCP user who tries to build a shortcut
with `FormatDate` and a variable reference will get a silent iOS failure, the lib
will have no way to tell them why, and the impression formed at that moment is the
one that sticks.

The correct sequencing: V1 means five real targets working end-to-end including
Setup section support (FU-9), wire-format equivalence for all 21 leaf actions,
and a stale-docs-free skill. That is V1-done as I defined it in R1. Publish the MCP
server after V1-done. The rename can happen sooner — it is a README change, not a
capability claim — but the MCP publication should wait for the lib to deliver on
what the MCP would advertise.

### TypedDict envelope sweep is the right idea in the wrong sprint

The Type-Hawk's Proposal 2 — TypedDicts for wire-format envelopes (`WFTextTokenString`,
`WFTextTokenAttachment`, `WFDictionaryFieldValueItem`) — is correct in principle and
I want it eventually. But it is a multi-day refactor that cascades into every action's
`_params` method and requires a half-day of pyright error triage. That is three to
five days of infrastructure work with zero user-visible output at the end of it.

The wire-format equivalence sweep achieves 80% of the same protection faster:
instead of making the type system prove envelope shapes are correct, you test them
empirically against real Apple outputs. The TypedDict work is the right follow-on
once the equivalence tests are green — at that point you are strengthening a layer
that is already empirically validated, not replacing empirical validation with static
analysis. Schedule the TypedDict sweep as a post-Target-B refactor, not a pre-Target-A
gate.

---

## 3. Synergies and Conflicts

### The critical sequencing question: V2 architecture before or after the next 3 targets?

The implicit ordering conflict between the technical proposals is stark:

- Pythonic + Type-Hawk would do `@block`, `Var[T]`, TypedDict envelopes, and
  `dataclass_transform` — a V2 architecture pass — before writing Target A.
- Wire Pragmatist + Test Engineer would do equivalence sweeps, envelope scanner,
  and high-frequency action modelling — a V1 correctness pass — before Target A.
- LLM-UX would fix SKILL.md and add the control-flow example — a V1 documentation
  pass — before Target A.
- The Evangelist would ship the MCP server and rename — a V1 marketing pass —
  before any of the above.

My position: the V1 correctness pass (Tests + Wire) is the gate on Target A. The
V1 documentation pass (LLM-UX) is also a gate, because a stale SKILL.md is a silent
target-blocker. The V2 architecture pass is post-Target-B at the earliest. The
marketing pass is post-V1-done.

Here is why the architecture-first ordering is risky: the design has been stressed
exactly once, with a single shortcut shape. We do not yet know whether the current
`_add_config / _add_polish / _add_push` pattern scales to a two-payload audio
pipeline (Target A), a GET-then-PUT sequence (Target B), or a conditional branch on
input type (Target C). The Pythonic Architect is proposing to make the composition
model typed and refactored before finding out whether the current composition model
breaks under real load. That is a classic over-engineering trap: redesign before
finding the pain. Let the targets reveal the actual friction, then refactor.

The specific synergy to exploit: the Literal migration (Type-Hawk P1) and the
wire-format equivalence sweep (Tests P1) compose naturally. Both are low-risk,
sample-grounded, and directly support Target A authoring. Run them in parallel in
the same sprint. The `Var[T]` wrapper (Pythonic P1) is the one V2-era change I'd
include in that sprint — it is additive, does not change SKILL.md conventions, and
directly addresses the most dangerous silent failure mode in the voice note builder
(misspelled variable names across two sequential PUTs).

### FU-9 Setup section timing

The Setup section (FU-9, `WFWorkflowImportQuestions`) is where my view and the
Evangelist's diverge most concretely. I argued in R1 that FU-9 should ship with
Target B. The Evangelist's MCP server proposal assumes FU-9 is in place before
publishing. These are consistent — if the MCP server waits for V1-done, and V1-done
requires FU-9, then FU-9 is a V1 gate, not a V2 aspiration. The sequencing works:
Target B implements FU-9, Target B ships, V1-done, MCP server. No conflict, but the
MCP server must wait for that chain.

### The `addnewreminder` modelling conflict

The Wire Pragmatist identified `addnewreminder` as a high-frequency unmodelled
identifier (5 sample appearances). My R1 flagged it as the optional enhancement to
Target B (Reminders integration). The conflict: Wire Pragmatist advises modelling
it with sample evidence from `batch_add_reminders.xml`; I called it optional for
Target B because the core daily note task works without it. These are consistent:
model `addnewreminder` in the Target B sprint as a bonus, using the Wire Pragmatist's
sample-evidence process. But do not let it block the core Target B delivery if the
`WFQuantityFieldValue` complexity takes longer than expected. Separate it as a
parallel track.

---

## 4. Direction Questions for the Evangelist

### Q1: Personal tool first or SDK first — and is the answer permanent?

This is the question that re-orders every other proposal. If the answer is "personal
tool first, proving the design with my own daily use, then SDK," then: FU-9 and
wire-format equivalence and three working targets are the V1 definition, MCP and
rename follow after. If the answer is "SDK first, ship the MCP server now while the
ecosystem is early, accept some rough edges," then: the rename and MCP server move
up, and we ship the MCP with an explicit "alpha, 21 validated actions, known gaps"
label and a GitHub issues link.

Both answers are legitimate. The first gives you a better product at V1 publish time.
The second gives you mindshare while the MCP ecosystem is forming. The answer changes
whether Pythonic's `@block` decorator is a V1 prerequisite (SDK-first: yes, the public
API should be clean) or a V2 improvement (personal-first: no, ship the working thing
then refactor). Everything in this review is implicitly betting on the personal-first
answer; the Evangelist may disagree.

### Q2: What is the minimum bar to call V1 "shareable"?

The Evangelist describes a V1-shareable state as: MCP server live, rename done,
three worked examples, and a README that explains the LLM authoring story. I
described it as: five working end-to-end targets covering all trigger surfaces, FU-9
Setup section working, and wire-format equivalence for all 21 leaf actions. These
are different bars. The Evangelist's bar is faster to hit and wider-reaching; mine
is higher-confidence and narrower.

The gap that matters: the Evangelist's shareable state does not require FU-9. A
shared shortcut without Setup section support requires the recipient to open the
Shortcuts editor and hand-edit credentials. That is a deal-breaker for the "any
Claude Desktop user can run this" pitch. Does the Evangelist consider that friction
acceptable at publication time, or is FU-9 a hard prerequisite for the MCP server?
The answer changes Target B's priority.

### Q3: How much does the GPL-3.0 licence constrain the SDK play?

The MCP server, once published to the MCP directory, will be picked up by Claude
Desktop users who may embed it in other toolchains or automate it. GPL-3.0 requires
derivative works to be GPL-3.0 as well. For an MCP server that other projects call
as a subprocess or network tool, this is probably fine — the server is the GPL
work, the callers are not derivatives. But if the Evangelist's vision includes the
lib being used as a library dependency in commercial tools or embedded in other
agents, GPL-3.0 is a real constraint. MIT or Apache-2.0 would allow that; GPL-3.0
would not. Worth clarifying before the rename and MCP publication commit the lib
publicly to this licence path.
