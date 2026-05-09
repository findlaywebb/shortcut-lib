# Architecture Review — Synthesis

**Date:** 2026-05-09
**Reading:** seven R1 documents + seven R2 cross-commentaries.
**Audience:** Findlay (developer; the lib's primary "second user" Claude Code).

---

## 1. Executive summary

Two rounds of seven-agent review yielded violent agreement on a small foundation, a handful of real disputes, and a 7-week calendar from the Evangelist that mostly survives scrutiny. The consensus floor is unusually solid: Literal migration first, wire-format equivalence sweep before any external surface, FU-9 Setup section as a V1 prerequisite, FU-7-class envelope bugs as structural debt needing both an empirical scanner and (eventually) TypedDicts. Pythonic, Type-Hawk, Tests, and Wire all converge here — different phrasing, same defence-in-depth.

The genuine debates: (a) whether `@block` and full `Annotated` slot dispatch land before or after Targets A/B/C reveal the friction (Strategy/LLM-UX say after; Pythonic says now), (b) whether the MCP server is parallel or a consequence of V1-done (Evangelist R2 conceded consequence; correct call), and (c) `@overload` vs factory methods for dependent fields — cross-commentary unanimously sided against Type-Hawk's R1 overloads in favour of LLM-UX's factory methods.

Calls only you can make:

1. **Personal-tool-first vs SDK-first as identity, not just timing.** Evangelist R2 framed it well ("personal-first timeline, SDK-quality every commit"); the answer changes which proposals are V1 blockers. If SDK-first, factory methods and `Var[T]` are V1; if personal-only, they can wait.
2. **Does V1 ship publicly at all?** Is `shortcuts-mcp` published, or does the lib stay private? Every downstream priority pivots on this.
3. **Licence posture for the MCP/embedding play.** GPL-3.0 is fine for MCP-as-subprocess; it constrains commercial library embedding. Decide before publishing.

**Bottom line:** if you commit to "personal-first now, SDK-quality always, MCP after V1-done in ~7 weeks," the lib in 8 weeks looks like: 3 distinct-surface working shortcuts end-to-end, all 21 leaf actions sample-grounded with equivalence tests + scanner CI gate, Literal-typed enums throughout, FU-9 Setup section live, `Var[T]` variable threading, an unpublished-but-drafted MCP server, and a clear V2 plan (TypedDicts, `@action` decorator, factory methods, Hypothesis). Credible v1.0 tag, believable blog-post abstract.

---

## 2. Consensus — what every agent agrees on

All of these surfaced in at least four R1 docs and were not contested in R2. Move past them.

- **Migrate the eight `frozenset` validators to `Literal` types** — eight fields, one afternoon. Single highest-ratio change in the codebase. (Type-Hawk R1 P1, endorsed by Pythonic R2, LLM-UX R2, Tests R2, Wire R2, Strategy R2, Evangelist R2 — unanimous.)
- **Wire-format equivalence sweep to all 21 leaf actions before any external surface ships** — closes the FU-7 class structurally. (Tests R1 P1 and Wire R1 P1 converge; endorsed by every R2 doc; Strategy R2 makes it a Target-A merge gate.)
- **Build `scripts/scan_envelope_types.py` and commit `data/observed_envelope_types.json`** as a living CI artefact — the empirical record that closes the loop the equivalence tests assert against. (Wire R1 P3, endorsed by Type-Hawk R2, Tests R2, LLM-UX R2.)
- **Fix `skills/make-shortcut/SKILL.md`** — the composition section still shows the deprecated `RunWorkflow` orchestrator pattern, contradicting the 2026-05-09 decisions-log pivot. Twenty-minute edit; blocks no other work; do this week. (LLM-UX R1 P2A; Strategy R2 elevates to "blocker today.")
- **Add `examples/control_flow_demo.py`** with worked `If`/`RepeatEach`/`ChooseFromMenu` patterns. Target C will need it; without it, the LLM constructs `If` cold and gets the GroupingIdentifier pairing wrong. (LLM-UX R1 P2B; Strategy R2 calls out the Target C dependency.)
- **FU-9 (`WFWorkflowImportQuestions` Setup section) is a V1 prerequisite, not V2** — without it, every shared shortcut requires post-import editor surgery. (Strategy R1; Evangelist R2 explicitly flips on this and agrees.)
- **`Var[T]` typed wrapper around `NamedVar`** is the one V2-era change that pays now: additive, backward-compatible, structurally prevents the most dangerous silent-failure mode (misspelled variable names across multi-step builders). (Pythonic R1 P1; endorsed by Type-Hawk R2 §3, LLM-UX R2, Strategy R2, Evangelist R2.)
- **Personal-tool-first in timeline; SDK-quality in every commit; MCP server is a consequence of V1-done, not parallel.** (Evangelist R2 finally agreed with Strategy R2's framing.)
- **The cross-platform DSL (Greenfield 2.4) is not a near-term commitment.** Evangelist R2 explicitly withdrew it after Wire R2 and Pythonic R2 made the IR-stability case. Slot annotations should be designed Apple-only, not as a multi-backend foundation.
- **GPL-3.0 stays for now**, compatible with MCP-as-subprocess; revisit only if commercial library embedding becomes a real ask. (Evangelist R2 answer to Strategy R2 Q3.)

Weak-consensus items (flagged honestly):
- *Hypothesis property tests come after the equivalence sweep.* Tests R1 said "after Layer 2"; Wire R2 sharpened to "before is wasteful"; LLM-UX R2 dissented mildly ("the never-raises property is worth running in parallel"). The synthesis call: defer until Layer 2 is in place. LLM-UX's argument is real but the FU-7 class remains the dominant risk and Hypothesis can't catch it.
- *TypedDict envelopes are correct eventually.* Type-Hawk R1 P2 wants them now; Pythonic R2 and Strategy R2 both say "right idea, wrong sprint." Synthesis: wait until equivalence sweep is green and `emit_params` dispatch (if adopted) centralises the cascade surface.

---

## 3. Contested questions

### 3.1 — Personal-tool-first vs SDK-first sequencing

**Position A (Strategy, Wire, Tests, LLM-UX):** Personal-tool-first. Three real distinct-surface targets (Voice Note, Quick Task, Share Sheet) drive the V1 definition; the lib must work for Findlay's daily use before any external claim. The MCP server and `shortcuts-sdk` rename wait for V1-done. Strategy R2 was firmest: a published MCP server with 14 unvalidated wire formats produces a worse first impression than no public surface at all.

**Position B (Evangelist R1):** SDK-first. The MCP ecosystem is forming; the gap between "can produce signed `.shortcut` files for Apple offline" and every other automation tool is genuinely uncrowded; the lib already passes that bar today. Publishing now claims the space; rough edges are fixable; mindshare compounds. Evangelist R1 Move 1 was "publish `shortcuts-mcp` in a week."

**What hangs on it:**
- If A: the Pythonic `@block` decorator and overload/factory work can wait until Targets A/B/C reveal the friction. The Type-Hawk TypedDict sweep is post-V1-done. The lib's name doesn't change yet.
- If B: factory methods and `Var[T]` and Literal migration are all V1 blockers (the second user — a developer with Claude Code — encounters them immediately); the rename happens before V1; the MCP server scaffold runs in parallel with the foundational work.

**Synthesiser recommendation: A, but with the discipline B demands.** Evangelist R2 effectively conceded to A by reframing as "personal-tool-first in timeline; SDK-quality in every commit." That reframe is correct: the timeline pressure goes to A (don't ship broken in public), the per-commit discipline goes to B (every change is one a developer-second-user could read tomorrow). The risk in pure-A is the project calcifies into "personal tool forever"; the discipline of "SDK-quality in every commit" is what prevents that. Adopt A.

---

### 3.2 — TypedDict envelope sweep before, with, or after the equivalence sweep

**Position A (Type-Hawk R1):** Now. TypedDicts for `WFTextTokenString`, `WFTextTokenAttachment`, `WFDictionaryFieldValueItem` would have caught FU-7 at pyright time, before any test ran. Hawk budgeted "half a day of pyright triage" for the cascade.

**Position B (Pythonic R2, Strategy R2, Tests R2):** After. Narrowing `coerce_value`'s return from `Any` to a TypedDict union ripples into 21 `_params()` methods. Pythonic R2 estimated the cascade cost as "3-5x the Hawk's budget." Right thing in the wrong sprint. The equivalence sweep achieves 80% of the same protection empirically and faster.

**Position C (Wire R2):** TypedDicts must be `total=False` with `Required[]` per key, every field annotated with a sample citation, treated as a living record not a static definition — otherwise they freeze a schema that Apple will drift on.

**What hangs on it:** Whether the V1 sprint includes any type-system work beyond the Literal migration. If A, you spend two of the seven weeks on the TypedDict cascade. If B, those weeks go to targets and FU-9.

**Synthesiser recommendation: B, with C's discipline when you eventually do A.** Wire R2 is right that any TypedDict definitions need sample citations and `total=False` + `Required[]` for keys observed always. Pythonic R2 is right that the cascade is bigger than Hawk estimated. The right sequence is: (1) equivalence sweep + scanner empirically prove envelope correctness, (2) `emit_params` dispatch (if you adopt the `Annotated` slot pattern) centralises coercion to one site, (3) *then* TypedDicts narrow the central site with sample-cited definitions. Doing TypedDicts before step 2 is doing them across 21 cascade points instead of one.

---

### 3.3 — `@overload` vs factory methods for dependent fields

**Position A (Type-Hawk R1 P3):** `@overload` on `AskForInput.__init__` (or via `__new__`) for the `input_type="Number" → allows_decimal` dependency. Catches the bad combination at pyright time, before the build runs.

**Position B (LLM-UX R2, Pythonic R2, Evangelist R2):** Factory methods (`AskForInput.number(...)`, `AskForInput.text(...)`). The argument is specifically about LLM error-message quality: pyright's overload-mismatch errors are notoriously poor (the LLM has to diff overload signatures and infer which constraint fires); a missing-argument error from a factory is the normal Python path with a single clear message. LLM-UX R2 made the strongest case: today's `__post_init__` message ("`allows_decimal` is only valid when `input_type='Number'`") is *better than* the pyright overload error the Hawk's path produces.

**What hangs on it:** Whether `AskForInput`, `FormatDate`, `TextSplit`, `DownloadURL` (body/body_type), and `RunWorkflow` (target resolution) get refactored to a factory pattern. This is a documented-API change.

**Synthesiser recommendation: B (factory methods).** LLM-UX R2's pyright error-quality argument is decisive — the lib's primary user is an LLM parsing error text, not a human reading IDE underlines. Factory methods also have no conflict with `@dataclass_transform` (Pythonic R1 P3, which Hawk endorsed); overloads on dataclass `__init__` do. Factory methods are surfaced naturally by `describe_action`. Adopt them. Keep the original `__init__` silently functional for back-compat; do not formally deprecate (deprecation warnings accumulate without value here).

---

### 3.4 — `frozen=True` by default vs iOS-drift accommodation

**Position A (Pythonic R1 P3, Tests R2, Type-Hawk R2):** Frozen-by-default via the `@action` decorator. Closes the post-construction mutation footgun (`fd.date_style = "Custom"` silently bypassing validation). Simplifies the test surface — no mutation tests needed. Frozen-by-default also pairs well with `@dataclass_transform` for proper IDE support.

**Position B (Wire R1, implicit in LLM-UX R2):** The wire format drifts. Treating action instances as frozen architectural primitives presumes the schema is more stable than Apple makes it. LLM-UX R2 added a specific UX concern: `FrozenInstanceError` is a poor LLM-facing error; intercepting it and converting to a `SchemaError` with the "construct a new instance" hint is a 10-line wrapper that should land alongside `frozen=True`.

**What hangs on it:** Whether the `@action` decorator (Pythonic P3) ships at all, and whether it ships gated on B7+E1 (the `_bind_self` mutation in `RunWorkflow.target` that currently blocks frozen).

**Synthesiser recommendation: A with LLM-UX R2's wrapper.** Frozen is the right default; the iOS-drift concern is real but applies to the *schema definitions*, not action instances at a single build time. B7+E1 is genuine prerequisite work — the `_bind_self` mutation must be removed before `@action(frozen=True)` lands. Adopt the LLM-UX R2 `FrozenInstanceError → SchemaError` interceptor as part of the `@action` decorator package.

---

### 3.5 — `@block` decorator now or after Target A reveals the friction

**Position A (Pythonic R1 P1):** Now. The current `_add_config / _add_polish / _add_push` pattern is procedural mutation with stringly-typed `NamedVar` coupling — the most active footgun in the codebase. `@block` with `Var[T]` returns gives the composition story a typed spine before more ad-hoc helpers accumulate.

**Position B (Strategy R2, LLM-UX R2, Evangelist R2):** After. `@block` introduces new vocabulary (`ShortcutBuilder`, the decorator itself, `Var[T]` as return type) before Targets A/B/C have stress-tested whether the current pattern actually breaks. LLM-UX R2: the LLM now has two composition patterns to disambiguate. Strategy R2 framed as classic over-engineering: redesign before finding the pain.

**What hangs on it:** Whether `vault_note_to_git.py` gets refactored to the `@block` pattern as a precedent, and whether SKILL.md documents `@block` as the canonical authoring path.

**Synthesiser recommendation: B with Var[T] decoupled.** The single agreed-on item is `Var[T]` typed threading — every R2 doc endorses this *separately* from the `@block` decorator. Ship `Var[T]` now (additive, backward-compatible, no SKILL.md change required). Defer `@block` until at least Target A and Target B have been authored with the current pattern. The friction Pythonic correctly identifies might be solved by `Var[T]` alone, in which case `@block` is unnecessary; or it might recur in Target B's GET-then-PUT chain, in which case `@block` arrives with concrete pain to validate against.

---

### 3.6 — MCP server timing

**Position A (Evangelist R1 Move 1):** Within a week, in parallel with the foundational work. The MCP ecosystem is early; the gap is real; first-mover mindshare matters.

**Position B (Strategy R2, Wire R2, Evangelist R2):** After V1-done. Strategy R2: a published MCP server with 14 unvalidated wire formats is a support-ticket factory. Wire R2: the first MCP user who builds a `FormatDate` shortcut with a variable reference gets a silent iOS failure, the lib has no diagnostic path, that's the first impression.

**What hangs on it:** The 7-week calendar's tail end. If A, the lib name changes earlier, the README rewrite happens earlier, and the MCP scaffold work runs in parallel with the type system work.

**Synthesiser recommendation: B.** Evangelist R2 already conceded this in their direction-question answers. The remaining synthesis call is just to make it explicit: the MCP scaffold can be drafted in parallel (no harm in writing the server), but `claude mcp add shortcuts-mcp` doesn't go live until V1-done. Treat as roughly week 8.

---

### 3.7 — Hypothesis ordering relative to narrow types

**Position A (Tests R1 P2):** Layer 2 (equivalence sweep) first; Hypothesis after, with type-narrowed strategies.

**Position B (LLM-UX R2):** Introduce a minimal Hypothesis suite (`test_schema_to_bplist_never_raises`, `test_bplist_round_trip_property`) in parallel with Layer 2. The LLM generates unusual parameter combinations that sample-based tests don't cover.

**Position C (Type-Hawk R2):** Hypothesis is *not* a substitute for narrow types. `GetText(text=42)` passes Hypothesis's "doesn't raise" test today because `ParamValue` accepts `int`. The strategies need to be constrained by the narrow types to be meaningful.

**What hangs on it:** Whether Hypothesis is in the V1 work or strictly V2.

**Synthesiser recommendation: A's ordering, C's framing.** LLM-UX R2's parallel-track argument is real but the specific tests they propose are weak in the current type regime — Hypothesis catches encode/decode asymmetry but cannot catch the FU-7 class. The strongest version is C: Hypothesis becomes transformative *after* Literal migration + slot-typed fields make the strategies semantically correct. V1 should not invest in Hypothesis. V2 introduces it as the third leg of the "scanner + TypedDicts + Hypothesis" closed audit loop the Evangelist R2 articulated.

---

## 4. Decisions the user owns

These are not technical calls; they're strategic posture. Each phrased so you can answer in one sentence.

### 4.1 — "Is shortcut-lib a personal tool, an SDK, or both — and which leads?"

The four corner agents (Strategy, LLM-UX, Wire, Tests) implicitly assume personal-first; Pythonic and Type-Hawk implicitly assume SDK-first; Evangelist explicitly bridged the two with "personal-first in timeline, SDK-quality in commits." Your answer determines whether `Var[T]` and factory methods are V1 blockers or V1.5 polish. **Who cares:** Pythonic (most affected — `@block` scope), Strategy (Target sequencing), Evangelist (V1 ship date), Type-Hawk (whether typed-coverage gaps block the natural-language compiler vision).

### 4.2 — "Is V1's bar 'shareable' or 'works for me'?"

Strategy R1 set "five distinct-surface targets working end-to-end + FU-9 + 21-action equivalence" as V1-done. Evangelist R1 set "MCP server live, rename done, three examples, README" as the bar. Evangelist R2 conceded Strategy's bar is right. But Strategy's bar is 7+ weeks; "works for me" is closer to 2-3 weeks (3 targets ad-hoc, equivalence sweep, FU-9 deferred). **Who cares:** Strategy (sets target count), Evangelist (what V1 announces), Wire/Tests (whether equivalence sweep is gating), every reader of `examples/` (what counts as a working example).

### 4.3 — "Public or private until V1?"

The repo is GPL-3.0 with `NOTICE` and `docs/sources.md` already in place — publication-clean today. But Evangelist R2 explicitly held the MCP publication for V1-done. Independent of the MCP, do you want the GitHub repo public during the 7 weeks, or only at v1.0.0 tag? **Who cares:** Evangelist (timing of the rename and any blog post), Strategy (Target C's "share-sheet from Safari" demo doesn't need a public repo to validate), you (rotating the FU-4 GitHub PAT in `samples/private/voice_note_to_github.shortcut` is overdue and pre-publication).

### 4.4 — "Is the natural-language compiler (Greenfield 2.2) a real direction?"

Evangelist R1 listed it as Greenfield candidate #2; Evangelist R2's answer to Type-Hawk R2 Q3 said it requires "completion of Pythonic + Type-Hawk V1 proposals" before it's viable. If you intend to pursue it, the Literal-typed enum + factory-method + slot-metadata coverage that is V1 work for the LLM-author surface is *also* on the critical path for the compiler. If you don't intend to pursue it, you have more flexibility on coverage. **Who cares:** Type-Hawk (typed-schema coverage threshold), Pythonic (whether `Annotated` slot dispatch is a V1.5 or V2 commitment).

### 4.5 — "Does anyone other than you and Claude Code use this in the next 12 months?"

Evangelist's "second user" framing (Pythonic R2 Q2) — a developer who already uses Claude Code and has heard about Apple Shortcuts — is the audience the V1 polish targets. If you intend to actively recruit second users (blog post, MCP directory, RoutineHub mentions), every V1-done item from the consensus list is genuinely required. If you don't, you can ship a personal tool with rough edges and revisit. **Who cares:** Evangelist (publication strategy), LLM-UX (whether error-message quality is a feature or a niceity), Strategy (Target C's "any iOS user" framing).

---

## 5. Prioritised proposal slate

Ordered by sequence position. Each entry is a discrete unit of work with clear unblocking effects.

### 5.1 — Fix `skills/make-shortcut/SKILL.md` composition section
- **Source:** LLM-UX R1 P2A
- **Cost:** S (20 minutes)
- **Unlocks:** any new make-shortcut session produces the current Python-function composition pattern, not the deprecated `RunWorkflow` orchestrator.
- **Depends on:** nothing
- **Sequence position: 1.** Today. Blocks no other work; un-blocks every future make-shortcut session.

### 5.2 — Literal migration (eight `frozenset` validators → `Literal` types)
- **Source:** Type-Hawk R1 P1; unanimous endorsement R2.
- **Cost:** S (one focused afternoon)
- **Unlocks:** pyright catches enum typos at write time; `describe_action` surfaces enum constraints to the LLM directly; sets up Pythonic's `Annotated` slot work; gives MCP `pydantic.model_json_schema()` derivation real validation for free.
- **Depends on:** nothing
- **Sequence position: 2.** Week of May 12. Every other typing improvement is downstream of this.

### 5.3 — Envelope-type scanner + `data/observed_envelope_types.json`
- **Source:** Wire R1 P3; Type-Hawk R2, Tests R2 endorse.
- **Cost:** S (2 hours)
- **Unlocks:** empirical record that the equivalence sweep can assert against; future iOS samples produce diffable output; oracle for the eventual `Annotated` slot metadata or TypedDict definitions.
- **Depends on:** nothing
- **Sequence position: 3.** Week of May 19, Monday. Run before extending equivalence tests so the JSON is the oracle.

### 5.4 — Wire-format equivalence sweep (all 21 leaf actions + 4 control-flow constructs)
- **Source:** Tests R1 P1, Wire R1 P1; Strategy R2 makes it the Target-A merge gate.
- **Cost:** M (3-4 focused hours, one per action)
- **Unlocks:** the FU-7 class is structurally caught at commit time, not on device; the MCP server publication path is no longer blocked on a per-action correctness audit; the audit CLI's "modelled coverage" tier becomes meaningful.
- **Depends on:** 5.3 (scanner provides oracle)
- **Sequence position: 4.** Week of May 19-26. The single highest-ROI investment in the codebase.

### 5.5 — `Var[T]` typed wrapper around `NamedVar`
- **Source:** Pythonic R1 P1; endorsed by every R2 doc.
- **Cost:** S (one new generic class + helper method on `Shortcut` + refactor of `vault_note_to_git.py`)
- **Unlocks:** typed threading of variables across helper functions; misspelled `NamedVar("Toekn")` becomes a type error not a silent iOS empty field; precondition for the eventual emit-time binding registry.
- **Depends on:** nothing (can run in parallel with 5.4)
- **Sequence position: 5.** Week of May 26 (parallel with the tail of 5.4).

### 5.6 — Add `examples/control_flow_demo.py`
- **Source:** LLM-UX R1 P2B; Strategy R2 calls out the Target C dependency.
- **Cost:** S (~60 lines)
- **Unlocks:** Target C's `If`-on-input-type branching has a worked reference; future LLM-authored shortcuts with conditional logic don't construct GroupingIdentifier pairs cold.
- **Depends on:** nothing (parallel-eligible)
- **Sequence position: 6.** Same week as 5.5.

### 5.7 — Target A: Voice Note → Vault re-author
- **Source:** Strategy R1 priority 1.
- **Cost:** M (builder script + verifying DeviceDetails wire format + ChooseFromMenu UX)
- **Unlocks:** validates the audio-binary PUT pipeline; `Base64Encode` decode mode exercised end-to-end; sample-grounded equivalence for `RecordAudio`, `TranscribeAudio`, `Base64Encode` (per Tests R2's "build and sweep together" resolution).
- **Depends on:** 5.4 (specifically the equivalence tests for the three constituent actions); 5.5 (`Var[T]` for the multi-step dataflow).
- **Sequence position: 7.** Week of June 2.

### 5.8 — FU-9 (`WFWorkflowImportQuestions` Setup section authoring)
- **Source:** Strategy R1 cross-cutting; Evangelist R2 made it a V1 prerequisite.
- **Cost:** M (top-level workflow key with structured question dicts; new `Shortcut(setup_questions=[...])` API; round-trip test via decoded sample)
- **Unlocks:** every shared shortcut becomes "drag in, fill form, run" instead of "drag in, edit Text actions, close, run"; precondition for any external publication.
- **Depends on:** nothing technically, but pairs with Target B authoring naturally.
- **Sequence position: 8.** Week of June 9, with Target B.

### 5.9 — Target B: Quick Task → Daily Note (macOS Spotlight surface)
- **Source:** Strategy R1 priority 2.
- **Cost:** M (read-then-modify-then-write pattern; macOS Spotlight surface metadata; FormatDate equivalence test)
- **Unlocks:** first shortcut writing *into* the vault; macOS surfaces validated; FU-9 dogfooded; FormatDate wire-format equivalence (the action that caused FU-7's worst bug) sample-grounded.
- **Depends on:** 5.4, 5.5, 5.8
- **Sequence position: 9.** Week of June 9-16.

### 5.10 — Target C: Share-Sheet → Vault Inbox
- **Source:** Strategy R1 priority 3.
- **Cost:** M (share-sheet `WFWorkflowTypes`, `accepted_input` C4 metadata, `If`-on-input-type)
- **Unlocks:** the share-sheet trigger surface (the bridge to every other iOS app); typed input handling; conditional-on-content-type pattern reusable for any future inbound-capture shortcut.
- **Depends on:** 5.4, 5.5, 5.6 (control-flow demo).
- **Sequence position: 10.** Week of June 16-23.

### 5.11 — Factory methods for dependent fields (`AskForInput.number`, `.text`, etc.)
- **Source:** LLM-UX R2 (against Type-Hawk R1 P3); Pythonic R2, Evangelist R2 endorse.
- **Cost:** S-M (factory methods on 4-5 actions; `describe_action` updates to surface them as primary)
- **Unlocks:** the `allows_decimal`-only-when-Number constraint becomes a method name, not an error message; clean LLM error path; precondition for the natural-language compiler's structured-output retry pattern.
- **Depends on:** 5.2 (Literal migration first so the factory parameter types are proper enums).
- **Sequence position: 11.** Week of June 23 — first piece of V1.5 work.

### 5.12 — `@action` decorator + `dataclass_transform` + frozen-by-default + B7+E1 resolution
- **Source:** Pythonic R1 P3; Tests R2 endorses; Type-Hawk R2 endorses; LLM-UX R2 adds the FrozenInstanceError → SchemaError interceptor.
- **Cost:** M-L (decorator + `_bind_self` mutation removal in `RunWorkflow` + 24-action mechanical migration)
- **Unlocks:** import-time identifier validation (free Layer 0 check); proper IDE typing for action constructors; one decorator instead of two-stack; eliminates the post-construction mutation footgun.
- **Depends on:** 5.2 (Literal); B7+E1 work (open in handoff.md) for the `RunWorkflow.target` mutation.
- **Sequence position: 12.** Week of June 30.

### 5.13 — `Annotated[X, SlotKind]` slot metadata + `emit_params` dispatch
- **Source:** Pythonic R1 P2; Tests R2 conditionally endorses (with sample-citation requirement); Wire R2 conditionally endorses.
- **Cost:** M (40 lines of dispatch + per-slot annotations across 21 actions, sample-cited)
- **Unlocks:** `describe_action` surfaces the coercion contract; FU-7 class becomes structurally impossible to introduce in new actions; centralises the cascade surface for the eventual TypedDict narrowing.
- **Depends on:** 5.3 (scanner output as oracle), 5.4 (equivalence tests as cross-check), 5.12 (`@action` provides the decorator surface).
- **Sequence position: 13.** Week of July 7.

### 5.14 — TypedDict envelope layer
- **Source:** Type-Hawk R1 P2; deferred by Pythonic R2, Strategy R2; Wire R2 adds `total=False` + Required + sample-citation discipline.
- **Cost:** M (TypedDict definitions + narrowing `coerce_value` return type + cascade triage)
- **Unlocks:** wrong-key typos in wire-format dicts become pyright errors at write time; closes the FU-7 class at the static layer.
- **Depends on:** 5.13 (centralised `emit_params` minimises the cascade surface).
- **Sequence position: 14.** Week of July 14.

### 5.15 — Hypothesis property tests
- **Source:** Tests R1 P2; Wire R2 sequences after 5.4; Type-Hawk R2 makes coverage meaningful only after narrow types.
- **Cost:** S-M (~150 lines of strategies + 2-3 invariant tests)
- **Unlocks:** combination-space coverage; encode/decode asymmetry; with type-narrow strategies, the third leg of the closed audit loop.
- **Depends on:** 5.2 (Literal — strategies need narrow types to be meaningful), 5.13 (slot metadata — strategies via `st.from_type`).
- **Sequence position: 15.** Week of July 21.

### 5.16 — MCP server scaffold + `pydantic.model_json_schema()` derivation
- **Source:** Evangelist R1 Move 1 (deferred to consequence by R2).
- **Cost:** M (server scaffold; tool wrappers; JSON-schema derivation; pinned-version policy)
- **Unlocks:** Claude Desktop users can author Shortcuts via natural language; the MCP directory listing claims the gap.
- **Depends on:** 5.4 (equivalence sweep — public-facing surface needs correctness floor); 5.8 (FU-9 — shareable shortcuts); 5.11 (factory methods — JSON schema correctness).
- **Sequence position: 16.** Week of July 21-28 (the publication week, post-V1-done).

### 5.17 — Rename to `shortcuts-sdk` (or similar)
- **Source:** Evangelist R1 Move 2.
- **Cost:** S (README + repo rename + GitHub migration)
- **Unlocks:** discovery on the searches that matter; signals that the lib is positioned alongside `anthropic-sdk`, `google-genai`.
- **Depends on:** 5.16 (rename without MCP is noise; rename with MCP is signal).
- **Sequence position: 17.** Same week as 5.16.

### Departures from the Evangelist's 7-week calendar

The Evangelist R2 calendar mostly survives; my changes:

- **`Var[T]` ships in week 3** (parallel with end of equivalence sweep) rather than "before Target A starts" — same effect, but clearer dependency on the equivalence work for the actions Target A uses.
- **Factory methods are post-Target-C, not bundled into Target B** — Evangelist R2 didn't sequence them explicitly, but they're V1.5 polish, not V1-blocking.
- **TypedDicts move from "week of June 30 V2 start" to "week of July 14"**, after `Annotated` slot dispatch centralises the cascade surface. Otherwise the cascade cost dominates the week.
- **Hypothesis is unambiguously V2** (week of July 21), not bundled with V1. The Evangelist R2 calendar was vague on this; the synthesis call is firm.
- **The MCP server scaffold can be drafted in parallel from week 5 onward** (Evangelist R2 noted this) but the publication is week 8, not earlier.

The Evangelist's claim that the rename can happen earlier than the MCP publication ("rename without the MCP is noise; rename with it is signal") survives — they happen the same week.

---

## 6. What this review didn't answer

These came up across multiple agents but couldn't be resolved without further investigation, user input, or work. They become open follow-ups in `docs/handoff.md`.

- **iCloud-share UUID preservation.** Strategy R1 asserted iCloud-shared shortcuts preserve UUIDs; Wire R2 flagged this as unverified — no sample in the corpus is iCloud-imported. The 10-minute test (share from iPhone, import on second device, decode, compare `WFWorkflowIdentifier`) determines whether the deferred `RunWorkflow` composition story has a future. Until done, B7+E1 deterministic-UUID work is scoped to "correct behaviour" only, not "unlocks composition."
- **MCP directory version pinning mechanics.** Evangelist R2 admitted not knowing whether the MCP directory supports version pinning well enough for the update path. 30-minute investigation that gates the MCP publication policy.
- **iOS 26 new-action sample coverage.** Wire R1 noted iOS 26 added 25+ new actions (Visual Intelligence, Create Image, Find Message, Search Photos) with zero corpus coverage. No agent quantified the sample acquisition effort. When does the corpus get extended, and from whose shortcuts?
- **Private sample (`samples/private/voice_note_to_github.shortcut`) as Target A oracle.** Tests R2 noted buzz format is too coarse for Layer 2. Decision: move it to `samples/decoded/` with PAT redacted, or write the equivalence test inline using the decoded XML structure as a comment?
- **`addnewreminder` `WFQuantityFieldValue` modelling.** Wire R1 P2 wants it modelled (5 sample appearances); Strategy R2 says optional for Target B; Pythonic R2 pushed back on modelling before sweep coverage. Decide before Target B starts.
- **Target A scope creep.** Are the ChooseFromMenu continue/done gate and optional metadata Ask part of the re-author, or a follow-on? Strategy R1 included them based on a voice-jot; no cross-commentary confirmed.
- **`text.combine` modelling + `daily_standup` kitchen-sink regression target.** Strategy R1 wanted it; Wire R1 P2 had it as a high-frequency candidate. Medium-value low-cost; worth a 90-minute slot somewhere in V1.
- **Validation-engine ownership (Tests R2 §3).** Single `validate_workflow(workflow) -> list[ValidationFinding]` consumed by both MCP server and audit CLI. Implicit consensus but not made explicit; should be confirmed before MCP scaffold work.
- **`RawAction` UUID asymmetry** (Wire R1 §1.3): freshly-authored `RawAction`s with `.output()` produce dangling pointers if `raw_params` lacks a `UUID` key. Four-line error-message + guard fix; lands alongside LLM-UX error-message rewrite.

---

<!-- For the parent: -->
TLDR: Six agents agree on the 8-week plan. Consensus floor: Literal migration first (1 afternoon), envelope scanner + 21-action equivalence sweep before any external surface, FU-9 + 3 distinct-surface targets define V1-done, Var[T] threading and stale-SKILL fix are easy wins now, MCP server is a consequence of V1 not parallel, cross-platform DSL withdrawn. Three real disputes resolved: factory methods beat @overload (LLM error quality), TypedDicts and @block defer until after equivalence sweep + targets reveal friction, Hypothesis is unambiguously V2.

The 3 user-decisions: (1) personal-tool-first or SDK-first as identity — Evangelist R2 bridged with "personal-first in timeline, SDK-quality per commit"; confirm; (2) is V1 "shareable" (Strategy's higher bar, 7 weeks) or "works for me" (faster, FU-9 deferred); (3) is the natural-language compiler a real direction — if yes, full Pythonic+Hawk V1 typing is critical-path. Open follow-ups for handoff.md include the iCloud UUID test, MCP directory pinning mechanics, iOS 26 sample coverage, and the private-sample-as-oracle question.
