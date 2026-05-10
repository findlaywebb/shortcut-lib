# v15/model-system-controls — Architecture Review

**Branch:** `v15/model-system-controls` (head: `f924eff`)
**Scope:** `SetDoNotDisturb` (`set_focus.py`) + `SetVolume` (`set_volume.py`)
**Reviewer:** architecture-review agent, 2026-05-10

---

## 1. Verdict

Merge. Both action classes are correct, well-tested, and honestly attributed.
The `SetDoNotDisturb` implementation contains the most interesting wire-format
work in this batch and executes it cleanly. `SetVolume` is straightforward but
does the right thing on the edge cases. One docstring position-taking issue
noted below; no blocking concerns.

---

## 2. Test result + prek

```
30 passed in 1.03s
```

All eight prek hooks pass (trailing whitespace, EOF, yaml, large-files, ruff
lint, ruff format, uv-lock, ty). Clean across the board.

---

## 3. What landed

### SetDoNotDisturb (`is.workflow.actions.dnd.set`)

Five optional Python fields map to five corpus-observed wire keys:

| Python field | Wire key | Envelope |
|---|---|---|
| `enabled` | `Enabled` | integer 0/1 |
| `assertion_type` | `AssertionType` | bare string |
| `focus_modes` | `FocusModes` | plain dict |
| `until` | `Time` | `WFTextTokenString` |
| `event` | `Event` | `WFTextTokenAttachment` |

The empty-params shape (dictionary.xml) is handled correctly: all fields
default to `None`, so the no-arg constructor emits only `UUID`.

### SetVolume (`is.workflow.actions.setvolume`)

One optional Python field:

| Python field | Wire key | Envelope |
|---|---|---|
| `volume` | `WFVolume` | float or `WFTextTokenAttachment` |

The no-arg constructor emits only `UUID`, matching both dictionary.xml
appearances. Integer inputs are coerced to float before emission. Out-of-range
floats and integers raise `SchemaError`.

---

## 4. The dual-envelope finding — verified

