# Architecture Review — Round 1: Product / Use-Case Strategy

_Reviewer: Product / Use-Case Strategist_
_Date: 2026-05-09_

---

## 1. Current-state critique

### What we have

A working foundation: decoder, encoder, round-trip test suite, 24 schema-modelled
actions, and one validated end-to-end target (`Vault Note To Git`). The lib signs
real `.shortcut` files that Apple imports and runs. The skills layer (`make-shortcut`,
`edit-shortcut`, `decode-shortcut`) means Claude Code can already be the primary
author without knowing the wire format. That's a meaningful starting position.

The private `voice_note_to_github.shortcut` sample tells us Findlay had a voice
→ GitHub workflow in production _before_ this lib existed — built by hand in the
Shortcuts editor. The voice jots in `~/Documents/FMP/jots/voice/` confirm that
workflow is actively used: seven entries in two days, each a `.m4a` plus a
transcribed markdown note with frontmatter. This isn't a demo use case; it's
daily personal infrastructure. The lib's job is to make improving and extending
that infrastructure low-friction.

### Where it falls short

**The gap between "lib works" and "lib serves real personal use" is mostly the
Setup section.** Every target so far (vault note, voice note, note-to-github)
requires the user to open the shortcut in Shortcuts.app after import and edit
placeholder Text actions to fill in credentials. FU-9 (`WFWorkflowImportQuestions`
authoring) is the difference between "shortcut you drag in and run" and "shortcut
you drag in, fill in a form, and run". That form is Apple's native Setup flow:
name your repo, paste your PAT, pick your target list. The current workaround
(hardcoded placeholder strings) is friction at every re-import or configuration
change. For the user as their own power user this is tolerable. For sharing or
re-running on a new device it breaks the experience.

**The action vocabulary is shallow for the user's actual workflow needs.** The voice
jot at `voice_2026-05-07_23-24-09.md` dictates three specific shortcuts the user
wants: (1) highlight text → right-click → add to jot, (2) Spotlight bar → write a
task → add to daily note, (3) webpage on Mac → add as note in daily note. None of
these are authoring exercises; they're real personal tools the user intends to use.
They each require actions the lib doesn't yet model: `addnewreminder` (or an append
to a file/note via URL scheme), macOS share-sheet / Services menu integration,
and the new iOS/macOS 26 "Spotlight input" surface. The schema covers the GitHub
API PUT pattern well — it doesn't yet cover the inbound capture patterns.

**The composition story is closed but underexplored.** The decision to pivot from
RunWorkflow composition to Python function composition was correct and the validation
proves it works. But we've only exercised the pattern once. The three pending targets
have meaningfully different trigger surfaces (share-sheet, Spotlight, automation
trigger) and it's not clear the current `Shortcut(surfaces=[...])` API handles
them cleanly. The `WFWorkflowInputContentItemClasses` and `WFWorkflowTypes` fields
(C4, partially done) are untested for share-sheet and automation contexts.

**The deterministic UUID question (B7) is still open.** Every time the build script
re-runs, `workflow_identifier` changes. For personal use this is invisible — you
import, it works. But the moment a target needs stable identity for cross-shortcut
linking (even just for future iCloud-share exploration), the instability matters.
This is a clean-up task, not a blocker for the next three targets, but it's the
kind of debt that compounds.

**The existing examples are all clipboard-in → API-out.** `dictate_to_clipboard`,
`note_to_github`, `vault_note_to_git` — same skeleton. The architecture hasn't been
stressed by a fundamentally different shape: inbound from share-sheet, write to a
local store rather than GitHub, or respond to an automation trigger rather than
user tap. Until we have one target in each of those shapes, we haven't validated
the design broadly.

---

## 2. Ideal-state thesis

### What V1-done looks like

Five real, useful, distinct shortcuts authored end-to-end with the lib — where
"distinct" means distinct trigger surfaces and action patterns, not just different
GitHub repo names. The five should collectively exercise:

1. Clipboard input (done: `vault_note_to_git`)
2. Voice input with audio commit (done: `voice_note_to_github` was hand-built;
   re-authoring via the lib is a natural next step)
3. Share-sheet / selected-text input (not yet authored via lib)
4. Automation trigger (time-based or file-based; not yet done)
5. User-prompted input with Setup section (blocked on FU-9)

The lib is "done" when it can author all five cleanly and a user never needs to
open the Shortcuts editor except to enter a PAT. That's the publishing bar too —
GPL-3.0 with a README that says "Claude Code can build these for you" becomes
meaningful the moment distribution doesn't require manual post-import surgery.

### Three target dependency graph

