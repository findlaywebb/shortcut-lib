# Round 1 — Wire-Format Pragmatist Review

_Agent: Wire-Format Pragmatist. Lens: Apple's wire format is the source of
truth. Schema abstractions that don't survive contact with a new sample are
technical debt waiting to bite._

---

## 1. Current-state critique

### 1.1 Round-trip semantics — what the tests actually guarantee

There are three distinct round-trip modes and they make very different claims.

**`test_round_trip.py`** (`decode → encode_to_bplist → re-decode`) guarantees
the plist round-trips without schema involvement. This is the strongest test:
it is a pure byte-identity check on Apple's serialised format. It never
touches the schema layer; `plistlib.dumps(plistlib.loads(x)) == x` for these
samples. This test proves the decode+encode pipeline is a no-op. It does not
prove the schema emits correct wire.

**`test_lift_round_trip.py`** (`decode → from_workflow → to_workflow`)
exercises the full top-level dict. Since B5 was fixed, `_extra` now absorbs
every unmodelled top-level key, and `to_workflow` merges it back verbatim.
The test (`test_lift_then_emit_preserves_full_top_level`) asserts full key
equality with an empty allowlist. This is a meaningful regression guard.
Confirmed: it covers `WFWorkflowImportQuestions` destruction that was
previously invisible.

**`test_wire_format_equivalence.py`** (`schema-built Action → compare against
decoded sample`) is the honest correctness test. Currently covers 7 actions:
`AskForInput`, `SetVariable`, `GetText`, `SetClipboard`, `ShowNotification`,
`DownloadURL`, and `Dictionary` (empty). These 7 are grounded in real samples.
The other 21 modelled actions — the 14 leaf actions not in this file — have
their wire format validated only by their own construction. That is a
tautology: the schema emits what the schema says it should emit.

**The gap**: `RecordAudio`, `TranscribeAudio`, `Base64Encode`, `FormatDate`,
`TextReplace`, `TextSplit`, `DictateText`, `AppendVariable`, `GetVariable`,
`ExitShortcut`, `GetClipboard`, `UseModel`, Writing Tools actions, and
`Comment` all fall into the tautology category. For these, the wire format
test does not exist or points at the action's own output as the oracle. When
Apple changes a parameter slot's envelope type on a future iOS update, no test
will catch it.

### 1.2 Unmodelled-but-frequent identifiers

The inventory script against all 21 decoded samples (687 total action
invocations, 393 distinct identifiers) reveals these unmodelled actions
appearing five or more times:

| Count | Identifier | Jellycore hint params |
|------:|-----------|----------------------|
| 7 | `is.workflow.actions.file.rename` | `WFFile`, `WFNewFilename` |
| 5 | `is.workflow.actions.addnewreminder` | not in Jellycore catalogue |
| 5 | `is.workflow.actions.text.combine` | `text`, `combine`, `WFTextCustomSeparator` |
| 5 | `is.workflow.actions.sendmessage` | not in Jellycore catalogue |
| 4 | `is.workflow.actions.previewdocument` | `WFInput` |
| 4 | `is.workflow.actions.filter.calendarevents` | no params in Jellycore |

Wire-format evidence from samples:

- **`file.rename`** (`rename_files.xml`): `WFFile` arrives as
  `WFTextTokenAttachment` (a named variable reference), `WFNewFilename` as
  `WFTextTokenString` with an attachment. Two distinct envelope types in the
  same action — exactly the class of bug that closed FU-7.

- **`addnewreminder`** (`batch_add_reminders.xml`): `WFCalendarItemTitle` is
  a `WFTextTokenString`, `WFAlertLocationRadius` uses `WFQuantityFieldValue`
  (the `{Magnitude, Unit}` shape from `docs/format.md`). A rich parameter set
  with two distinct non-trivial envelope types. Not in Jellycore — no hint
  source for parameter names.

- **`text.combine`** (`sort_lines.xml`): `text` key holds a
  `WFTextTokenAttachment` envelope (single variable reference). Jellycore
  names the separator param `combine` and `WFTextCustomSeparator`; the sample
  does not include either (default separator, no separator key emitted) — so
  the Jellycore names are unverified. The `Show-text` key appears here too (a
  UI-toggle pattern that also shows up in `text.split`).

