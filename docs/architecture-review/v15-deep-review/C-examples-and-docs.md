# V1.5 Section C — Deep Review: Examples + Skills + Documentation

**Scope:** Cross-cutting evaluation of the LLM-author surface and the user-facing surface across `main` (V1 closeout) + the two V1.5 doc/example branches.

**Reviewed:**
- Branch: `v15/note-to-github-modernize` @ `0ec729a`
- Branch: `v15/readme-release-notes` @ `1f8ccd9`
- `main`: examples (5 V1-pattern + 3 legacy), `skills/{make,edit,decode}-shortcut/SKILL.md`, `docs/release-notes/v1.0.md`, `docs/handoff.md`, `docs/roadmap.md`, `docs/architecture-review/synthesis.md`

**Big picture:** The V1.5 doc/example branches are individually correct but together expose a more interesting story — the LLM-author surface is **not yet self-consistent**. The four V1 examples use a hybrid pattern (`s.set("X", value)` with the return value discarded; downstream code re-fetches via `NamedVar("X")` strings); the freshly-modernized `note_to_github` uses the typed-handle pattern as designed (`x = s.set("X", value)`; downstream code references `x`). Both are legal; they are not stylistically aligned. Today's LLM, reading any one of the four V1 examples as canonical, will write the *less typed* form; reading `note_to_github` it will write the *more typed* form. The README + release-notes are calibrated reasonably for v1.0 but harbour two factual errors and one safety regression that nobody flagged in the individual reviews.

---

## 1. LLM-author walkthrough — first-shot, today's `main`

Hypothetical request: *"Make me a shortcut that takes the clipboard, asks Apple Intelligence to summarise it, and copies the summary back to the clipboard."*

Claude Code, having read only `skills/make-shortcut/SKILL.md` and run `scripts/print_actions.py`, walks roughly like this. SKILL.md mandates 8-12 file reads (roadmap, format, registry, three to seven vault notes) before any code. The action surface (164-line registry output) makes selection easy: Claude finds `GetClipboard`, `SummarizeText`, `SetClipboard`, picks them on the first attempt thanks to the `Literal` types and clean docstrings. Apple Intelligence integration is excellent — `Literal["Apple Intelligence", "Private Cloud Compute", ...]` for `UseModel.model` is exactly the discoverability shape an LLM needs.

For composition, SKILL.md says "see `examples/vault_note_to_git.py` for the canonical example." Claude opens it and reads `_add_polish`:

```python
note = s.add(GetClipboard())
s.add(SetVariable(name="Note", input=note))
polished = s.add(UseModel(prompt=Text("Polish:\n\n{n}", substitutions={"n": NamedVar("Note")}), ...))
s.add(SetVariable(name="Polished", input=polished))
```

The pattern Claude infers: variables are stored as bare `SetVariable` actions and re-referenced as `NamedVar("Polished")` strings. Claude does *not* notice that `Shortcut.set()` exists, because `vault_note_to_git.py` doesn't use it. The roadmap mentions `NamedVar[T]` typed handles, but the canonical example shipped in V1 doesn't demonstrate them. Claude writes:

```python
def build():
    s = Shortcut(name="Summarise Clipboard", surfaces=["share"])
    note = s.add(GetClipboard())
    s.add(SetVariable(name="Note", input=note))
    summary = s.add(SummarizeText(text=NamedVar("Note")))
    s.add(SetClipboard(input=summary))
    return s
```

This is **correct and works**. But Claude has not used `s.set()` once. The whole typed-handle apparatus that V1.5's `NamedVar[T]` work introduced is invisible.

If the prompt had required `If` branching, Claude would have searched for a control-flow reference. `examples/control_flow_demo.py` exists and is good — short, with worked patterns for each construct — but it isn't named in `print_actions.py`'s control-flow section or in SKILL.md. R1 LLM-UX Proposal 2B suggested adding `Example: examples/control_flow_demo.py` next to `### If` in the registry output. Not landed. Claude finds the file only by listing `examples/`.

**The improvement vs V1 pre-V1.5 Section C:** SKILL.md no longer shows the deprecated multi-shortcut `RunWorkflow` composition pattern (commit `ec3cb72`). Four V1 examples exist as references. `Literal` types surface in `describe_action`. Apple Intelligence and FU-9 Setup-section paths both have working examples. `make-shortcut` is materially better than it was at the start of V1.