```
Target A: Voice Note → Vault (re-author)       Priority: 1
  Depends on: RecordAudio, TranscribeAudio (both exist)
              DeviceDetails magic var (needs verification)
              Optionally: ChooseFromMenu for "continue/done" (exists)
              Optionally: Setup section for repo/path config (FU-9, nice-to-have)
  Stress test: audio passthrough + two GitHub PUTs in one shortcut,
               ChooseFromMenu as a UX decision gate

Target B: Quick Task → Daily Note              Priority: 2
  Depends on: macOS Spotlight input surface (WFWorkflowTypes: "WFWorkflowTypeReceivesOnScreenContent")
              AskForInput or Spotlight input as trigger
              GitHub append-or-create action (FU-8 pattern), OR:
              Obsidian URI scheme via DownloadURL (already modelled)
              Optionally: addnewreminder (needs schema implementation)
  Stress test: macOS Spotlight surface, append-not-overwrite pattern,
               first shortcut that writes TO the vault rather than FROM it

Target C: Share-Sheet → Vault Inbox            Priority: 3
  Depends on: share-sheet trigger surface (ActionExtension)
              ShortcutInput magic var (exists)
              Optionally: WFWorkflowInputContentItemClasses for URL + text + image
              Optionally: GetContentsOfURL for webpage title extraction
  Stress test: share-sheet surface declaration, typed input handling,
               first shortcut that handles input it didn't itself create
```

The dependency order follows from "what forces a primitive we don't have yet":

- Target A forces the lib to handle two sequential GitHub PUTs with the
  audio binary as a second payload — tests that `DownloadURL` + `Base64Encode`
  composes correctly for binary data, not just text.
- Target B forces the lib to handle macOS surfaces and the append-to-file
  pattern. It's the first shortcut that writes *into* the vault rather than
  pulling from it. The GitHub API PUT is reused but the trigger and workflow
  shape are new.
- Target C forces share-sheet surface declaration and typed input handling —
  the first shortcut where the data source is external (another app) rather
  than something the user actively produces.

Together these three validate: audio pipeline, macOS surface authoring,
share-sheet triggering, and the append/update pattern. The architecture
that survives all three is a V1 worth publishing.

---

## 3. Top 3 concrete proposals

### Target A — Voice Note → Vault (re-author via lib)

**What it does.** Record audio → transcribe → generate frontmatter → commit
markdown + raw audio as two sequential GitHub PUTs → notification. Optionally:
ChooseFromMenu "Continue / Done" to allow appending to the same session note
before committing.

**Why this first.** The user already uses `voice_note_to_github.shortcut` daily.
The shortcut was built by hand; the lib should be able to re-author it cleanly
and improve it per the user's stated wants (confirmation prompt, optional
metadata). The hand-built shortcut is both a spec and a regression target: decode
it, compare buzz output against what the lib emits, iterate until they match in
intent if not in UUID. The user also noted a concrete desired improvement in a
voice jot: "once it's finished recording, option to continue or confirmation that
I am done, and then option to be prompted for more metadata." That's two small UX
features (ChooseFromMenu decision gate, optional metadata Ask) that are directly
exercisable from the current schema.

**What it stresses.** Two sequential GitHub PUTs in a single shortcut — the first
for the markdown, the second for the raw `.m4a`. The audio PUT is a binary payload
(base64-encoded `.m4a`), not text, which tests that `DownloadURL` + `Base64Encode`
handles binary inputs correctly. The ChooseFromMenu gate tests that the lib can
express a real UX decision (continue recording vs commit) cleanly.

**Prerequisites.** RecordAudio and TranscribeAudio are already modelled. DeviceDetails
magic variable needs verification against the decoded private sample (it appears in
the buzz output as `@DeviceDetails` — confirm the wire key). ChooseFromMenu is in
the schema. The only open question is whether `Base64Encode` correctly handles audio
input vs text input (check the `mode` parameter — encoding vs decoding).

**Scope.** Small-to-medium. Most primitives exist. The main work is the Python
builder script and verifying the DeviceDetails wire format.

**What it unlocks.** (a) Proves the lib can handle a two-payload commit workflow
correctly. (b) Re-author means the user gets the improved UX version (continue/done
gate) without touching the Shortcuts editor. (c) Establishes the pattern for
"improve an existing shortcut by re-authoring it via the lib" — the most common
real-world use case. (d) Grounds further audio-pipeline work in a real validated
output.

---

### Target B — Quick Task → Daily Note (macOS Spotlight surface)

**What it does.** From macOS Spotlight (or as a manual shortcut): user types or
dictates a task string → shortcut appends it as a task line (`- [ ] ...`) to
today's daily note in the vault, which the lib targets via the GitHub API append
path (GET sha + PUT with updated content). Optional: simultaneously add as a
Reminder.

