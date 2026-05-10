# Review: v15/readme-release-notes

**Branch:** v15/readme-release-notes (head 27a6730)
**Reviewer:** agent-review session, 2026-05-09
**Verdict:** GREEN with two minor corrections required before merge.

---

## 1. Verdict

**GREEN (conditional).** Both docs are substantively accurate, well-structured, and
grounded in what shipped. Two factual errors need fixing; both are small and mechanical.
No aspirational drift, no features claimed that don't exist, no structural problems.

---

## 2. Word count + prek status

| File | Words |
|------|-------|
| README.md (branch) | 560 |
| docs/release-notes/v1.0.md | 1 162 |
| Total diff | ~1 722 new words |

prek: **all 8 hooks pass** (ruff lint, ruff format, uv-lock, ty, whitespace, YAML,
large files).

---

## 3. What landed

- README restructured end-to-end per the brief: tagline + 2-sentence description,
  status callout on line 9, 8-row status table, install, quickstart, four examples,
  CLI block, library decode example, See also, licence.
- `docs/release-notes/v1.0.md` is new: headline, 7 highlights, validated-targets
  table, 3 architecture decisions, 5 known limitations, V1.5 deferred list,
  acknowledgements.
- All linked files exist on both the branch and main:
  `docs/architecture-review/synthesis.md`, `examples/VALIDATION_vault_note_to_git.md`,
  `docs/format.md`, `docs/sources.md`, `NOTICE`.
- Licence section unchanged word-for-word from main.

---

## 4. Accuracy checks

### 4.1 Test count — PASS (with nuance)

README and release notes both cite **336 tests**. Actual counts:

- `336 passed, 2 skipped, 3 xfailed` — 336 is the *passing* count, which is the
  natural reading of "336 tests". Total collected is 341 (includes xfails and skips).
- Roadmap (updated 2026-05-09) also says "336 tests". Consistent.
- Verdict: acceptable. The release notes separately and correctly calls out the 3
  xfails by name (FU-13).

### 4.2 Unmodelled identifier count — FAIL (minor)

Release notes, highlights and known-limitations sections both state:

> "365 unmodelled action identifiers in the corpus"

Ground truth: roadmap says 393 distinct identifiers; registry confirms 24 modelled.
393 − 24 = **369**, not 365. The figure is wrong by 4.

No source in the repo uses 365; the roadmap explicitly says 393 distinct.

**Fix:** change both occurrences of "365" to "369" in `docs/release-notes/v1.0.md`.

### 4.3 Validation date — PASS

README and release notes validated-targets table both say "iPhone iOS 26.4.2 +
Apple Intelligence, 2026-05-09". `examples/VALIDATION_vault_note_to_git.md` says
"Device: iPhone, iOS 26.4.2" and "Bugs surfaced and fixed during validation
(2026-05-08 / 2026-05-09)"; the roadmap E1 entry says "validated end-to-end on
iPhone (iOS 26.4.2 + Apple Intelligence) on 2026-05-09". Date and device match
the authoritative sources.

### 4.4 Status table vs roadmap — PASS

All 8 rows cross-check against `docs/roadmap.md` "Current state (2026-05-09)".
Counts (20+1 samples, 687 actions, 24 leaf+4 control-flow, 336 tests), feature
names (FU-9, envelope oracle, RawAction passthrough), and skill locations all match.

### 4.5 Four examples — PASS

Each description checked against the example file's own docstring and code:

- `vault_note_to_git.py`: "clipboard → Apple Intelligence polish → GitHub Files API
  PUT → notification" — exact match.
- `voice_note_to_git.py`: "record audio → on-device transcription → optional
  metadata via ChooseFromMenu → two GitHub PUTs (markdown + raw .m4a binary)" — matches
  docstring pipeline.
- `spotlight_quick_task.py`: "AskForInput from macOS Spotlight → format timestamp →
  GitHub Files API PUT at daily/\<date\>/task_\<stamp\>.md" — exact match.
- `share_to_inbox.py`: "share-sheet trigger (ActionExtension surface); branches on
  URL vs text; writes a timestamped markdown file to inbox/" — matches docstring.
  The "ActionExtension surface" label is confirmed by the file's surface declaration.

### 4.6 Control-flow count — PASS (framing choice)

README and release notes say "4 control-flow constructs". `list_control_flow()`
returns 5: If, RepeatCount, RepeatEach, ChooseFromMenu, RunWorkflow. The
discrepancy is intentional: the roadmap's own encoder row uses "4 control-flow"
and separately lists "RunWorkflow composition" — RunWorkflow is counted as the
composition primitive, not a control-flow construct. The README and release notes
follow the roadmap's own framing. Consistent.

### 4.7 FU-8 / FU-9 placement — PASS

- FU-9 (Setup-section authoring): correctly in the highlights as a V1 deliverable.
- FU-8 (GitHub create-or-update sidestep): correctly in Known Limitations AND in
  V1.5 deferred. Not presented as shipped.
- No FU-8 leakage into the highlights section.

### 4.8 Factory methods for AskForInput — PASS

Release notes highlights include:

> "Factory methods for AskForInput. AskForInput.number(...) and AskForInput.text(...)"

This is correctly positioned as V1 (synthesis §3.3 chose factory methods over
@overload; roadmap V1 done entry confirms). DownloadURL factory methods (FU-10)
are correctly deferred to V1.5.

### 4.9 Architecture decisions section — PASS

Three decisions in the release notes (lib-as-LLM-callee, composition-in-Python,
FU-9 Setup section, envelope oracle) accurately summarise synthesis §2 consensus
and the decisions log. The composition-pivot description matches roadmap
2026-05-09 entry and `VALIDATION_vault_note_to_git.md` "Lessons" section verbatim.