**The regression (or failure to improve):** the canonical example in SKILL.md (`vault_note_to_git.py`) does not use `s.set`'s typed return value. The freshly-modernized `note_to_github.py` demonstrates the typed pattern correctly but isn't mentioned in SKILL.md and isn't in the README's example list. **An LLM following the SKILL.md-pointed canonical example produces less-typed code than an LLM that happens to read `note_to_github.py`.** This is exactly the inconsistency that `Var[T]` was meant to eliminate.

---

## 2. Example consistency audit

Eight files in `examples/`. Five "V1-pattern" intent (the four named in the README plus the modernized `note_to_github.py`); three legacy or auxiliary (`quick_pomodoro.py`, `dictate_to_clipboard.py`, `control_flow_demo.py`). The four V1 examples and the modernized `note_to_github.py` are the surface a stranger sees.

| File | Helper structure | FU-9 Setup | `s.set` return captured? | Downstream var refs | GitHub PUT pattern | Surface declaration |
|---|---|---|---|---|---|---|
| `vault_note_to_git.py` | `_add_config / _add_polish / _add_push` | Yes (token, repo) | **No** — return discarded | `NamedVar("Token")` strings | Inline (no helper) | `["share", "quick-action"]` |
| `voice_note_to_git.py` | `_add_config / _add_record_and_transcribe / _add_metadata_gate / _add_push` | Yes (token, repo) | **No** — return discarded | `NamedVar("Token")` strings | Inline twice (md + audio) | `["quick-action"]` |
| `spotlight_quick_task.py` | `_add_config / _add_input / _add_datestamp / _add_content / _add_push` | Yes (token, repo) | **No** — return discarded | `NamedVar("Token")` strings | Inline | `[_SPOTLIGHT_SURFACE]` (custom string) |
| `share_to_inbox.py` | `_add_config / _add_capture / _add_stamp / _add_branch / _add_push` | Yes (token, repo) | **No** — return discarded | `NamedVar("Token")` strings | Inline | `["share", "quick-action"]` + `accepted_input=_ACCEPTED_INPUT` |
| `note_to_github.py` (V1.5) | **None** — flat `build()` | Yes (token, repo) | **Yes** — `token`, `repo`, `stamp`, `base`, `content_b64` | Typed handles (`token`, `repo`) | Inline | `["share", "quick-action"]` |
| `quick_pomodoro.py` | None — flat `build()` | No (pre-FU-9) | N/A — uses `s.add` returns directly | Action references (no SetVariable) | N/A | `["watch", "widget"]` |
| `dictate_to_clipboard.py` | None — flat | No | N/A | N/A | N/A | `["watch", "widget"]` |
| `control_flow_demo.py` | None — four `build_*()` | No | N/A | Action references | N/A | `[]` |

**Five problems.**

**A. The `s.set`-with-discarded-return pattern is the worst of both worlds.** The four V1 examples write `s.set("Token", token_text)` (no `=` capture), then later write `NamedVar("Token")`. This:
1. Pays the syntactic cost of `s.set` (over `s.add(SetVariable(...))`) without taking the typing benefit.
2. Forces the reader to mentally bind `"Token"` (string) to the typed `Action` variable visible above.
3. Means a typo in `NamedVar("Toekn")` is **not** caught by the type system — defeating the whole point of `s.set` returning `NamedVar[T]`.
4. Reads as if `s.set` is a side-effecting helper, not the recommended replacement for `SetVariable`.

The modernized `note_to_github.py` proves this can be done better: `token = s.set("Token", token_text)`, then `substitutions={"tok": token}`. Same line count. Type-safe. No string keys.

**B. `note_to_github.py` is internally inconsistent.** It uses typed handles for Token/Repo/Stamp/Base/ContentB64 — but for Note it falls back to `s.add(SetVariable(name="Note", input=note))` and references `NamedVar("Note")` once. The R1 review noted this; it remains. Either convert (`note_var = s.set("Note", note); ... Base64Encode(input=note_var)`) or document the omission in the docstring as deliberate (e.g. "Note is intentionally not captured because it's used only once").

