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
| Decode (AEA → AA → bplist) | Done; 21 samples; 678 actions; 388 distinct ids |
| Jellycore facts extraction | Done; 288 actions + 77 enums + 9 structural ids |
| Coverage analysis | Done; ~62% of identifiers in kitchen-sink sample |
| LLM-readable decode output | Not started |
| Encoder + round-trip | Not started |
| Schema layer | Not started |
| Skills (make/edit/decode) | Not started |
| Apple docs digest (vault) | Not started |
| Goal shortcut | Not started |

## Phases

### Phase A — Foundation

A1. Encoder: dict → bplist → optional `shortcuts sign` for AA+AEA wrapping.
A2. Round-trip identity tests against all 21 committed samples.
A3. LLM-readable decode format (`shortcut-decode --format buzz`) — compact
    representation with named variables and indented control flow.

### Phase B — Apple docs digest (parallelisable)

B1. Crawl Apple's official Shortcuts user guide + iOS 26 changelog.
B2. Distil into vault notes at `~/Documents/FMP/tech/Apple_Shortcuts/`,
    following vault conventions (Snake_Case, frontmatter, wikilinks,
    `author: external` with provenance).
B3. Cross-reference from `docs/format.md` and the make-shortcut skill.

### Phase C — Schema layer (tiered)

C1. **Tier 0 — control flow + values.** `If/Else`, `RepeatEach`,
    `RepeatCount`, `ChooseFromMenu`, `Dictionary`, variable references
    (`Var`, `Output`, `CurrentDate`, `Clipboard`, `Ask`, `ShortcutInput`),
    templated strings (`Text("... {x}", x=...)`), typed values
    (`Quantity`, `TimeOffset`). **Plus `RunWorkflow` as the composition
    operator** — first-class so helper shortcuts compose naturally.
C2. **Tier 1 — top 10 by sample frequency.** `setvariable`, `gettext`,
    `ask`, `comment`, `getclipboard`, `setclipboard`, `format.date`,
    `text.replace`, `text.split`, `notification`.
C3. **Tier 2 — vault target actions.** `recordaudio`,
    `TranscribeAudioAction`, `downloadurl`, `base64encode`, plus whatever
    Obsidian's iOS share extension exposes.
C4. **Workflow-level metadata.** Icon, surfaces (`WFWorkflowTypes`),
    accepted/output content item classes, import questions.

### Phase D — Skills

D1. `make-shortcut` — author from a description.
D2. `edit-shortcut` — decode → modify → encode.
D3. `decode-shortcut` — quick "what does this do" digest.
D4. Each skill loads `docs/format.md` + the relevant vault notes; uses the
    schema registry; runs via `uv run` from the lib.

### Phase E — Goal shortcut

E1. **Vault Note → LLM → Git.** Compositional design:
    - `Helpers/Auth_GitHub` — returns Bearer token (variable-only shortcut)
    - `Helpers/Polish_With_LLM` — input: text → output: polished
    - `Helpers/Push_To_Vault_Repo` — input: filename + content → commits
    - `Vault_Note_To_Git` — orchestrator that calls the helpers in order
    Each helper round-trips through the lib; the orchestrator is the
    real test of `RunWorkflow` composition.

## Decisions log

- **2026-05-07** — Python over YAML for now; YAML if the Python ergonomics
  prove cumbersome for the LLM.
- **2026-05-07** — ty + ruff + prek; matches `~/.claude/toolkit/` style.
- **2026-05-07** — Personal use; relicense path open if it proves useful.
- **2026-05-07** — Action-fact dataset bootstrapped by mechanical
  extraction from Open-Jellycore (GPL-3.0). The resulting JSON is a
  derivative compilation; the project as a whole is licensed
  GPL-3.0-or-later to match. See `NOTICE` for the §5(a) modifications
  log.
- **2026-05-07** — Compositional: shortcuts compose via `runworkflow` like
  Python modules. Schema layer treats it as a first-class operator.
- **2026-05-07** — Lib's primary user is Claude. Discoverability, error
  quality, and registry introspection are load-bearing UX.

## Open questions

- LLM step in goal shortcut: Apple Intelligence "Use Model" (free, on-device,
  iOS 26+) vs HTTP to Claude/OpenAI. Lean toward Apple Intelligence first,
  HTTP fallback if features need it.
- Git destination: GitHub API direct (Voice Note shortcut pattern) or via
  Working Copy? GitHub API simplest.
- Vault scope: write into vault or just from? First target is *from*.
