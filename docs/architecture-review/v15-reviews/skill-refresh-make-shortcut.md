# Review: `v15/skill-refresh-make-shortcut` — SKILL.md refresh for V1.5 patterns

**Branch:** `v15/skill-refresh-make-shortcut` (head `571bd66`)
**Reviewer:** Claude Sonnet 4.6 (automated, on behalf of user)
**Date:** 2026-05-09
**Scope:** docs-only — `skills/make-shortcut/SKILL.md` (158 ins, 32 del)

---

## 1. Verdict

Approve with one note. The four areas the agent targeted are all addressed
correctly and the SKILL is materially better for an LLM author than the main
branch version. The credentials path, typed-handle story, and factory methods
are clear and well-placed. One gap: the `_add_config` sketch in the SKILL
deliberately departs from main's `vault_note_to_git.py` (which still uses the
old `SetVariable` + `NamedVar("string")` pattern), but the intended reference
point is the parallel branch `v15/v1-examples-typed-handles`. That branch's
version of `vault_note_to_git.py` does match the SKILL's sketch exactly. The
SKILL claims the example is the canonical reference; it will mislead an LLM
that reads the example off `main`. This is a sequencing concern, not a defect
in this PR's prose — but it warrants a note in the merge message.

---

## 2. Sections added (in document order)

1. **Step 3 — Credentials: use `ask_text_on_import`** — inserted between
   "Choose actions" and "Write Python". Includes a two-call snippet showing
   `ask_text_on_import` → `s.set` → typed handle, plus a prose paragraph
   explaining the import-time flow.

2. **Typed handles — the recommended variable pattern** (new top-level
   section, after Step 6). Before/after code blocks; explains the typo
   failure mode and recommends explicit annotation.

3. **Factory methods on `AskForInput`** (new top-level section, after typed
   handles). Four factory examples; explains when to use the direct
   constructor.

4. **Composition pattern** — rewritten. Now shows `_add_config` returning
   `tuple[NamedVar, NamedVar]`, `_add_polish` returning `NamedVar`,
   `_add_notify` receiving `polished: NamedVar` as a typed arg. Key-points
   bullet list added. Rule-of-thumb (decompose > 3 phases) added.

---

## 3. LLM-author walkthrough — "vault note → polish → push"

Reading the SKILL cold as an LLM about to build a shortcut that reads the
clipboard, polishes via Apple Intelligence, and pushes to GitHub:

**Pre-reading list** — unchanged, appropriate. Covers the right vault notes
for this surface area.

**Step 1 (Clarify)** — no change. Adequate.

**Step 2 (Choose actions)** — no change. The fallback options (A/B/C) are
still there.

**Step 3 (Credentials)** — the new step lands exactly where it should.
Before reading Step 4, the LLM sees `ask_text_on_import` used with the
exact credential question format it will need for a GitHub PAT. The prose
explains what happens at import time. An LLM that reads linearly will not
reach Step 4 (Write Python) with any impulse to hard-code a PAT. This is
the right placement and the right amount of explanation.

**Step 4 (Write Python)** — the inline pattern example now uses
`AskForInput.number(...)` rather than `AskForInput(input_type=...)`.
Consistent with the new factory section. However, the inline snippet imports
`AskForInput` from `shortcut_lib.schema.actions.ask` and `Text` from
`shortcut_lib.schema` — imports not fully covered by the composition sketch
below, which imports from `shortcut_lib.schema.values`. An LLM synthesising
both may wonder about the split import path. Minor; real behaviour is
`uv run python` will catch it.

**Step 5 (Run and verify)** — the new `uv run pytest` step is here. The buzz
sanity-check now includes a note that unexpected empty values signal a
`NamedVar` wiring issue, and points to typed handles as the fix. This is a
useful link from symptom to solution.

**Typed handles section** — the before/after makes the story clear. The
`NameError` vs silent empty-value distinction is the right framing for an
LLM reader. One minor quibble: the "both forms produce identical wire format"
sentence appears before the explicit annotation example. An LLM might
short-circuit here and decide either form is fine. Moving that sentence after
the explicit annotation example would leave the recommendation as the last
thing read.

**Factory methods section** — clear. The `TypeError at call site` explanation
is well-targeted at an LLM that might reach for kwarg flexibility. The note
about the direct constructor for runtime-determined types covers the one
legitimate escape hatch.

**Composition section** — the rule-of-thumb ("more than 3 logical phases")
is a welcome addition; main's version had no threshold guidance. The typed
sketch is internally consistent. The key-points list at the bottom is
genuinely useful — it summarises what an LLM should take away without
forcing a second read of the code.