**C. No common GitHub-PUT helper.** The same 30-odd-line block (URL build → auth header → DownloadURL with PUT/headers/body/JSON) appears verbatim in `vault_note_to_git`, `voice_note_to_git` (twice — md + audio), `spotlight_quick_task`, `share_to_inbox`, and `note_to_github`. Five examples × ~30 lines = ~150 lines of literal duplication. A `_github_files_put(s, *, path_template, base, content_b64, repo, token, message_template, headers_extra=None)` helper in a shared module (`examples/_helpers.py` or a private module under `shortcut_lib`) would collapse this. **Not blocking for V1.5 Section C** — examples are deliberately self-contained for didactic value — but worth filing as a V1.5 follow-up.

**D. Helper-function naming is consistent across the four V1 examples** (`_add_<phase>(s)` always; void-returning; mutating `s` via `s.add`). The pattern is *de facto* established. The modernized `note_to_github.py` doesn't follow it because the file is short enough (~110 lines of code) that helpers would be over-structuring. That's a defensible call. But there is no documented rule for "when to use helpers"; the next example author (LLM or human) has no signal beyond file-length intuition. Worth one paragraph in `skills/make-shortcut/SKILL.md` Step 3: "If the workflow has more than 3 logical phases, decompose into `_add_<phase>` helpers; otherwise inline."

**E. `note_to_github.py` is not in the README's example list.** It's the most pedagogically useful single example of the typed-handle pattern; the README mentions only the four `_add_*`-style examples. A reader navigating from README → `examples/` finds 8 files and 4 mentioned. The 4 mentioned use the pattern that's *less* aligned with the V1 design intent. **This is a pure documentation gap with a one-line README fix:** mention `note_to_github.py` as a sixth example with "compact, single-function form" framing.

---

## 3. README + release-notes assessment

### 3.1 What's right

