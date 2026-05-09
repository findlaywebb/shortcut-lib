# Review: v15/model-text-combine

**Verdict: green**
**Branch:** `v15/model-text-combine` (head: a3be634)
**Reviewer:** Claude Sonnet 4.6 (autonomous, 2026-05-09)

---

## Test result

13/13 passed, 0 failures, 0 skipped. Full suite: 344 passed, 6 skipped, 3 xfailed.
All pre-commit hooks pass (ruff lint, ruff format, ty, uv-lock).

---

## What landed

Three files changed (+368 lines):

- `src/shortcut_lib/schema/actions/text_combine.py` — 85 lines. Typed schema for `is.workflow.actions.text.combine`.
- `tests/test_action_text_combine.py` — 267 lines. 13 tests including 2 wire-format equivalence tests grounded in corpus samples.
- `docs/known_identifiers.md` — histogram updated to include `text.combine` row (5 appearances, daily_standup + dictionary + sort_lines) and minor surrounding count corrections from a refreshed scan.

---

## Jellycore divergence: independently confirmed

The agent's claim holds. `data/jellycore_facts.json` lists the action's parameter keys as `["text", "combine", "WFTextCustomSeparator"]` — using `"combine"` as the separator key. All 5 corpus samples use `"WFTextSeparator"` instead:

- `daily_standup.xml` indices 5, 12, 19: `WFTextSeparator: "New Lines"` present explicitly
- `dictionary.xml` index 40: no separator key (default "New Lines" omitted)
- `sort_lines.xml` index 2: no separator key (default "New Lines" omitted)

The schema correctly uses `WFTextSeparator` as the wire key, trusting corpus over Jellycore. This is the right call per the project's sample-grounded convention.

---

## Pattern alignment with TextSplit

Alignment is correct where the corpus mandates it and intentionally diverges where the actions differ.

**Matches:**
- `_VALID_SEPARATORS` derived from `get_args(...)` on the Literal alias.
- `__post_init__` validation with the same message style (`ClassName.field value is not valid...`).
- `_params()` omits the separator key when value equals `"New Lines"` (default-omit rule). Confirmed by dictionary.xml (no key) and sort_lines.xml (no key).
- `Show-text` opt-in: emitted only when not `None`. Grounded in sort_lines.xml index 2 and batch_add_reminders.xml index 9.
- Input slot wire key is `text`, envelope is `WFTextTokenAttachment`. Oracle (`data/observed_envelope_types.json`) shows 5/5 corpus appearances use `WFTextTokenAttachment` for the `text` slot — `coerce_value` is the correct choice.

**Intentional divergences (not issues):**

1. **Literal alias name:** TextSplit defines `WFTextSeparator = Literal[...]`. TextCombine defines `WFTextCombineSeparator = Literal[...]`. The rename avoids a module-level name collision if both are imported in the same namespace. This is correct.

2. **Separator wire key in `_params()`:** TextSplit emits `out["separator"] = self.separator` for non-default values. TextCombine emits `out["WFTextSeparator"] = self.separator`. This is the meaningful difference — `"separator"` vs `"WFTextSeparator"` — and the combine side is corpus-confirmed. The split side cannot be independently verified from the current corpus (all 6 text.split samples use the default "New Lines" and omit the key), but that is TextSplit's pre-existing concern, not this PR's.

3. **Valid separator set:** TextSplit allows `"Every Character"`, TextCombine does not. The docstring explains this correctly: "Every Character" is split-only with no combine equivalent.

---

## Issues

### Minor: daily_standup round-trip gap (known limitation, not a bug)

Three of the 5 corpus appearances (daily_standup.xml indices 5, 12, 19) write `WFTextSeparator: "New Lines"` explicitly rather than omitting it. The schema always omits it for "New Lines" to produce minimal output. This is correct per project convention, but it means the schema cannot round-trip those 3 samples. The wire-format equivalence tests wisely target dictionary.xml (omits key) and sort_lines.xml (omits key) — the two samples where Apple's generator also omits it.

This Apple generator inconsistency should be noted in the docstring or a comment. The current code mentions `dictionary.xml confirms: no separator key`, which implies it's universally omitted, but it isn't. A comment like `Apple is inconsistent here — daily_standup.xml emits it explicitly; we omit for minimal output` would be more accurate. This is cosmetic; no functional impact.

### Non-issue: oracle absence flag

`d.get('is.workflow.actions.text.combine', None)` returned `null` initially due to the oracle file's top-level structure being keyed under `slots`, not the root. The oracle does have an entry under `slots['is.workflow.actions.text.combine']['text']` confirming `WFTextTokenAttachment` (5 observations). No action needed.

### Non-issue: Literal alias visibility

`WFTextCombineSeparator` is module-level and exported. This is fine — it gives callers the type without `text_combine.py` clashing with `text_split.py`'s `WFTextSeparator`. Both are importable without collision.

---

## Discoverability

`uv run python scripts/print_actions.py` from the worktree emits:

```
### TextCombine → Combined Text
`is.workflow.actions.text.combine`
_Combine a list of text items into a single string._
```

Discoverable, formatted correctly.

---

## Merge recommendation

**Merge.** The implementation is correct, corpus-grounded, and complete. All 13 tests pass including sample-exact wire-format equivalence for both nominated samples. The jellycore divergence is handled correctly and documented at the source level. Pattern alignment with TextSplit is faithful except where the actions legitimately differ. The one cosmetic issue (docstring slightly overstates the default-omit universality) is low enough priority to address post-merge or in a follow-on pass.