**Where an LLM would still get stuck:**

- The SKILL references `vault_note_to_git.py` as the canonical example, but
  reading it off `main` shows `SetVariable` + `NamedVar("Note")` in
  `_add_polish` and a void-returning `_add_config`. An LLM that reads the
  example after reading the SKILL will see a conflict and may revert to the
  old pattern. Resolvable by landing `v15/v1-examples-typed-handles` before
  or alongside this branch.

- The SKILL doesn't address what to do when a helper phase needs credentials
  (`token`, `repo`) as well as a value from a prior phase. The composition
  sketch demonstrates `_add_push` not existing in the sketch (it's replaced
  by `_add_notify` for brevity), so the full three-phase passing pattern is
  only implied, not shown. A reader who copies the sketch and then needs to
  thread `token` into `_add_push` has to infer the pattern. A single comment
  like `# _add_push(s, polished, token, repo)` substituted for `_add_notify`
  would close this gap.

---

## 4. Style consistency with `examples/vault_note_to_git.py`

Comparison against the **main** branch version of `vault_note_to_git.py`
and the **`v15/v1-examples-typed-handles`** version:

| Aspect | SKILL sketch | main's example | v1-examples-typed-handles |
|---|---|---|---|
| `_add_config` return type | `tuple[NamedVar, NamedVar]` | `None` | `tuple[NamedVar, NamedVar]` |
| `_add_polish` return type | `NamedVar` | `None` | `NamedVar` |
| Variable storage | `s.set(...)` | `s.add(SetVariable(...))` | `s.set(...)` |
| `NamedVar` references in Text | Python identifier (`note`) | `NamedVar("Note")` string | Python identifier |
| `_add_push` signature | not shown | `(s: Shortcut)` | `(s, polished_var, token, repo)` |

The SKILL sketch matches `v15/v1-examples-typed-handles` perfectly. Against
`main`'s example it is a deliberate advancement, not an inconsistency — but
the SKILL presents the example as current ground truth. The cross-reference
in the Composition section (`See ~/personal/shortcut-lib/examples/vault_note_to_git.py
for the canonical example`) will mislead until the typed-handles branch lands.

---

## 5. Issues

**Issue 1 (moderate): Cross-reference to `vault_note_to_git.py` ahead of its
migration.** The SKILL points to the example as canonical. On `main` the
example still uses the old pattern. Merge order matters: this branch should
either land after `v15/v1-examples-typed-handles`, or the cross-reference
should be phrased as forward-looking ("see the typed-handles form in
`v15/v1-examples-typed-handles`") until that branch merges.

**Issue 2 (minor): "both forms produce identical wire format" sentence
placement.** Currently appears mid-section before the recommendation to
prefer typed handles. An LLM reading quickly may stop at "identical wire
format" and conclude there is no real reason to prefer one form. Recommend
moving that sentence to after the explicit annotation example, so the
section ends on the recommendation rather than on an equivalence statement.

**Issue 3 (minor): Full three-phase typed-argument threading not shown.** The
sketch omits `_add_push` and replaces it with a void-returning `_add_notify`.
`_add_notify` only consumes one typed arg, so the pattern for threading
multiple handles into a downstream phase (`_add_push(s, polished, token, repo)`)
is not demonstrated. The key-points list mentions it but doesn't show it.

**Issue 4 (non-blocking): Import path note.** The inline Step 4 pattern imports
`NamedVar` from `shortcut_lib.schema.values` implicitly (via the composition
sketch import block), while the Step 4 snippet omits `NamedVar` from its
imports. This is technically consistent — the Step 4 snippet doesn't use
`NamedVar` directly — but an LLM might add `NamedVar` usage and then wonder
which import path to use. Not a doc error; just a minor friction point.

---

## 6. Merge recommendation

Merge after `v15/v1-examples-typed-handles` — or add a note to the
cross-reference acknowledging that the example on `main` still uses the older
form. All four areas the agent targeted are correctly implemented. The
preserved sections (RunWorkflow warning, single-Shortcut mandate,
drag-in-fill-run narration, pre-reading list, Clarify, Choose-actions,
Editing, Constraints) are intact and unaltered. `prek run --all-files` passes
clean. No structural or prose regressions.

The SKILL is a net improvement: an LLM following it will write `s.set(...)`
returns, `ask_text_on_import` for secrets, and `.number()` / `.text()`
factories. That is the right outcome.
