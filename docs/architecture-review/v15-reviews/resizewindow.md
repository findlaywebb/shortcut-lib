# Review: v15/model-resizewindow

**Action:** `is.workflow.actions.resizewindow`
**Reviewer:** Claude (deputy review, owner away)
**Date:** 2026-05-09
**Head:** `5b375f7`

---

## 1. Verdict

**Approve.** Clean implementation, 23/23 tests pass, all pre-commit hooks green. The
corpus grounding is honest and the docstring accurately flags the speculative Literal
values. No blocking issues found.

---

## 2. Test Result

```
23 passed in 0.12s
```

All pre-commit hooks passed: ruff lint, ruff format, ty (type checking), uv-lock, yaml,
large-file, whitespace.

---

## 3. What Landed

Two new files, 371 lines net:

- `src/shortcut_lib/schema/actions/resize_window.py` (86 lines) — `ResizeWindow`
  dataclass registered under `is.workflow.actions.resizewindow`. Three fields:
  `window` (`ParamValue`), `configuration` (`WFWindowConfiguration | None`),
  `bring_to_front` (`bool | None`). A `__post_init__` guard validates `configuration`
  against a `frozenset` derived from `get_args(WFWindowConfiguration)` and raises
  `SchemaError` on any unrecognised value.

- `tests/test_action_resize_window.py` (285 lines) — 23 tests across: all 10 Literal
  presets, bare (no-configuration) invocation, no-args invocation, `bring_to_front`
  true/false/omitted, registry lookup, identifier/output-name constants, and three
  wire-format round-trips against real sample XML.

---

## 4. Sample Grounding — the 2-of-11 Literal Gap

**Verdict: accepted, and honestly documented.**

The corpus contains exactly 3 appearances of `resizewindow`, all confirmed in the slot
oracle (`observed_envelope_types.json`). Two carry `WFConfiguration`:

- `tile_last_2_windows.xml` action 1 → `"Left Half"`
- `tile_last_2_windows.xml` action 2 → `"Right Half"`

The third (`dictionary.xml`) has `WFWindow` but no `WFConfiguration` key — the bare form.

The remaining 8 Literal values (`"Top Half"`, `"Bottom Half"`, four quarter positions,
`"Fill"`, `"Center"`) are drawn from the standard macOS tiling grid visible in
Shortcuts.app's dropdown. The module docstring is explicit about this: it names both
corpus-confirmed values with exact sample paths and states the rest are "standard macOS
Stage Manager / tiling grid positions that appear in Shortcuts.app's dropdown."

This is a reasonable inference, not silent speculation. The risk is that one or more of
the 8 unverified strings diverges from Apple's wire spelling (e.g. "Top-Left Quarter"
vs "Top Left Quarter"). However: (a) the naming pattern is consistent with the two
confirmed values, (b) the validation guard means a wrong string fails loudly at
construction time rather than silently producing bad plist, and (c) the note about
`WFHeight`/`WFWidth` custom-size mode being out of scope is documented in the module
comment.

No change needed here, but if further corpus samples surface contradictions these
strings should be corrected immediately.

---

## 5. Issues

**Minor — `bring_to_front` not explicitly flagged as Jellycore-only.**

The module docstring says "When `True` emits `WFBringToFront = True`. Defaults to
`None` (key omitted)." It does not note that `WFBringToFront` has zero sample support
and was sourced from Jellycore's spec. The tests encode this correctly (the
`bring_to_front` tests are isolated from any wire-format round-trip), but a future
reader has no in-source signal that this key is unverified against real plist.

Suggested fix — one sentence in the `bring_to_front` arg docstring:

```
bring_to_front: When ``True`` emits ``WFBringToFront = True``.
    Defaults to ``None`` (key omitted).  **No corpus sample confirms
    this key exists in production plist; sourced from Jellycore spec only.**
```

This is non-blocking. The field is safe as written (emitting an unseen key is lower
risk than silently dropping a real one), and the tests are honest about the gap.

**Non-issue — `config` vs `WFConfiguration` override.**

The agent's brief notes that Jellycore listed `config` as the wire key but the actual
plist uses `WFConfiguration`. This is handled correctly — the implementation emits
`WFConfiguration`, the wire-format tests confirm it matches real plist, and the
corpus-over-jellycore discipline is followed. No documentation gap here beyond what the
brief already records.

---

## 6. Merge Recommendation

**Merge.** The implementation is clean, the validation is tight, and the docstrings are
honest about what is and isn't sample-confirmed. The only issue is the missing
Jellycore-only caveat on `bring_to_front` — low enough priority that it can be filed as
a follow-up or folded into the merge commit message rather than blocking the branch.

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `69a33ce`)

**Branch HEAD:** `69a33ce` (diverges from _SUMMARY.md record `5b375f7` — this branch was reviewed in batch 7 on main, not registered in the autonomous session _SUMMARY.md; HEAD advanced by the inline fix commit applied during this pass)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: No conflicts. The branch adds only `src/shortcut_lib/schema/actions/resize_window.py` and `tests/test_action_resize_window.py`; `docs/known_identifiers.md` was not touched on this branch (clean worktree). The review file `resizewindow.md` lives on main and arrives cleanly via merge.

**Pytest on merged state:** 354 passing, 0 failing, 6 skipped, 3 xfailed

**prek:** green (all 8 hooks passed on merged state)

**Drift / observations:**
- Branch is 1 commit ahead of main at the time of the original schema commit (`5b375f7`); now 2 commits ahead after the inline docstring fix (`69a33ce`).
- The `docs/known_identifiers.md` file was not present in the branch diff — no conflict risk on that known trouble file.
- `bring_to_front` provenance caveat was missing from the docstring (flagged as minor in the 2026-05-09 review, section 5). Fixed inline before this merge-readiness pass.
- 8 of 10 Literal `WFWindowConfiguration` values remain UI-inferred; this is honestly documented and accepted per the original review. No sibling actions on main contradict the wire-key choices (`WFWindow`, `WFConfiguration`, `WFBringToFront`).
- `coerce_value` (not `coerce_text_field`) used for the `WFWindow` slot — consistent with `WFTextTokenAttachment` single-variable-ref semantics confirmed by the envelope oracle.

**Minor corrections applied:**
- `src/shortcut_lib/schema/actions/resize_window.py:56-58` — added Jellycore-only caveat to `bring_to_front` arg docstring (commit `69a33ce`)

**Concerns for higher-tier review:**
- none