**Confirmed in raw XML.** Both `Time` and `Event` in start_pomodoro.xml
reference the same UUID (`3776F881-73AB-4A82-961F-7AEC4563A72B`, "Break End
Time"), yet they use different envelopes:

- `Time` → `WFTextTokenString` with `attachmentsByRange: {"{0, 1}": {OutputUUID: ..., OutputName: ..., Type: "ActionOutput"}}` and `string: "￼"`
- `Event` → `WFTextTokenAttachment` with `Value: {OutputUUID: ..., OutputName: ..., Type: "ActionOutput"}` at the top level

This is exactly the pattern described in `wire-format-quirks.md §4`:
`WFTextTokenString` for slots that Apple's runtime reads as a templated
string; `WFTextTokenAttachment` for single-variable-only slots. The finding is
significant because it shows that **the envelope shape is determined by the
slot's semantic type, not the value type** — the identical UUID is wrapped
differently because `Time` is a "string-bearing" slot and `Event` is a
"single-token" slot.

**Recommendation:** Add a concrete row for `dnd.set` / `Time` and
`dnd.set` / `Event` to `wire-format-quirks.md §4`'s tables. This is the
cleanest in-corpus example of the same value appearing in both envelope types
simultaneously — it's worth calling out explicitly. The doc already names both
slots in the bare-keys table (§1), but the dual-envelope angle deserves a note
in §4 or §6.

The implementation handles this correctly: `_params()` detects whether the
`until` value is already a `WFTextTokenAttachment` and rewraps it as a
one-attachment `WFTextTokenString`; `event` is left as-is via `coerce_value`.

---

## 5. AssertionType — Literal position

**Recommendation: keep `str`, do not make it a `Literal`.**

Only `"Time"` is confirmed in corpus. The docstring correctly lists `"Event"`
and `"Indefinitely"` as plausible-but-unconfirmed alternatives. A `Literal["Time"]`
would be misleading: it signals "these are the only valid values" but iOS
almost certainly accepts others (the UI offers at minimum "Time", "Event-based",
and no-end-time variants depending on the Focus configuration). The type
annotation is `str | None`, the docstring names the one confirmed value and
acknowledges the open set — that's the right balance. Do not narrow it further
without additional corpus evidence.

---

## 6. WFVolume range guard — defensible

The `0.0 ≤ volume ≤ 1.0` `SchemaError` guard is defensible and correct.
Rationale:

- The Shortcuts UI renders a continuous slider from 0% to 100% (proportional).
  Out-of-range floats cannot be entered through the UI; they can only arrive
  from the library.
- Jellycore names the parameter but does not specify a range; the UI is the
  only specification and it is unambiguous.
- A library that silently emits `WFVolume: 1.5` would produce undefined
  iOS behaviour and is strictly worse than raising early.

The only alternative position — accept any float and let iOS clamp — is also
defensible, but the early-raise approach is consistent with how `SchemaError`
is used elsewhere in the library (e.g. `GetItemFromList` index bounds). Keep
the guard.

One minor note: the `isinstance(self.volume, bool)` exclusion in the `int`
branch is correct and catches `True`/`False` being passed as ints (Python
`bool` is a subclass of `int`). Good defensive coding.

---

## 7. Source-attribution audit

Both docstrings attribute every parameter key to one of three sources:
corpus observation, jellycore, or inference from the UI. No false jellycore
claims found.

- `Enabled` — jellycore-listed, corpus-confirmed. Both stated.
- `AssertionType`, `FocusModes`, `Time`, `Event` — corpus-only (start_pomodoro.xml).
  Docstring explicitly flags these as corpus-only and notes jellycore lists
  only `Enabled`. Accurate.
- `WFVolume` — jellycore-listed; corpus silent (both appearances empty). Docstring
  explicitly states this: "Jellycore names the key `WFVolume`… corpus is silent
  (empty params) so no direct confirmation exists in the sample set." Accurate.

The docstring for `SetDoNotDisturb` contains a slightly awkward note: "From
start_pomodoro.xml both `Time` and `Event` carried the same `ActionOutput` ref;
the relationship between the two is unclear — pass both when reproducing that
exact wire shape." This is honest but arguably under-explains: the agent's own
implementation shows the relationship is not mysterious — they are the same
logical value slotted into two different semantic slots (string-bearing vs.
single-token). A future revision could tighten this prose to say "both slots
reference the same action output; pass both to reproduce the wire shape exactly."
Not a blocker.

---

## 8. Doc quality

### SetDoNotDisturb

**Score: A-**

- Summary line is accurate and within 72 chars.
- Apple display name change (iOS 14 → "Set Focus") noted. Useful for future
  corpus search.
- Wire-format notes section covers all five observed behaviours: integer
  `Enabled`, `WFTextTokenString` for `Time`, `WFTextTokenAttachment` for
  `Event`, plain-dict `FocusModes`, and empty-params validity.
- The dual-envelope note is present and technically correct; the "unclear"
  phrasing could be sharpened (see §7 above), but does not mislead.
- The `FocusModes` example in the docstring (inline dict) is taken verbatim
  from corpus. Good practice.
- AppIntent-aliasing note confirms jellycore's `Enabled` matches corpus exactly
  (no WF-prefix discrepancy). Correct and useful.

### SetVolume

**Score: A-**

- Summary line is accurate.
- Corpus silence explicitly stated — this is the right thing to do when the
  only data is "we saw two empty params dicts."
- Mute semantics (`volume=0.0` to silence) called out explicitly. Good.
- No separate `Mute` boolean clarification is useful forward-looking context.
- The "Validation" sub-section at the end of the docstring is a nice touch;
  it makes the SchemaError guard discoverable without reading `_params()`.
- The one-liner "Jellycore names the key `WFVolume`… this is already WF-prefixed
  and aligns with the broader WF-key convention" is accurate and helpfully
  distinguishes this from the bare-key cases.

---

## 9. Issues

None blocking. Two minor items:

1. **Docstring prose** (`SetDoNotDisturb`, `event` arg): "the relationship
   between the two is unclear" is slightly misleading — both slots carry the
   same value but require different envelopes, which is the corpus-confirmed
   dual-envelope pattern, not a mystery. A one-sentence clarification would
   sharpen this. Low priority.

2. **wire-format-quirks.md §4** is missing a concrete `dnd.set` example row
   in the `WFTextTokenString` and `WFTextTokenAttachment` tables. The dual-
   envelope case is the clearest in-corpus demonstration that the same value
   can appear in both envelope types. Worth adding after merge as a standalone
   doc edit.

---

## 10. Merge recommendation

**Merge as-is.** Both classes are correct, tests are thorough (30 pass, 0 skip),
prek is clean, and source attribution is honest throughout. The dual-envelope
implementation is the library's most rigorous handling of the
`WFTextTokenAttachment`-rewrap-to-`WFTextTokenString` pattern to date, and the
tests lock it in precisely. The minor docstring and quirks-doc follow-ons are
post-merge.
