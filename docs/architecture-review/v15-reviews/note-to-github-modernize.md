# Review: v15/note-to-github-modernize

**Branch:** `v15/note-to-github-modernize` (head: 0ec729a)
**File changed:** `examples/note_to_github.py` (41 ins / 37 del, net +4)
**Verdict:** GREEN

---

## Test result

All clean.

- `tests/test_example_note_to_github.py` — **3/3 passed**
- Full suite — **311 passed, 28 skipped, 8 warnings** (same baseline as main)
- `prek run --all-files` — all 8 hooks **Passed** (ruff lint, ruff format, ty, uv-lock, yaml, etc.)
- Build + sign — `uv run python examples/note_to_github.py` produces `~/Desktop/Note to GitHub.shortcut` without error.
- Plist inspection (via `shortcut-decode --format json`) confirms **two `WFWorkflowImportQuestions`**:
  - `"Your GitHub personal access token (fine-grained, contents: read+write)"` / default `REPLACE_WITH_GITHUB_PAT`
  - `"The repo to commit to (owner/name)"` / default `owner/repo-name`

The Setup section is populated; the two prompts will appear in Shortcuts.app at import time.

---

## What landed

1. **`PLACEHOLDER_TOKEN` / `PLACEHOLDER_REPO` constants removed.** Both were only used as defaults for the two `GetText` actions that preceded `SetVariable`. They are gone from the module.

2. **Two `ask_text_on_import` calls added** at the top of `build()`, replacing the old `GetText(text=PLACEHOLDER_*) + SetVariable` pairs. The Setup section now carries both questions with appropriate user-facing prompts and safe placeholder defaults.

3. **`Shortcut.set` typed-handle pattern applied consistently** across all five variables that follow a `s.add(...)` + `s.add(SetVariable(...))` pair: `Token`, `Repo`, `Stamp`, `Base`, and `ContentB64`. Each is now a local Python handle returned by `s.set(name, action_result)`.

4. **All `NamedVar("...")` references that had a corresponding local handle replaced.** The substitution dicts in `Text(...)`, the `auth_header`, the `DownloadURL` body, and the `ShowNotification` body all reference the typed handles (`token`, `repo`, `stamp`, `base`, `content_b64`) rather than string-keyed `NamedVar(...)` lookups.

5. **Module docstring updated.** The old `⚠️  The token is intentionally a placeholder. Open the resulting shortcut...` warning block is gone. Replaced with a short "Drops … on Desktop. Import, fill in the two Setup prompts, then run." description. The `print(...)` in `main()` is updated to match.

6. **Wire format behaviour unchanged.** The action sequence, action identifiers, HTTP method, headers, and body shape are all identical. The test `test_download_url_carries_auth_and_json_body` passes without modification, confirming no wire-level regression.

---

## Style consistency check

The other four V1 examples use two distinct patterns depending on complexity:

- **`vault_note_to_git`** and **`voice_note_to_git`** and **`spotlight_quick_task`** and **`share_to_inbox`** use a `_add_config(s)` helper function that calls `ask_text_on_import` + `s.set(...)` but does **not** capture the returned handle — they call `s.set("Token", ...)` for the side-effect and rely on `NamedVar("Token")` downstream. Inside their `_add_push` helpers they still reference `NamedVar("Token")` / `NamedVar("Repo")` / `NamedVar("Base")` etc., not typed handles from `_add_config`.

- **`note_to_github`** (this branch) is a flat, non-helper-function example and converts all variables — including Token and Repo — to local typed handles throughout, so `NamedVar(...)` is only used where there is no local handle (specifically `NamedVar("Note")` on line 88, which comes from a plain `s.add(GetClipboard()) + s.add(SetVariable(...))` pair that was **not** converted to `s.set`).

The typed-handle vs. `NamedVar` split is therefore consistent within each file's own idiom. `note_to_github` is a self-contained flat example, so the all-handles approach is appropriate and arguably more illustrative than the helper-function examples. There is no style inconsistency that warrants a change — both patterns are intentional.

One minor note: `note_to_github` still has a raw `s.add(SetVariable(name="Note", input=note))` pair on lines 60–61 rather than converting that to `s.set("Note", note)`. This is a small omission relative to the stated brief ("convert `NamedVar("X")` references to typed handles where they came from a `Shortcut.set` call"), but `NamedVar("Note")` is only used once (line 88, `Base64Encode` input) so there is no practical issue. Not a blocker.

---

## FU-10 preemption check

No preemption. The `DownloadURL(...)` direct construction is identical to main — same constructor, same keyword arguments, same body shape. No factory method, no URL-builder helper, no API layer added. FU-10 is untouched.

---

## Issues

**None blocking.**

Minor: `NamedVar("Note")` (line 88) was not converted to a typed handle via `s.set`. The `note` variable is captured but a bare `s.add(SetVariable(name="Note", input=note))` is used for storage instead of `note_var = s.set("Note", note)`. This is cosmetically inconsistent with the approach applied to `Stamp`, `Base`, and `ContentB64` in the same file. Not worth a re-roll; can be cleaned up in a follow-on.

---

## Merge recommendation

**Merge.** The migration is correct and complete within scope. Both Setup prompts land in the wire format. All tests pass. Linting and type checking are clean. The DownloadURL call is untouched. The docstring and `main()` print are updated consistently. The minor `Note` variable inconsistency is cosmetic and sub-threshold for blocking.
