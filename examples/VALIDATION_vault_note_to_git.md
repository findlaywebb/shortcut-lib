# Vault Note → Git — on-device validation

End-to-end validation of `examples/vault_note_to_git.py` (Phase E1 in
`docs/roadmap.md`).

## Result

**Working** — clipboard note → Apple Intelligence polish → committed
to a GitHub sandbox repo as `notes/note_<stamp>.md`.

## Setup used

- **Device**: iPhone, iOS 26.4.2, Apple Intelligence enabled.
- **Trigger**: clipboard. (Share-sheet rewiring not yet validated;
  surfaces are declared but the shortcut consumes `GetClipboard()`.)
- **Auth**: fine-grained PAT scoped `Contents: read+write` on a
  sandbox repo, edited into the placeholder Text actions in
  Shortcuts.app after import.

## Bugs surfaced and fixed during validation (2026-05-08 / 2026-05-09)

Three instances of the same envelope-shape bug class. Apple's runtime
reads several parameter slots as `WFTextTokenString`; a bare
`WFTextTokenAttachment` (which `coerce_value` produces for an
`Action`/`Value` reference) is silently ignored at those slots.

| Slot | Symptom |
|------|---------|
| `WFURL` (DownloadURL) | "No URL Specified"; URL field renders disconnected |
| JSON body dict values | Body field references look unlinked in the editor |
| `WFDate` (FormatDate) | Empty formatted output; here, filename became `note_.md` |

Fix: `coerce_text_field` in `src/shortcut_lib/schema/base.py` rewraps
the bare attachment as a single-attachment `WFTextTokenString`
(`string="￼"`, `attachmentsByRange={"{0, 1}": token}`). Wired into
`DownloadURL.WFURL`, `FormatDate.WFDate`, and the JSON body / header
dict path. Plain strings pass through unchanged (matches Apple's
emission for static URLs).

## Lessons (carried forward)

- **Locally-signed `.shortcut` files cannot pre-link RunWorkflow
  targets.** iOS assigns a fresh UUID at import time and ignores any
  identifier baked into the file. Multi-shortcut composition requires
  manual re-selection in the picker after every import. Pivoted the
  composition story: Python helper *functions* compose; each
  `Shortcut` emits as one self-contained workflow. `RunWorkflow`
  remains for cases where a separate trigger is genuinely required.
- **GitHub Files API requires per-run unique paths.** Per-second
  timestamp collides on rapid re-runs and produces a 422 (`"sha"
  wasn't supplied`). Bumped the filename precision to milliseconds
  (`yyyy-MM-dd_HH-mm-ss-SSS`). For long-term robustness a real
  create-or-update path needs GET-then-PUT-with-sha; punted.
- **The envelope-shape bug class is broader than three slots.** Worth
  a deliberate sweep (see `FU-7` in `docs/handoff.md`).

## Sample input / output

- **Input**: a short markdown note copied to clipboard.
- **Output**: a commit on the sandbox repo at
  `notes/note_2026-05-09_HH-mm-ss-SSS.md` containing the polished
  text. Apple Intelligence's "polish for clarity and tone" prompt
  produced acceptable output on a casual note.