The 365 unmodelled identifiers are not all equal: 293 of them appear exactly
once in samples, meaning the corpus itself is sparse. What the 62% modelling
figure actually means is: 38% of identifiers have a `RawAction` passthrough,
and for the high-frequency ones, Apple's parameter shape is visible in
samples but not yet encoded in typed schema.

### 1.3 `RawAction` — what its contract actually guarantees

`RawAction` holds `raw_identifier: str` and `raw_params: dict[str, Any]`
verbatim. `to_action_dict` returns them without modification. This means:

- **On lift**: every action in a decoded workflow becomes a `RawAction`
  preserving the exact Apple wire dict. Round-trip is exact. Good.
- **On authored use**: a caller can construct `RawAction(raw_identifier="...",
  raw_params={...})` to emit any action without schema. The contract is that
  whatever goes into `raw_params` comes back out; there is no validation and
  no UUID injection. The `Action.to_action_dict` base path injects `UUID` from
  `self.uuid`; `RawAction.to_action_dict` bypasses that path and emits
  `raw_params` as-is. If `raw_params` already contains a `UUID` key (as all
  lifted actions do), it passes through correctly. If an LLM authors a
  `RawAction` without a `UUID` key and then references `.output()`, the
  reference will use the dataclass-generated `uuid` field but the emitted
  dict will not contain that UUID — the downstream reference will be
  dangling.

This is a subtle asymmetry: for lifted actions the UUID is in `raw_params`
(correct); for freshly-authored `RawAction`s the UUID is in `self.uuid` but
not emitted (broken if referenced). The docstring does not document this.

**Per-action `_extra` is absent.** `_extra` at the `Shortcut` level absorbs
un-modelled top-level keys. There is no equivalent at the action level. If a
future iOS version adds a new parameter slot to, say, `is.workflow.actions.ask`
that the typed `AskForInput` schema does not model, a lift→emit round-trip
through `from_workflow` will preserve it (because `from_workflow` uses
`RawAction` for everything). But an authored `AskForInput` constructed via the
typed class will silently omit that slot. There is no `_extra` on `AskForInput`
to bridge this.

### 1.4 Known wire-format pitfalls — a working checklist

Based on the sample corpus and the FU-7 sweep:

1. **`WFTextTokenString` vs `WFTextTokenAttachment`**: slots that Apple reads
   as templated strings (`WFURL`, `WFDate`, `WFNotificationActionTitle/Body`,
   `WFLLMPrompt`, `WFAskActionPrompt`, `WFCommentActionText`,
   `WFReplaceTextFind/Replace`) reject a bare `WFTextTokenAttachment` for
   variable references; they present as empty at runtime ("No URL Specified").
   The fix (`coerce_text_field`) is now applied to these slots. The risk: any
   newly-modelled action must correctly classify each slot as text-token-string
   or attachment at modelling time.

2. **Empty `WFItems` suppression for `Dictionary`**: Apple omits the `WFItems`
   key entirely for an empty Dictionary action; emitting an empty
   `WFDictionaryFieldValue` envelope is wrong. Fixed. The pattern recurs:
   many Apple slots use "omit key entirely" to signal default state, not
   "emit empty container".

3. **Non-GET `WFHTTPMethod` presence**: Apple omits `WFHTTPMethod` for GET
   requests; the schema correctly mirrors this (`DownloadURL._params`). The
   inverse trap: add a new HTTP method action and forget to suppress the
   default-method emit.

4. **`WFControlFlowMode` integers vs strings**: older shortcuts-js encoded
   `WFCondition` as `"Equals"` (string); current iOS uses integer `0`. The
   schema uses integers. Confirmed via `docs/format.md`. But the full enum is
   not yet mapped — `WFCondition` integer `100` appears in
   `batch_add_reminders.xml` for a reminders-specific condition that is
   undocumented.

5. **`WFQuantityFieldValue` for measurement slots**: `addnewreminder`'s
   `WFAlertLocationRadius` uses `{Magnitude: "250", Unit: "ft"}` wrapped in
   `WFQuantityFieldValue`. The Magnitude is a **string** `"250"`, not an
   integer. This is easy to get wrong.