- Status callout at line 9 (`**Status: V1 — used daily; v1.0 not yet tagged.**`) does the work it needs to: any reader skimming the page sees the calibration immediately. Good placement.
- Status table (8 rows) cross-checks accurately against `docs/roadmap.md`'s state table modulo the `336 tests` issue noted below.
- Quickstart code is **runnable end-to-end**. Verified: `from shortcut_lib.builder import Shortcut`, `s.add(GetClipboard())`, `s.add(ShowNotification(... body=clip.output()))`, `s.save_signed()` (no-arg default = `~/Desktop/<name>.shortcut`) all resolve and produce a valid signed shortcut. The `clip.output()` chain is correctly typed: `Action.output() -> Output`. **A first-time user can copy-paste this and have a working shortcut on their Desktop in 30 seconds.**
- "On-device validation pending" wording for three of four examples is honest. The validated-targets table differentiates clearly.
- Release-notes structure supports v1.1, v1.2 etc by adding sibling files; this is the right call vs a single CHANGELOG.md (which loses readability past 5-6 releases) or git tag annotations alone (which aren't browseable on GitHub without clicking each tag). `docs/release-notes/v1.0.md` as the home is correct.

### 3.2 What's wrong (factual)

**Issue 1 — `336 tests` is overstated for the public surface.** The README and release notes both claim "336 tests including a deliberate sweep over 24 leaf actions + 4 control-flow constructs confirming the emitted dicts match Apple GUI emission byte-for-byte." On a fresh checkout (samples/decoded/ is gitignored), the sweep skips entirely — `28 skipped` in `test_wire_format_equivalence.py` because the decoded `.xml` samples don't exist locally. On the user's `main` with samples present: 336 passed total. On the v15/readme-release-notes branch worktree: **311 passed, 28 skipped**. The release notes' "Wire-format equivalence sweep" highlight makes a stronger claim than what a stranger cloning the repo will actually see. Two fixes possible:
   - (a) Reword the README/release-notes claim to "336 tests when run with the full sample corpus; 311 + 28 sample-gated equivalence tests on a fresh clone" — accurate but ugly.
   - (b) Stop gitignoring `samples/decoded/` (they're public Apple gallery shortcuts; the only sensitive one is `samples/private/voice_note_to_github.shortcut`, which is separately gitignored and contains the rotated PAT). This would let strangers see the sweep run. **This is the right move.** File as a V1.5 follow-up: commit the decoded XMLs from public samples into the repo so equivalence tests aren't sample-gated for fresh clones.

**Issue 2 — "placeholder `Text` actions" wording is misleading.** README line 61: "All use the Setup-section pattern (FU-9): token and repo are placeholder `Text` actions that Shortcuts prompts the user to fill in at import time — never bake a real PAT into a signed file." Technically true: `ask_text_on_import` *does* internally add a `GetText` action (verified at `src/shortcut_lib/builder.py:279` — `get_text = self.add(GetText(text=default))`). But the user-facing claim sounds like the prompt mechanism is the `Text` actions themselves, when in fact the prompt mechanism is `WFWorkflowImportQuestions` (a separate top-level workflow key). A reader unfamiliar with the wire format will think "ah, there's a Text action, the user edits it" — which was the pre-FU-9 pattern. Better wording: "All use the Setup-section pattern (FU-9): token and repo are emitted as `WFWorkflowImportQuestions` entries — Shortcuts shows them as a form at import time, with the answers wired into hidden `Text` action slots."

**Issue 3 — `.gitignore` regression on the readme-release-notes branch.** The branch's commit `27a6730` deletes three lines from `.gitignore`:

```
-
-# Claude Code working dir (worktrees, transcripts, etc.)
-.claude/
```

This was added to `main` in commit `589e500` ("gitignore .claude/ (worktrees + transcripts)") for a reason: the user's worktree pattern puts agent working directories under `.claude/worktrees/` and `.claude/reviews/`. Deleting the rule means a future `git add -A` could accidentally stage those directories. **The individual review of this branch did not flag the deletion at all.** The commit message "docs: V1 README refresh + v1.0 release notes draft" doesn't mention the gitignore change. This looks like an accidental revert during branch creation (possibly the worktree was based on a pre-`589e500` commit).

**Severity:** Should-fix before merge. Restore the three lines.

### 3.3 What's missing

- **Quickstart doesn't mention `print_actions.py`.** A first-time programmer who runs the quickstart and wants to author something more interesting has no signpost to the registry. Add one line under quickstart: "For the full action surface, run `uv run python scripts/print_actions.py`."
- **No "what to read next" path for a new contributor.** README lists `docs/format.md`, `docs/sources.md`, `docs/architecture-review/synthesis.md`, `docs/release-notes/v1.0.md`, `NOTICE`. But there's no `CONTRIBUTING.md` or a sentence in README pointing a would-be contributor at `docs/handoff.md` (which is the actual entry point for a new developer agent). For the v1.0 public flip this is a real gap; flag as V1.5 follow-up.
- **No mention of macOS-only constraint in the install-block sub-text.** The install block's footer says "Requires macOS (uses the system `aea`, `aa`, and `shortcuts` binaries)." Good. But the quickstart that follows uses `s.save_signed()` without restating the dependency on `shortcuts sign`. A Windows reader might run quickstart, get a confusing CLI error. Minor; one-sentence callout fixes it.

### 3.4 Tone

The README and release-notes both walk the line correctly between "we shipped" and "still cooking." The "v1.0 not yet tagged" framing is honest and gives the user space to rotate the FU-4 PAT and run the on-device validation for the three remaining examples before flipping public. The release-notes "Status: V1 complete. v1.0 tag and repo-public flip are the user's call." sentence is precisely the right calibration. **This is well-done.** No notes on tone.

### 3.5 Release-notes structure for future versions

Current structure:
- Highlights (8 bullets)
- Validated targets (table)
- Architecture decisions worth knowing (3 prose sections)
- Known limitations (5 prose sections)
- What's deferred to V1.5 (6 bullets)
- Acknowledgements

This is an appropriate template for a foundation release. v1.1 will likely have fewer architecture decisions (all the big ones are settled) and more "Highlights / Bug fixes / Migration notes." Suggest a one-line stub at the top: `_See docs/release-notes/v1.0.md for the foundation release._` — gives every subsequent release a place to defer to without re-stating settled architecture. Worth setting up at the next minor.

---

## 4. Skill files audit

| Skill | State | Findings |
|---|---|---|
| `make-shortcut/SKILL.md` | Refreshed during V1 closeout (`ec3cb72`) | Composition section is correct. Pre-reading list is comprehensive but heavy (8-12 file reads). No mention of `s.set()` typed handles or `note_to_github.py` as the typed-handle reference. Composition sketch (lines 131-166) reproduces the V1-example pattern with `NamedVar("Polished")` strings — same anti-pattern as the V1 examples. |
| `edit-shortcut/SKILL.md` | Untouched in V1.5 | Strategy A (direct dict edit) is fine. Strategy B says "write the desired result fresh using `Shortcut(...)`" — but doesn't mention `Shortcut.from_file(path)` which the underlying lib *does* support and would be the natural starting point. Doesn't mention `Shortcut.set` typed handles or factory methods (`AskForInput.text(...)`, etc.). |
| `decode-shortcut/SKILL.md` | Untouched in V1.5 | Read-only skill; no V1.5-relevant API surface to document. The `--format buzz` workflow described matches today's CLI behaviour. Hardcoded constraint "Watch for secrets... mention it explicitly and recommend rotation" is great advice. **No changes needed.** |

**Specific finds in `make-shortcut/SKILL.md` to fix (V1.5 follow-up, not blocking):**

1. **Lines 131-166 composition sketch** uses the same `s.add(SetVariable(...)) + NamedVar("Polished")` pattern that the four V1 examples ship. To stop replicating the V1 anti-pattern in fresh authoring sessions, this sketch should either:
   - (a) Use the typed-handle form: `polished = s.set("Polished", s.add(UseModel(...)))` and reference `polished` directly downstream.
   - (b) Use the V1 form *and* note explicitly that "the four V1 examples ship this form for historical reasons; the typed-handle equivalent is `polished = s.set('Polished', ...)` and is preferred for new code."

2. **No mention of `ask_text_on_import` / `ask_on_import`.** FU-9 is the dominant Setup-section authoring path; SKILL.md doesn't show it. A subsection between current Step 3 and Step 4 would do: "If the shortcut needs credentials (PAT, repo, API key), use `s.ask_text_on_import(question=..., default=...)` — never bake real credentials into a signed file."

3. **No mention of `factory methods`** (e.g., `AskForInput.text(...)`, `AskForInput.number(...)`). These are the V1 dependent-field UX win; the SKILL.md sketch shows raw `AskForInput(prompt=...)` which is fine but misses the discoverability point.

4. **`scripts/print_actions.py` is referenced** but the LLM has to *run* it to get the surface. Reasonable, but the output is 164 lines. For a smaller token cost the LLM could call `from shortcut_lib.schema import describe_action; describe_action("AskForInput")` for a single action. Not in SKILL.md; would be a useful cheat-sheet entry.

**`edit-shortcut/SKILL.md` items (V1.5 follow-up):**

5. **Strategy B mentions "write the desired result fresh"** but doesn't reference `Shortcut.from_file()` which would be the natural way to start. The current Strategy A example uses `decode_file(...)` and `sign_to_file(...)` — that's a lower-level path than what `Shortcut.from_file` offers. Update.

6. **No mention of `_extra` field** (the dict added in B5 to preserve un-modelled top-level keys on lift). When editing a shortcut that uses `WFWorkflowImportQuestions` and re-emitting, the editor needs to know the lift round-trip handles this correctly.

**`decode-shortcut/SKILL.md`** is fine. No edits needed.

---

## 5. Doc-sweep checklist for post-V1.5-merge

Once the 16 V1.5 batch branches merge to main, several docs need a sweep. Items here that already accommodate V1.5 are flagged ✅; items that need updating are flagged ⏳.

| Doc | State | Required updates |
|---|---|---|
| `README.md` | ⏳ | Update "24 leaf actions" count post-V1.5 (10+ new actions land). Update unmodelled-identifier count. Re-state 336-test number. Mention `note_to_github.py` in example list. |
| `docs/release-notes/v1.0.md` | ⏳ | Lock as the V1 record once tagged; add `## Patch notes` if v1.0.x ships. |
| `docs/release-notes/v1.1.md` (new) | ⏳ | Author once V1.5 merges. Highlights = 10+ new actions, FU-10 DownloadURL factories, FU-12 validation engine, FU-13 xfail resolution. |
| `docs/roadmap.md` | ⏳ | Move V1.5 items to Done in the state table. Add V2 deferred items. |
| `docs/handoff.md` | ⏳ | Significant rewrite. Most "Open tasks" closed in V1.5; archive them and add V2 tasks. |
| `skills/make-shortcut/SKILL.md` | ⏳ | Address §4 findings 1-4. Update composition sketch to typed-handle form. |
| `skills/edit-shortcut/SKILL.md` | ⏳ | Address §4 findings 5-6 (`Shortcut.from_file`, `_extra`). |
| `skills/decode-shortcut/SKILL.md` | ✅ | No updates required. |
| `examples/{vault,voice,spotlight,share}*.py` | ⏳ | Migrate to typed-handle pattern. Single PR, one commit per file. |
| `examples/note_to_github.py` | ✅ now; ⏳ post-FU-10 | Already typed-handle. After FU-10, migrate to `DownloadURL.json(...)` factory. |
| `examples/quick_pomodoro.py` | ⏳ | Pre-FU-9; either add Setup-section or label as "legacy / Self-recursion demo". |
| `examples/control_flow_demo.py` | ✅ | Correct. |
| `examples/VALIDATION_vault_note_to_git.md` | ⏳ | Add one-line "Validated successfully on 2026-05-09" header. |
| `docs/architecture-review/{synthesis,round1-*,round2-*,v15-reviews}.md` | ✅ | Frozen historical record. Don't update. |
| `docs/format.md` | ⏳ | Audit for FU-10/FU-12 changes to documented wire-format invariants. |
| `data/observed_envelope_types.json` | ⏳ | Re-run scanner after V1.5 sample additions; commit fresh oracle. |
| `NOTICE`, `LICENSE`, `docs/sources.md`, `data/jellycore_facts.json` | ✅ | Stable. |

**Sweeps needed in priority order:** (1) restore `.claude/` to `.gitignore` (trivial); (2) re-author `docs/handoff.md` as a V2 handoff (current doc references "216 tests" and mostly-closed open tasks); (3) update README counts post-V1.5 merge; (4) example modernization sweep — convert the four V1 `_add_*` examples to typed-handle pattern; (5) `make-shortcut/SKILL.md` composition sketch update.

---

## 6. Public-readiness assessment

If the user flips public on v1.0 today, a stranger's first 10 minutes:

**Minutes 1-4 — README + quickstart.** Status callout sets calibration; the "canonical user is Claude Code" framing is distinctive. Quickstart **works** (verified copy-paste against the readme branch — produces a signed `.shortcut` that imports cleanly). This is the moment that decides whether the stranger continues. **Strong first impression.**

**Minutes 5-7 — Examples.** README lists four. Stranger opens `vault_note_to_git.py`, reads the helper-decomposed structure. Slight friction reading `_add_polish`: `s.add(SetVariable(name="Note", input=note))` followed by `NamedVar("Note")`. Reader thinks "why isn't this `note_var = s.set('Note', note)` with `note_var` referenced downstream?" — looks at the registry, finds `s.set` exists. **The answer (V1 examples ship the discarded-return pattern; V1.5's `note_to_github.py` is the typed-handle form) is not visible from any doc the stranger will find.**

**Minutes 8-10 — Registry + decision.** `print_actions.py` output is good for selection but the stranger doesn't understand `ParamValue` (no inline definition). Tests pass on a fresh clone but show **311 passed, 28 skipped** — the equivalence sweep is gated on `samples/decoded/` (gitignored). The advertised "byte-for-byte" wire-format claim is invisible. Release-notes' "Architecture decisions" section (three solid paragraphs) salvages trust.

**Where it would shine more:**
- **If `samples/decoded/` were committed**, fresh-clone `pytest` would show the full 336.
- **If the README mentioned `note_to_github.py`** as the typed-handle exemplar.
- **If `print_actions.py` referenced `control_flow_demo.py`** (R1 LLM-UX P2B; not landed).

**Where it would break down right now:**
- The `.gitignore` `.claude/` regression. Worktree paths could be accidentally committed by a stranger using Claude Code on the repo.
- An LLM following SKILL.md produces less-typed code than V1.5 intended.

**Bottom line:** Public flip would land cleanly with **two pre-flip fixes** (gitignore restore + README "placeholder Text actions" wording). The deeper inconsistencies (V1 examples not using typed handles, SKILL.md replicating the V1 anti-pattern, `samples/decoded/` not committed) are V1.5 follow-ups, not blockers.

---

## 7. Followups consolidated

Atomic, file-this-don't-fix-now, ordered by user-value:

### Pre-merge (block v1.0 tag)

- **F1.** Restore three deleted lines to `.gitignore` on `v15/readme-release-notes`:
  ```
  # Claude Code working dir (worktrees, transcripts, etc.)
  .claude/
  ```
- **F2.** Reword README line 61 to reflect the FU-9 wire-format pattern:
  > "All use the Setup-section pattern (FU-9): token and repo are emitted as `WFWorkflowImportQuestions` entries — Shortcuts shows them as a form at import time, with answers wired into hidden `GetText` action slots so the rest of the workflow references them as ordinary variables."
- **F3.** Add `examples/note_to_github.py` as the fifth example in the README's example list, framed as "compact single-function form for shorter pipelines."

### V1.5 polish (post-merge, pre-public)

- **F4.** Migrate the four V1 examples to typed-handle pattern: capture `s.set(...)` returns, drop `NamedVar("X")` strings, eliminate the discarded-return form. Single PR, one commit per file.
- **F5.** Update `skills/make-shortcut/SKILL.md` composition sketch (lines 131-166) to use typed handles. Add a subsection on `ask_text_on_import` for credentials. Add a rule on when to decompose into `_add_<phase>` helpers vs inline.
- **F6.** Update `skills/edit-shortcut/SKILL.md` to mention `Shortcut.from_file()` and the `_extra` round-trip mechanism.
- **F7.** Commit `samples/decoded/*.xml` for the 20 public samples (everything except `samples/private/`). Stop gitignoring `samples/decoded/`. Verify fresh-clone `pytest -q` shows the full 336 passed.
- **F8.** Add a one-line "Validated successfully on 2026-05-09" header to `examples/VALIDATION_vault_note_to_git.md`.

### V1.5 example fixes (low priority)

- **F9.** Resolve the internal inconsistency in `examples/note_to_github.py` (Note variable not typed-handle).
- **F10.** Extract a `_github_files_put` helper shared by the five GitHub-PUT examples (~150 lines of duplication).

### V2 / `docs/handoff.md` re-author

- **F11.** Re-author `docs/handoff.md` as a V2 handoff. Archive closed V1/V1.5 tasks; add new open tasks.
- **F12.** Author `docs/release-notes/v1.1.md` template with a stub linking back to v1.0 for foundation context.

### `print_actions.py` LLM-UX

- **F13.** Add `Example: examples/control_flow_demo.py` to control-flow entries (R1 LLM-UX P2B; not landed in V1).
- **F14.** Add a `Text` constructor signature + worked example to the values section (R1 LLM-UX P2C).

### Strategic note (not an action)

The most interesting V1.5 finding is structural: the four V1 examples canonicalise a *less typed* form than what V1.5's `s.set` / `NamedVar[T]` work introduced. The canonical example shipped in SKILL.md uses the V1 form. The freshly-modernized example uses the V1.5 form. **An LLM following the V1.5 design intent today learns the V1 form because that's what the canonical example shows.** F4 + F5 are the structural fix; the alternative is letting the typed-handle pattern become a footnote and accepting `NamedVar("X")` string-keying as the de-facto pattern. Worth deciding deliberately rather than letting the V1 examples drift into permanence by accident.

---

## Closing note

Both V1.5 Section C branches are individually correct and merge-clean *modulo the three pre-merge fixes (F1, F2, F3)*. The deeper inconsistencies surfaced here are not regressions — they are the natural consequence of writing the four V1 examples *before* V1.5's typed-handle apparatus had its own canonical example. The V1.5 work happened in waves: the typed handles landed in `0a9caab`; the four V1 examples were written in `11a63d8`, `f8194ae`, `aaf7904`; the modernized `note_to_github` came after. None of the V1 examples were retrofitted. Section C's job was to surface the inconsistency; the actual fix (F4) is V1.5's epilogue.

Word count: ~4,000.
