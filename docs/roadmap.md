# shortcut-lib roadmap

## Vision

A Python library for authoring, decoding, and modifying Apple Shortcuts —
designed so an LLM (Claude) can be the primary author. The lib is the surface
the LLM operates against; the human (Findlay) tells the LLM what shortcut to
make, edit, or polish.

## Goals

- **LLM-authored shortcuts.** Claude can scaffold, modify, and round-trip
  shortcuts with high reliability and small token cost.
- **Compositional.** Shortcuts call other shortcuts (`runworkflow`) the way
  Python modules import each other. Helper shortcuts are first-class.
- **Round-trip is gospel.** decode → modify → encode preserves bytes (or at
  worst, semantically-equivalent dicts). Without this, "edit this shortcut"
  silently corrupts.
- **Real targets.** Author shortcuts that do useful work — vault note →
  LLM → git is the first concrete target.

## Design principles

1. **Decode first, encode second; round-trip everywhere.** Every encoder
   must be exercised against a real decoded sample.
2. **Discoverability over conciseness.** A registry of supported actions
   that Claude can list, grep, and introspect at runtime.
3. **Errors are training signal.** `expected X, got Y` not `invalid input`.
   The LLM uses the error to correct.
4. **Composable.** `RunWorkflow` is a top-level construct. Helper shortcuts
   become modules; orchestrator shortcuts become application entry points.
5. **Typed Python API for now.** No YAML until the Python surface settles.
6. **Personal use polish bar.** Don't over-invest in packaging, but errors
   and docstrings deserve real care because they're the LLM's interface.

## Current state (2026-05-08)

| Layer | Status |
|-------|--------|
| Decode (AEA → AA → bplist) | Done; 20 public + 1 private sample; 678 actions; 388 distinct ids |
| Jellycore facts extraction | Done; 288 actions + 77 enums + 9 structural ids |
| Coverage analysis | Done; ~62% of identifiers in kitchen-sink sample |
| LLM-readable decode output | Done; `--format buzz` (informational; non-round-tripping) |
| Encoder + round-trip | Done; bplist + `shortcuts sign`; 262 tests incl. round-trip, lift round-trip, wire-format equivalence |
| Schema layer (Tier 0/1/2 + Apple Intelligence) | Done; 24 leaf actions + control flow (`If`, `RepeatCount`, `RepeatEach`, `ChooseFromMenu`) + values (`Text`, `NamedVar`, `Output`, `Self`) + `RunWorkflow` composition; auto-discovering registry; `RawAction` passthrough |
| Workflow-level metadata (C4) | Partial; `_extra` preserves un-modelled top-level keys on lift; first-class authoring API for icon / surfaces / accepted-input / output classes is the next gap |
| Skills (make/edit/decode) | Done; in-repo at `skills/`, symlinked into `~/.claude/skills/` |
| Apple docs digest (vault) | Done; 8 notes under `~/Documents/FMP/tech/Apple_Shortcuts/` |
| Goal shortcut (`Vault Note To Git`) | Done; validated on iPhone (iOS 26.4.2 + Apple Intelligence) on 2026-05-09. Single self-contained shortcut; clipboard → polish → GitHub commit. Notes in `examples/VALIDATION_vault_note_to_git.md` |
| Deep review action list | Closed; B1–B8, SF-batch1–7, N-batch nits all landed |
| Licence + attribution | Done; GPL-3.0-or-later, NOTICE, narrative `docs/sources.md` |

## Phases

### Phase A — Foundation _(done)_

A1. ✅ Encoder: dict → bplist → optional `shortcuts sign` for AA+AEA wrapping.
A2. ✅ Round-trip identity tests against all committed samples.
A3. ✅ LLM-readable decode format (`shortcut-decode --format buzz`) — compact
    representation with named variables and indented control flow.

### Phase B — Apple docs digest _(done)_

B1. ✅ Crawl Apple's official Shortcuts user guide + iOS 26 changelog.
B2. ✅ Distil into vault notes at `~/Documents/FMP/tech/Apple_Shortcuts/` —
    8 notes (Design_Intent, Magic_Variables, Content_Item_Classes,
    Control_Flow, URL_Schemes, Personal_Automation, iOS_26_Highlights,
    Action_Reference_Index).
B3. ✅ Cross-reference from `docs/format.md` and the make-shortcut skill.

### Phase C — Schema layer _(C1–C3 done, C4 partial)_

C1. ✅ **Tier 0 — control flow + values.** `If`/`Else`, `RepeatEach`,
    `RepeatCount`, `ChooseFromMenu`, `Dictionary`, variable references
    (`NamedVar`, `Output`, `Self`, magic variables), templated strings
    (`Text("... {x}", x=...)`), and `RunWorkflow` as the composition
    operator.