**Why this second.** The user asked for this explicitly in a voice jot from
2026-05-07: "free [bar], Spotlight or whatever it is with command-space to write
out a task, and then have that added ideally directly to my daily tasks as a task."
That's not a hypothetical; it's a feature request the user dictated. The daily note
format is well-established (`daily/YYYY-MM-DD-Day.md`, `## Tasks` section), the
vault's git-backed GitHub repo is already wired, and the pattern of "append to
today's file" is directly expressible with `DownloadURL` GET + base64-decode +
append + re-encode + PUT.

**What it stresses.** Three new stresses for the design: (1) macOS Spotlight surface
— `WFWorkflowTypes` needs to declare `"WFWorkflowTypeReceivesOnScreenContent"`,
which is the iOS 26 Spotlight-input surface flag, and this hasn't been authored via
the lib yet. (2) Read-then-write pattern — GET the current file, decode from base64,
append, re-encode, PUT back with the correct `sha`. This is a more complex GitHub
API interaction than the append-only vault-note path. (3) Date-based filename
construction for "today's note" — `FormatDate` with the `YYYY-MM-DD-Day` pattern
(the vault names daily notes with day-of-week, which is a `EEEE` format token).

**Prerequisites.** `AskForInput` and `FormatDate` exist. `DownloadURL` with JSON
body exists and handles both GET and PUT. The `base64encode` decode-mode is in the
schema. The only unmodelled action is `addnewreminder`, but it's optional — the
shortcut is useful without it. Verify the `WFWorkflowTypes` key for Spotlight
input against the iOS 26 docs (the note `iOS_26_Highlights.md` confirms it exists;
the exact key needs a decode sample or Apple docs verification).

**Scope.** Medium. The read-then-modify-then-write GitHub pattern is the most
complex data flow we've authored yet. It's not large in code terms — maybe 60 lines
of builder Python — but it requires the lib to correctly sequence a GET result into
a base64-decode action (`Base64Encode` with `mode="Decode"`), which hasn't been
exercised.

**What it unlocks.** (a) First shortcut that writes *into* the vault rather than
from it. (b) Proves macOS surfaces work. (c) The GET-then-PUT pattern (FU-8) is
solved once here and reusable everywhere. (d) If `addnewreminder` is also
implemented, opens a whole class of Reminders-based productivity shortcuts (the
`add_expiry_reminder` and `set_weekend_chores` samples both use it).

**The Setup section question.** This is the cleanest target for FU-9
(`WFWorkflowImportQuestions`). The shortcut has exactly two configuration values:
the GitHub PAT and the vault repo name. A Setup section would let the user import
the shortcut, fill in those two fields once, and run. The improvement in
out-of-box experience is high, and this target is simple enough that implementing
FU-9 here doesn't compound with other complexity.

---

### Target C — Share-Sheet → Vault Inbox (share-sheet surface)

**What it does.** From any app's share sheet (Safari, Notes, Messages, Readwise,
etc.): receive a URL, selected text, or image → format as a vault note with
frontmatter (`source`, `url`, `date`, `tags: [note/jot, inbox]`) → commit to
`jots/inbox/` in the vault GitHub repo → notification.

**Why this third.** The user mentioned "highlight text, right click, add to jot" as
a desired shortcut. Share-sheet is the canonical iOS/macOS mechanism for that
pattern. The distinction from Targets A and B is the trigger: neither the user nor
a timer initiates this — another app hands content to the shortcut. This is the
"inbound capture" shape, which is categorically different from "user creates content"
(voice recording) or "user types something" (Spotlight task). Validating this shape
completes the trigger-surface matrix.

**What it stresses.** (1) Share-sheet surface declaration via `WFWorkflowTypes`:
`"ActionExtension"`. (2) `ShortcutInput` magic variable as the content source —
the shortcut doesn't know in advance whether it'll receive a URL, text, or image;
it needs to handle the ambiguity. The `WFWorkflowInputContentItemClasses` metadata
(C4) is what gates which apps show your shortcut in their share sheet. Authoring
this correctly is the first time C4's `accepted_input` parameter is exercised end-
to-end. (3) Conditional branch on input type — `If` operating on `ShortcutInput`'s
type to handle URL vs text differently. This is a new use of `If` (condition on
content type) that hasn't been exercised.

**Prerequisites.** `ShortcutInput`, `DownloadURL`, `FormatDate`, `ShowNotification`
all exist. The C4 `accepted_input` API needs to be verified — the roadmap marks it
as partial. Implement the minimum needed: expose `WFWorkflowInputContentItemClasses`
as a `Shortcut(accepted_input=[...])` parameter and emit it correctly. The
`GetContentsOfURL` action (for webpage title extraction from a shared URL) is in
the decoded samples but not yet schema-modelled; it can be deferred — the shortcut
works without extracting the page title.

**Scope.** Medium. The action chain is simple (receive → format → PUT). The
complexity is surface metadata (C4) and input-type handling.