6. **`Show-text` UI toggle key**: appears in `text.split` and `text.combine`
   samples as a bare boolean key at the top of the parameters dict. No typed
   action models this; `RawAction` preserves it. Any authored `TextSplit`
   will omit `Show-text`, which changes the UI appearance but not runtime
   behaviour.

7. **`WFNewFilename` for `file.rename`**: uses `WFTextTokenString` (with
   substitution), while `WFFile` uses `WFTextTokenAttachment` (single
   variable). Correctly classifying these two slots requires reading the
   sample — Jellycore's parameter hints (`WFFile`, `WFNewFilename`) do not
   carry envelope-type information.

8. **`WFWorkflowClientVersion` hardcoded to `"4033.0.4.3"`**: all 21
   committed samples carry this version. Apple shipped iOS 26 in September
   2025 and 26.x.x releases through at least 26.4.2 (validated). The
   version string has not yet caused an import rejection in testing, but the
   field exists for a reason. Future point releases may start gating on it.

### 1.5 Decode vs encode coverage asymmetry

The decoder accepts any `.shortcut` file regardless of action identifier —
every action passes through `RawAction`. The encoder can only produce correct
wire for the 28 modelled identifiers; for anything else the caller must
provide the raw dict manually via `RawAction`. This asymmetry is not
prominently documented. `docs/roadmap.md` mentions `RawAction` passthrough
for the lift path; the skill docs (`skills/make-shortcut/SKILL.md`) do not
call out "you can only author these 28 identifiers with type safety". An LLM
reading the registry via `describe_action` will see 28 actions and may
incorrectly assume that is the full universe.

---

## 2. Ideal-state thesis

### 2.1 What sample-grounded confidence looks like

A modelled action is sample-grounded when all three of these are true:
(a) there exists at least one decoded sample containing that identifier;
(b) a `test_wire_format_equivalence.py` test asserts that the schema's emit
matches the sample's wire form (after normalisation); and
(c) each parameter slot's envelope type (`WFTextTokenString`,
`WFTextTokenAttachment`, bare scalar, `WFDictionaryFieldValue`, etc.) is
documented in an inline comment citing the sample file and element.

Currently only 7 of 28 modelled actions satisfy condition (b). The others
may be correct, but we do not know. FU-7's finding — that six slots had the
wrong envelope type, and the deep review's batch6 demoted it from blocker
because "Apple is permissive" — is the clearest evidence that plausible-
looking schema can be concretely wrong. The cost of being wrong is that
shortcuts run fine for literal strings (Apple is permissive for literals) but
silently break for variable references at runtime.

**The sample corpus should be the living oracle.** When an action's parameter
slot is ambiguous, the question "which envelope does Apple use here?" is
answered by: decode a real shortcut containing that action with a variable
reference in that slot, then read the XML. Any claim not backed by a sample
is a hypothesis.

### 2.2 The "lifted vs authored" contract

There should be two explicitly distinct authoring modes:

- **Lifted**: a decoded workflow passed through `from_workflow`. Every action
  is a `RawAction`. Round-trip is exact by construction. The schema layer is
  not involved. This is the correct path for "edit this existing shortcut".

- **Authored**: actions constructed via the typed schema layer. The schema
  layer owns the wire format for these identifiers. Only actions that have
  passed a wire-format equivalence test against a sample are fully trustworthy
  for variable references (not just literal strings).

These two modes should be documented as distinct. An LLM building a new
shortcut from scratch should understand that for identifiers outside the 28
modelled ones, it has two choices: use `RawAction` with a hand-crafted
parameters dict, or ask the lib to decode a reference shortcut first and
inspect what Apple emits.

### 2.3 Absorbing iOS version drift

The strategic posture needs to be:

1. **Passive drift detection**: a scanner script run against newly-decoded
   samples that checks whether each parameter slot in a typed action matches
   the observed envelope type. If a slot that was `WFTextTokenString` in
   iOS 26.4.2 becomes something else in iOS 27, the scanner should flag it.
   This is a 50-line Python script that can be run whenever a new sample is
   decoded.