C2. ✅ **Tier 1 — top sample-frequency actions.** `setvariable`, `gettext`,
    `ask`, `comment`, `getclipboard`, `setclipboard`, `format.date`,
    `text.replace`, `text.split`, `notification`.
C3. ✅ **Tier 2 — vault target actions.** `recordaudio`,
    `TranscribeAudioAction`, `downloadurl`, `base64encode`, plus
    Apple Intelligence (`UseModel`, Writing Tools).
C4. 🟡 **Workflow-level metadata.** `_extra` preserves un-modelled top-
    level keys on lift; first-class authoring API for icon, surfaces
    (`WFWorkflowTypes`), accepted/output content item classes, and
    import questions is the next gap.

### Phase D — Skills _(done)_

D1. ✅ `make-shortcut` — author from a description.
D2. ✅ `edit-shortcut` — decode → modify → encode.
D3. ✅ `decode-shortcut` — quick "what does this do" digest.
D4. ✅ In-repo at `skills/`, symlinked into `~/.claude/skills/`; each
    loads `docs/format.md` and the schema registry; runs via `uv run`.

### Phase E — Goal shortcut _(done)_

E1. ✅ **Vault Note → LLM → Git.** `examples/vault_note_to_git.py`
    emits a single self-contained `Vault Note To Git.shortcut`:
    clipboard → Apple Intelligence "Use Model" polish → GitHub Files
    API PUT → notification. Validated end-to-end on iPhone
    (iOS 26.4.2 + Apple Intelligence) on 2026-05-09. Token + repo are
    placeholder Text actions; the user edits them in Shortcuts.app
    after import. See `examples/VALIDATION_vault_note_to_git.md` for
    setup and lessons.

    The original brief called for compositional helper *Shortcuts*
    linked via `RunWorkflow`. iOS strips and reassigns shortcut UUIDs
    at import time, so locally-signed `.shortcut` files can't pre-link
    helpers — every import would require manual re-selection. The
    composition story shifted to Python helper *functions*
    (``_add_config``, ``_add_polish``, ``_add_push``) that build a
    single workflow. See the 2026-05-09 decisions-log entry.

## Decisions log

- **2026-05-07** — Python over YAML for now; YAML if the Python ergonomics
  prove cumbersome for the LLM.
- **2026-05-07** — ty + ruff + prek; matches `~/.claude/toolkit/` style.
- **2026-05-07** — Personal use; relicense path open if it proves useful.
- **2026-05-07** — Action-fact dataset projected from Open-Jellycore
  (GPL-3.0). See `NOTICE` for attribution.
- **2026-05-07** — Compositional: shortcuts compose via `runworkflow` like
  Python modules. Schema layer treats it as a first-class operator.
- **2026-05-07** — Lib's primary user is Claude. Discoverability, error
  quality, and registry introspection are load-bearing UX.
- **2026-05-08** — Phases A, B, D done; C done bar C4 (workflow-level
  metadata authoring API). Deep-review action list (B1–B8 + SF-batch1–7
  + N-batch nits) closed. Remaining gating work for the lib's first
  real target is on-device validation of `Vault_Note_To_Git`.
- **2026-05-09** — Composition story pivoted: Python *functions* compose
  the steps; each `Shortcut` emits as one self-contained workflow.
  iOS reassigns UUIDs on import and ignores any identifier in a
  locally-signed `.shortcut`, so `RunWorkflow` cannot pre-link
  helpers — every import would require manual re-selection.
  `RunWorkflow` stays in the schema for cases where a genuinely
  separate trigger is required (Setup-only auth helpers, iCloud-shared
  utilities), but is no longer the default composition operator.
- **2026-05-09** — `Vault Note To Git` validated end-to-end on iPhone
  (iOS 26.4.2 + Apple Intelligence). Closed Phase E1.
- **2026-05-09** — Three instances of the same envelope bug class
  (`WFURL`, JSON body dict values, `WFDate`) found and fixed via a
  shared `coerce_text_field` helper that rewraps bare
  `WFTextTokenAttachment` envelopes as single-attachment
  `WFTextTokenString`. SF-batch6's "Apple is permissive" assumption
  was selectively wrong — Apple is permissive for plain literals but
  not for variable references. A deliberate sweep over all action
  parameter slots is filed as FU-7.

## Open questions

- LLM step in goal shortcut: Apple Intelligence "Use Model" (free, on-device,
  iOS 26+) vs HTTP to Claude/OpenAI. Lean toward Apple Intelligence first,
  HTTP fallback if features need it.
- Git destination: GitHub API direct (Voice Note shortcut pattern) or via
  Working Copy? GitHub API simplest.
- Vault scope: write into vault or just from? First target is *from*.