**What it unlocks.** (a) The share-sheet is how iOS users interact with every other
app — this surface is the bridge from the lib to the whole iOS/macOS ecosystem.
(b) The `accepted_input` C4 work unlocks proper typing of all future share-sheet
shortcuts. (c) The conditional-on-content-type pattern is reusable for any
shortcut that handles mixed input.

---

## Cross-cutting observations

### On the Setup section (FU-9)

FU-9 should be implemented alongside Target B, not deferred to V2. The Setup
section (`WFWorkflowImportQuestions`) is a first-class Apple UX primitive — it
produces the import dialog where you enter a repo name and PAT once, and Apple
stores it in the shortcut's configuration. Every real shortcut the lib produces
needs credentials of some kind; without Setup section support, every import
requires Shortcuts.app surgery. This is the friction point that makes sharing
shortcuts painful. It's also architecturally straightforward: it's a top-level
workflow key that carries a list of question dicts. The work belongs in C4 and
isn't large.

### On iCloud-share and RunWorkflow revival

The research finding is that iCloud-shared shortcuts _do_ preserve UUIDs on share
(unlike locally-signed imports, which get new UUIDs assigned at import). If this is
validated, it would enable genuine multi-shortcut composition for distributed
libraries. This is worth a one-time test: share a shortcut from iPhone, import on
the same or another device, check whether the `workflow_identifier` in the
installed shortcut matches the original. If it does, the composition story changes
significantly. The investigation cost is ~10 minutes; the upside is high.

The B7 task (deterministic `workflow_identifier` from name) becomes load-bearing if
iCloud-share preserves UUIDs — two shortcuts with the same name, built by different
`make-shortcut` runs, would get the same UUID and could link to each other without
manual re-wiring. This is worth fixing now regardless of the iCloud finding, since
the deterministic-UUID guarantee is just correct behaviour.

### On Apple Intelligence integration

`UseModel` is already modelled and proven in `vault_note_to_git`. The next
interesting AI integration isn't more `UseModel` — it's the Writing Tools actions.
`SummarizeText` is the obvious add to the voice note pipeline: record → transcribe
→ summarise → commit both transcript and summary. This is a small addition to Target
A that requires only `SummarizeText` (already in the schema). It makes the committed
note much more useful: the raw transcript plus a one-paragraph summary in the
frontmatter.

The `WFLLMSystemPrompt` and `WFLLMModelExtension` fields (FU-6 — ChatGPT routing)
are worth deferring until there's a concrete target that needs them. The current
`UseModel` with Apple Intelligence on-device is sufficient for all three proposed
targets and avoids introducing an external dependency.

### On "kitchen sink" regression target

There's a clear gap: no single shortcut exercises the full schema breadth as a
regression artefact. The daily standup sample (`samples/daily_standup.shortcut`)
is the closest candidate — it uses `ask`, `text.split`, `text.combine`,
`for each`, `if`, calendar events, and formatted dates. Re-authoring it via the
lib (analogous to `dictate_to_clipboard.py` vs `dictate_to_clipboard.shortcut`)
would produce a regression target that catches regressions across 10+ action types.
The `text.combine` action is not yet modelled — that's the only blocker. This is a
medium-value, low-cost addition: model `text.combine` (one file, ~30 lines), write
the builder script, add a round-trip test against the decoded sample. Worth doing
as part of the N-batch cleanup, not a standalone target.

### On distribution and GPL-3.0

The lib is licensed GPL-3.0-or-later. Publishing under that licence with the skills
layer as the interface means: if someone finds the lib via GitHub and wants to use
the skills in their own Claude Code setup, they can. The licence is appropriate and
the attribution chain (`NOTICE`, `docs/sources.md`) is clean.

"Publish-ready V1" in this context means: (1) README that shows the three-command
workflow (`git clone`, `uv run python examples/my_shortcut.py`, drag-and-drop), (2)
the five targets from the V1-done definition are all present as examples, (3) Setup
section works so the examples are actually usable out-of-box. The lib doesn't need
packaging on PyPI for personal use — the `uv run` pattern is sufficient.

One caution: the private `voice_note_to_github.shortcut` has a live GitHub PAT
baked in (visible in the buzz decode output). FU-4 mentions this is gitignored
locally. Rotation is overdue.

---

## Summary priority stack

| Priority | Target | Stress | Effort |
|---|---|---|---|
| 1 | Voice Note → Vault re-author | Audio binary PUT, ChooseFromMenu UX gate | Small |
| 2 | Quick Task → Daily Note (Spotlight) | GET-then-PUT, macOS surface, FU-9 | Medium |
| 3 | Share-Sheet → Vault Inbox | Share-sheet surface, C4 accepted_input | Medium |
| Side | Re-author daily_standup | text.combine, full schema breadth regression | Small |
| Side | B7 deterministic UUID | RunWorkflow stability, iCloud-share prep | Small |
| Deferred | FU-6 ChatGPT routing | No concrete target needs it yet | — |