2. **`WFWorkflowClientVersion` as a dial, not a constant**: the field is
   named `_CLIENT_VERSION` in `builder.py` with a comment pointing to FU-2.
   The ideal state is: expose it as a `Shortcut` field with a documented
   default, and have a test that decodes the output and asserts the version
   is present and not `None`. When Apple starts rejecting stale versions,
   the fix is a one-line bump plus a test update — not a search-and-replace.

3. **The iOS 26 new actions are not yet in samples**: iOS 26 added 25+ new
   actions (Visual Intelligence, Create Image, Find Message, Search Photos,
   etc.). None of these appear in the current 21 samples. If a user asks the
   LLM to "send a message via the new Messages Find Conversation action", the
   lib has no wire-format evidence for those identifiers. The correct response
   is `RawAction` with a note that the slot has not been verified. The wrong
   response is to invent parameters from Jellycore hints and emit confidently.

4. **App Intents drift is faster than `is.workflow.actions.*` drift**: the
   third-party app intent identifiers (`com.apple.WritingTools.*`,
   `com.apple.clock.*`, `com.microsoft.*`) are controlled by individual app
   teams with independent release cycles. Writing Tools actions are modelled
   and iOS-26-validated. Clock actions (`com.apple.clock.*` appearing in
   samples) are not modelled. Any `com.*` identifier in samples is a potential
   future breakage point.

---

## 3. Top 3 concrete proposals

### Proposal 1 — Wire-format equivalence sweep for all 21 modelled leaf actions

**Priority**: high
**Effort**: medium (estimated 3–4 hours; mostly reading sample XML and writing
boilerplate)

The 21 leaf actions without wire-format equivalence tests are operating on
faith. The FU-7 outcome proves this faith is sometimes wrong. A sweep that
adds one equivalence test per action — or documents why no sample exists —
turns silent unknown unknowns into either passing tests or explicit TODO
markers.

**Concrete steps:**

1. For each modelled leaf action (`RecordAudio`, `TranscribeAudio`,
   `Base64Encode`, `FormatDate`, `TextReplace`, `TextSplit`, `DictateText`,
   `AppendVariable`, `GetVariable`, `ExitShortcut`, `GetClipboard`,
   `UseModel`, Writing Tools actions, `Comment`):
   a. Search decoded samples for an invocation. Use the scanner script.
   b. If found: assert `schema.to_action_dict()` normalised == sample action
      normalised. Document the sample file:action-index in the test docstring.
   c. If not found: add a `pytest.skip` with message `"No sample exists; add
      a decoded shortcut containing <identifier> to remove this skip."` This
      makes the gap visible.

2. Run the full test suite. Any test that fails surfaces a concrete schema
   error — fix before committing.

3. For slots that are tricky (e.g. `RecordAudio` which has no output UUID,
   `TranscribeAudio` which takes an audio file reference): inspect the sample
   manually for the actual envelope type and document it with an inline
   comment in the action file: `# samples/decoded/X.xml line N: WFInput is
   WFTextTokenAttachment here`.

**Success criterion**: every modelled leaf action either passes a sample-
grounded equivalence test, or has a skip with a documented explanation. The
tautology class shrinks to zero.

---

### Proposal 2 — Model the top 5 unmodelled high-frequency identifiers from samples

**Priority**: medium
**Effort**: medium (estimated 4–6 hours for all 5; 1 hour each, smaller for
simple params)

The five identifiers appearing 4+ times in samples but not modelled are
actionable with sample evidence already in hand:

| Identifier | Count | Sample file | Known wire keys |
|-----------|------:|-------------|----------------|
| `file.rename` | 7 | `rename_files.xml` | `WFFile` (WFTextTokenAttachment), `WFNewFilename` (WFTextTokenString) |
| `text.combine` | 5 | `sort_lines.xml` | `text` (WFTextTokenAttachment), `combine` enum?, `WFTextCustomSeparator` |
| `addnewreminder` | 5 | `batch_add_reminders.xml` | `WFCalendarItemTitle` (WFTextTokenString), `WFAlertLocationRadius` (WFQuantityFieldValue), `WFFlag`, `WFCalendarItemNotes`, `WFAlertCondition` |
| `previewdocument` | 4 | multiple | `WFInput` (WFTextTokenAttachment) |
| `filter.calendarevents` | 4 | `daily_standup.xml` | complex filter shape — may deserve `RawAction` until verified |

