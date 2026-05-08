# Work log

Append-only record of substantive design decisions and surprises. New
entries at the top.

## 2026-05-08 — Overnight autonomous run (continued)

After Phase A/B/C1/C2 landed earlier in the night, took a product-review
pass via a sonnet sub-agent acting as a staff-engineer reviewer
(`docs/product_review.md`). Acted on P1, P3, P4, P5 — skipped P2
(UseModel needs an iOS 26 sample the user hasn't exported yet).

**Tier 2 actions** (commit f3c6544): DownloadURL, Dictionary,
Base64Encode. DownloadURL was the heavyweight: headers and JSON body
both encoded as `WFDictionaryFieldValue` envelopes containing
`WFDictionaryFieldValueItems` arrays. WFHTTPMethod is omitted for GET.
ShowHeaders=True is needed when headers are present so the GUI renders
the section expanded.

**Lift / RawAction** (commit 2ba5deb): unblocks editing arbitrary
shortcuts. Decoded workflow → Shortcut wrapper → mutate → re-encode
works end-to-end for any identifier, modelled or not. Lift round-trip
test parametrises over all 21 samples.

**E1 example — note → GitHub** (commit 84978fb): clipboard → format
date → base64-encode → strip whitespace → PUT to GitHub Files API with
JSON body. Validates Tier 0/1/2 + Auth header + JSON body shape end to
end. Three tests cover action sequence, PUT shape, and signed-file
emission.

**Audio actions** (commit c127d7f, P1): RecordAudio plus the
first-party AppIntent-style TranscribeAudio (uses camelCase
`audioFile` parameter rather than `WF*`-prefixed).

**Helpers + registry visibility** (commit c127d7f, P3+P4):
- `Shortcut.from_file(path, name=)` — sugar for the lift pattern.
- `ExitShortcut`, `GetVariable`, `AppendVariable` — top-30 histogram
  gaps; trivially simple to model, enable guard-clause patterns.
- `list_values()`, `list_control_flow()` so an LLM running
  `list_actions()` doesn't miss `If`, `Text`, `NamedVar`, `CurrentDate`
  etc. — the most-used constructs.
- `describe_action()` now uses `typing.get_type_hints()` to resolve
  forward-ref strings into real types (`dict[str, Any] | None`,
  `str | None` etc.). Was returning `"Any"` for everything.
- `scripts/print_actions.py` prints all three sections.

**Composition example** (commit c127d7f, P5):
`examples/vault_note_to_git.py` — a polish helper, a push helper, and
an orchestrator linked via RunWorkflow with real Shortcut instances.
LLM step is a placeholder pending UseModel.

**Skill updates** (~/.claude/skills/, not in this repo):
- make-shortcut points to `print_actions.py` for the full surface.
- mentions `open ~/Desktop/<Name>.shortcut` as the quickest macOS import.
- Composition pattern now references the worked example.

**Final state**: 170 tests pass, 19 registered actions across Tier 0/1/2,
3 skills written (make/edit/decode), 8 vault notes documenting Apple's
design intent. The vault → LLM → git goal shortcut is now scaffolded —
real LLM integration waits on the user exporting a Use Model sample for
schema verification.

## 2026-05-08 — Overnight autonomous run

**Phase A complete.** Decode + encode + round-trip + LLM-readable buzz
format all green. plistlib handled every quirk we worried about (key order,
bool/int discrimination, bytes vs str) on first try; no encoder edge cases
to debug.

**Phase B complete.** B1 sub-agent (sonnet) crawled 21 Apple doc pages
into `docs/apple_raw/`. B2 sub-agent (sonnet) distilled them into 8 vault
notes at `~/Documents/FMP/tech/Apple_Shortcuts/`:

- `Design_Intent.md` — content graph, surfaces, composition
- `Magic_Variables.md` — types, scope, lifecycle
- `Content_Item_Classes.md` — accepted/produced types
- `Control_Flow.md` — If, Repeat, Choose-from-Menu encoding
- `URL_Schemes.md` — `shortcuts://` reference + x-callback-url
- `Personal_Automation.md` — triggers including macOS 26 additions
- `iOS_26_Highlights.md` — Use Model action, Writing Tools
- `Action_Reference_Index.md` — nav hub linking lib + Apple docs

Key insight from B2: **iOS 26's `Use Model` action** is the natural pivot
for the vault → LLM → git goal shortcut. It's a first-class action that
pipes Apple Intelligence (or ChatGPT) output into the Shortcuts data flow.

**Phase C in progress.**

C1 (Tier 0 schema) — done by opus.
- Functional control-flow API (`If(cond, then=[...], otherwise=[...])`),
  flat-encoded with paired `GroupingIdentifier` markers.
- `RunWorkflow` is first-class composition. Accepts `Shortcut` instances,
  `(identifier, name)` tuples, or `"self"` (resolved at emit time).
- `Text` does UTF-16 range computation including supplementary-plane chars.
- Registry auto-discovers modules in `schema/actions/` — adding a new
  action means dropping a `.py` file, no shared-file edits.

C2 (Tier 1 actions) — 9 sonnet sub-agents dispatched in parallel:
SetVariable, GetText, AskForInput, Comment, GetClipboard, FormatDate,
TextReplace, TextSplit, ShowNotification. Each only modifies its own
action file + test file (no shared-file collisions thanks to the
auto-discovery registry).

**Decisions taken**

- **No WFWorkflowName in the bplist.** None of the decoded samples have
  it; the Shortcuts app uses the imported file's filename for display.
  Builder keeps `self.name` for composition (RunWorkflow.workflowName)
  and signed-filename use only.
- **Functional over context-manager control flow.** LLMs find functional
  patterns easier — `If(cond, then=[...])` is one expression, no
  statefulness. Scope rules become the schema's problem on emit.
- **Auto-discovery in `actions/__init__.py`.** Eliminates a shared file
  every parallel C2 agent would otherwise need to edit.
- **Jellycore parameter names are hints, not ground truth.** Confirmed:
  `AskForInputParameter.swift` declares `var type:` but Apple's plist
  uses `WFInputType`. Sub-agents are instructed to verify against
  decoded samples.
- **Skip `prek` and `ty` in sub-agent runs.** They check the whole tree
  and would race with parallel agents. The orchestrating opus does one
  consolidated `prek run --all-files` pass after sub-agents merge.

**Open / next**

- C2 consolidation: full pytest + prek pass; commit Tier 1 in logical
  batches.
- D1 (make-shortcut skill): pending C2 consolidation.
- C3 (vault-target actions): `recordaudio`, `TranscribeAudioAction`,
  `downloadurl`, `base64encode`. Voice Note → GitHub gives ground truth.
- E1 (vault → LLM → git): blocked on C3 + D1.
