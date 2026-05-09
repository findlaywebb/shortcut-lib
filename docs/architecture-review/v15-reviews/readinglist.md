# Review: v15/model-readinglist

**Reviewer:** agent (on behalf of Findlay)
**Date:** 2026-05-09
**Branch head:** b7e4a45
**Files:** `src/shortcut_lib/schema/actions/reading_list.py`, `tests/test_action_reading_list.py`

---

## 1. Verdict

**Approve.** The implementation is correct, minimal, and well-evidenced. The
`coerce_value` choice is confirmed by both the corpus and the oracle. Test
discipline is exemplary for a one-slot action.

---

## 2. Test result

8/8 passed, 0 failures, 0 skips. Ruff lint and format checks clean on both
files. `pre-commit` is not installed in the worktree environment, but the
individual linter invocations (`ruff check`, `ruff format --check`) pass
without complaint — adequate substitute for the pre-commit gate.

---

## 3. What landed

Two new files, 299 lines total:

- **`reading_list.py`** (54 lines) — `ReadingList(Action)` dataclass wrapping
  `is.workflow.actions.readinglist`. Single optional param `url: ParamValue =
  None`, serialised as `WFURL` via `coerce_value`. The key is omitted when
  `url` is `None`, matching the third corpus appearance. Module docstring,
  class docstring, and `_params` docstring are all present and within the
  72-char summary rule.

- **`test_action_reading_list.py`** (245 lines) — 8 tests covering: NamedVar
  URL, Output URL, field omission, registry lookup, two wire-format
  equivalence checks (one per named corpus sample), the WFTextTokenAttachment
  envelope pin (test 7), and `default_output_name`.

No changes to existing files. No new dependencies introduced.

---

## 4. The WFTextTokenAttachment vs WFTextTokenString distinction — confirmed

The oracle (`data/observed_envelope_types.json`) records exactly two
appearances of `WFURL` on `is.workflow.actions.readinglist`, both
`WFTextTokenAttachment`:

```json
{
  "WFURL": {
    "envelopes": {
      "WFTextTokenAttachment": {
        "count": 2,
        "samples": [
          "samples/decoded/dictionary.xml:211",
          "samples/decoded/read_later.xml:7"
        ]
      }
    }
  }
}
```

The raw XML in both samples confirms the shape: `WFSerializationType =
WFTextTokenAttachment`, with a flat `Value` dict containing `OutputName`,
`OutputUUID`, and `Type = ActionOutput`. No `string` key, no
`attachmentsByRange` — the markers that would indicate a WFTextTokenString
wrapper.

The third corpus appearance (the second hit in `dictionary.xml`) has no
`WFURL` key at all — just `UUID` in the params. The omit-when-None behaviour
is correct.

**The distinction matters.** `DownloadURL.WFURL` uses `WFTextTokenString`
because the HTTP runtime requires a fully-resolved text value; passing a bare
`WFTextTokenAttachment` there results in "No URL Specified" at runtime. The
Reading List action is more permissive — it accepts the bare attachment
directly. Using `coerce_text_field` here would produce a structurally
different envelope that the corpus does not support.

**Should the wire-format-quirks doc gain a note?** Yes. The
WFTextTokenAttachment-vs-WFTextTokenString distinction for URL slots is the
single highest-confusion point across the corpus, and DownloadURL vs
ReadingList is the cleanest side-by-side example available. A note in the
wire-format-quirks doc pairing these two actions would head off the wrong
choice in any future URL-bearing action. Consider adding it when that parallel
branch merges — it does not need to block this one.

---

## 5. Issues

None. No pre-existing issues encountered in the touched files. No adjacent
code was modified, so no scope-expansion question arises.

---

## 6. Merge recommendation

**Merge.** All acceptance criteria met:

- 3 corpus appearances confirmed (1 in `read_later.xml`, 2 in `dictionary.xml`).
- All populated WFURL instances are `WFTextTokenAttachment`; the no-WFURL
  case omits correctly.
- Test 7 is sound: it asserts `WFSerializationType == "WFTextTokenAttachment"`,
  then asserts absence of `string` and `attachmentsByRange` from the `Value`
  dict — exactly the right negative assertions to distinguish the two envelope
  shapes.
- `coerce_value` is the correct choice, confirmed by oracle and raw XML.
- 8/8 tests pass; linters clean.

One follow-on: file a note about the URL-slot distinction in the
wire-format-quirks doc on its parallel branch (not a blocker).