For `previewdocument` the pattern is a single `WFInput` — a trivial
typed schema. For `addnewreminder`, the `WFQuantityFieldValue` shape
(`{Magnitude: "250", Unit: "ft"}` with string Magnitude) and the absence
from Jellycore's catalogue (no hint source) makes it higher-risk;
the sample evidence at `batch_add_reminders.xml` is the guide. For
`filter.calendarevents`, the filter shape (sorting, limit, date-range
conditions) is complex enough that a `RawAction` + comment is safer than
a half-modelled schema.

**Concrete steps for each:**
1. Decode the sample to confirm the exact wire format.
2. Write the action module in `src/shortcut_lib/schema/actions/`.
3. Add a wire-format equivalence test citing the sample line.
4. Run the full test suite.

**Do not model `sendmessage` (5 occurrences) in this batch**: it
requires a contact picker reference type (`WFSendMessageRecipients`) that
has not been observed as a plain variable reference. Modelling it wrong
is worse than `RawAction`.

---

### Proposal 3 — Envelope-type scanner script as a living CI artefact

**Priority**: high
**Effort**: small (estimated 2 hours)

The FU-7 sweep was a one-off. The root cause — a mismatch between the
schema's assumed envelope type and the envelope type Apple actually uses —
will recur every time an action is modelled from Jellycore hints rather than
sample evidence. A preventive scanner script run on decode would catch this
class of error before it reaches `save_signed`.

**Concrete steps:**

1. Write `scripts/scan_envelope_types.py`. For each decoded sample, for each
   action invocation, for each parameter key that is a dict with a
   `WFSerializationType`, record `(identifier, param_key, serialization_type)`.
   Group by `(identifier, param_key)` and report any key observed with more
   than one serialization type (that is a polymorphic slot; document it) and
   any key observed with a type different from what the typed schema emits
   (that is a bug candidate).

2. Bake the output into `data/observed_envelope_types.json`. This is the
   empirical record — checkable by eyeball and diffable when new samples
   arrive.

3. Add a pytest test that, for each modelled action identifier, for each
   parameter slot, asserts the schema's emit type matches the observed type
   in `observed_envelope_types.json`. If a sample shows `WFTextTokenAttachment`
   for a slot the schema emits as `WFTextTokenString`, the test fails. This
   makes the FU-7 class of error automatically detected for modelled actions
   going forward.

4. Run the scanner whenever a new sample `.shortcut` file is decoded and
   committed. Gate on diff: if `observed_envelope_types.json` changes, the
   diff is reviewable.

**Why this is high priority**: this script would have caught all six FU-7
regressions before they were submitted to Apple's runtime. It converts a
class of "works for literals, fails for variables" bugs from runtime-
discovered to pre-commit-caught. It also serves as documentation: the file
is the empirical record of what Apple emits, cross-referenceable with the
schema source.

---

## Appendix: raw numbers from the scanner

Inventory run against 21 decoded XML files (21 = 20 public + 1 private):

```
Total action invocations:   687
Distinct identifiers:       393
Modelled in registry:        28  (21 leaf + 5 control-flow + 2 implicit)
Identifiers with 5+ sample appearances:  16
Unmodelled identifiers with 5+ appearances:  6 (file.rename, addnewreminder,
                                               text.combine, sendmessage,
                                               previewdocument, filter.calendarevents)
Wire-format equivalence tests covering modelled actions:  7 of 28
WFWorkflowClientVersion unique value:  "4033.0.4.3" (all 21 samples)
Open-Jellycore last release:  v1.1.0, October 2023 (pre-iOS-26)
```

Jellycore's parameter hints are iOS-14-era for most actions; the two
highest-frequency unmodelled actions (`addnewreminder`, `sendmessage`) are
absent from its catalogue entirely. Apple's iOS 26 Shortcuts additions (25+
new actions including `com.apple.Photos.PhotosSearchAssistantIntent`,
`com.apple.news.*`, and the new Sports and Voice Memos actions) have zero
sample coverage and zero Jellycore hints — they are `RawAction`-only territory
until new samples are decoded.