### 4.10 V1.5 deferred list — PASS (sufficiently accurate)

Six items listed. All traceable to open follow-ups in `docs/handoff.md`:
MCP server publication (synthesis 5.16), FU-10, FU-12, iOS 26 samples, FU-8,
and the @action decorator (synthesis 5.12, depends on B7+E1). The list omits
lower-level open tasks (B5, B7+E1, SF-batches) which are cleanup/debt rather
than user-facing features — appropriate omission for release notes.

### 4.11 Quickstart snippet — PASS

Verified the snippet compiles and builds a valid workflow against the installed
library:

```
Quickstart snippet compiles OK
```

Imports (`shortcut_lib.builder.Shortcut`, `shortcut_lib.schema.actions.get_clipboard.GetClipboard`,
`shortcut_lib.schema.actions.show_notification.ShowNotification`) all resolve.
`s.add()` returns `Action`; `.output()` is on the base class; `save_signed()` with
no args drops to `~/Desktop/<name>.shortcut` as the README describes. The `body=`
parameter on `ShowNotification` accepts `Output` via `ParamValue`. Snippet is
copy-paste runnable.

---

## 5. Readability notes

- **Status callout position**: line 9, immediately after the 2-sentence description,
  before the status table. Exactly where it should be. Hard to miss.
- **Tone**: grounded throughout. No aspirational framing of V1.5 items as if shipped.
  Known limitations section is honest (three xfails named and explained, FU-8
  workaround explicitly flagged as a workaround).
- **Validated targets table**: clear differentiation between "Yes — iPhone …, 2026-05-09"
  and "Build-verified; on-device validation pending" for the three other shortcuts.
  No overclaiming.
- **Architecture decisions section**: appropriately short (three decisions, ~300 words).
  Not a reprint of the synthesis; a useful map for a reader who wants to understand
  why the lib looks the way it does.
- **Acknowledgements**: matches `docs/sources.md` and `NOTICE` in content and licence
  attribution. The three projects (Open-Jellycore GPL-3.0, shortcuts-js MIT,
  iOS-Shortcuts-Reference archived 2022) are correctly cited.
- One minor style point: the "See also" section in the README lists
  `docs/architecture-review/synthesis.md` without a brief description of what it
  contains. Worth one parenthetical ("V1 design rationale from a 7-agent review") —
  but the current entry already has "— V1 design rationale (7-agent review)" so this
  is fine.

---

## 6. Issues

### Issue 1 — REQUIRED: Wrong unmodelled identifier count (release notes)

**File:** `docs/release-notes/v1.0.md`, two locations.

- Highlights section: "passthrough for the 365 unmodelled action identifiers in the corpus"
- Known limitations section: "The corpus contains 393 distinct action identifiers;
  24 are modelled with typed schemas. `RawAction` passthrough handles the rest — any
  unrecognised identifier **round-trips** correctly..."

The arithmetic is stated as "393 … 24" but the prose says "365 unmodelled", which is
wrong (369). Fix by changing both "365" occurrences to "369".

### Issue 2 — MINOR: Test count specificity

README status table row says "336 tests incl. equivalence sweep". This is the passing
count, accurate. The known-limitations section of the release notes separately
identifies 3 xfailed tests. No change required unless the user wants to add
"(+ 3 xfailed, 2 skipped)" to the status table for precision — judgment call, not a
blocker.

### Issue 3 — NOTE: Validation file has no explicit "success" timestamp

`examples/VALIDATION_vault_note_to_git.md` records "Bugs surfaced and fixed during
validation (2026-05-08 / 2026-05-09)" but doesn't have an explicit "validated
successfully on 2026-05-09" statement — the 2026-05-09 date comes from the roadmap
decisions log ("Vault Note To Git validated end-to-end on iPhone … on 2026-05-09").
The README and release notes are correct to use this date; the validation file is just
slightly ambiguous for future readers. Not a blocker; could be a one-line addition to
the validation file. Out of scope for this branch.

---

## 7. Merge recommendation

**Merge after fixing Issue 1.** Change two occurrences of "365" to "369" in
`docs/release-notes/v1.0.md`. Everything else is accurate, readable, and grounded
in what shipped. The quickstart runs, linked files exist, status callout is in the
right place, FU placement is correct, validation date is sourced accurately, and
the licence section is untouched. prek is clean.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `0e3c3e9` (matches _SUMMARY.md record `0e3c3e9`)

**Merge against main:**
- Result: trivial-conflicts-resolved
- Conflict files: `.gitignore`
- Resolution: Branch adds `.claude/` (bare ignore); main has the more precise `.claude/*` + `!.claude/rules/` form (introduced in `589e500` + `c06f6ff`). Took main's version — the branch's intent (hide the worktree dir) is satisfied by main's form, which additionally allows `.claude/rules/` to be tracked.

**Pytest on merged state:** 330 passed, 6 skipped, 3 xfailed (green)

**prek:** green (all 8 hooks pass on branch state)

**Drift / observations:**
- Main's README is still the old pre-branch format — no conflict on that file; the branch's full README rewrite applies cleanly.
- `docs/release-notes/v1.0.md` is a pure addition (not present on main) — merges cleanly.
- `examples/note_to_github.py` confirmed present on main; the README entry added by commit `0e3c3e9` is accurate.
- Issue 1 (365 → 369) verified fixed: both occurrences in `docs/release-notes/v1.0.md` now read "369".
- Test count on merged state (330 passing) differs from branch-only due to test suite growth on main pulling in additional files; suite is fully green.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
