# Review: v15/model-list-helpers — `GetItemFromList` + `Count`

**Branch:** `v15/model-list-helpers` (head: ecbea30)
**Reviewer:** agent (Sonnet 4.6), 2026-05-09
**Scope:** `src/shortcut_lib/schema/actions/get_item_from_list.py`,
`src/shortcut_lib/schema/actions/count.py`, and their tests.

---

## 1. Verdict

Solid. Both schemas are correct against the corpus, validation guards are
tight, factory methods are ergonomic, and the one genuine Apple quirk
(`Input` vs `WFInput` for Count) is confirmed and documented. One real
issue with round-trip fidelity for the "Last Item" + `WFItemIndex` case,
and a minor docstring gap in the factory signatures, but neither blocks
merge. Recommend merge with the round-trip issue tracked.

---

## 2. Test Result

**38/38 passed, 0.13 s. prek: all hooks passed (ruff lint, ruff format,
ty, uv-lock).**

---

## 3. What Landed

### `GetItemFromList` (`is.workflow.actions.getitemfromlist`)

- `WFItemSpecifier` typed as a `Literal` over five values.
- Default specifier is `"First Item"`; the key is intentionally omitted from
  the wire format for that value (confirmed from two corpus samples).
- `WFInput` carries the list (standard `WFTextTokenAttachment` envelope).
- `WFItemIndex` emitted only for `"Item At Index"`.
- `WFItemRangeStart` / `WFItemRangeEnd` emitted only for `"Item Range"`.
- `__post_init__` rejects invalid combinations (missing index, missing range
  bounds, fields provided for the wrong specifier).

**Factory extras:** `.first()`, `.last()`, `.random()`, `.at_index(*, list_input, index)`,
`.range(*, list_input, range_start, range_end)`. Each hides the fields that
are not valid for that specifier, turning invalid-combination errors from
`SchemaError` (post-construction) into `TypeError` (at call-site). Factory
signatures are keyword-only throughout.

### `Count` (`is.workflow.actions.count`)

- `WFCountType` typed as a `Literal` over five values; always emitted.
- `Input` wire key for the value to count (see section 4).
- `__post_init__` rejects unrecognised `count_type` values.
- No factory methods — not needed; only one meaningful variant axis.

---

## 4. The `Count.Input` Wire-Key Surprise — Confirmed

**Confirmed across both corpus samples.**

`combine_screenshots_and_share.xml` and `dictionary.xml` both emit the
parameter under the key `Input`, not `WFInput`. The schema correctly uses
`Input`. This is a genuine Apple inconsistency: every other action reviewed
to date uses `WFInput` for the primary value parameter. `Count` is the
first confirmed exception.

The code comment and class docstring both call this out. Worth adding a
cross-reference to the Jellycore stale-key pattern documented in
`text-combine.md` to build up the list of Apple wire-format divergences for
future reference.

---

## 5. The `WFItemIndex` Co-Emission Question — Schema/Apple Disagreement Confirmed

**Real disagreement. The schema drops data on round-trip for this case.**

In `tile_last_2_windows.xml`, the second `getitemfromlist` block contains:

```xml
<key>WFItemIndex</key>
<string>2</string>
<key>WFItemSpecifier</key>
<string>Last Item</string>
```

`WFItemSpecifier` is `"Last Item"` **and** `WFItemIndex` is `2`. This
combination is semantically odd (Last Item ignores index) but it is what
Apple's own shortcut emits.

The current schema only emits `WFItemIndex` when `specifier="Item At Index"`.
If this shortcut were parsed and re-serialised through the schema, the
`WFItemIndex` key would be silently dropped. That is a round-trip fidelity
loss.

**Assessment:** The behaviour is almost certainly benign — Apple's runtime
likely ignores `WFItemIndex` when `WFItemSpecifier` is `"Last Item"`. The
`tile_last_2_windows.xml` sample was probably created by the user switching
the specifier dropdown from "Item At Index" to "Last Item" without the UI
clearing the index field. But "likely" is not "confirmed", and the current
schema cannot reproduce the sample verbatim.

**Recommended action:** Track this in an issue file. A `preserve_extra_params`
escape hatch (or a dedicated `raw_params` field on `Action`) would solve it
generically if it recurs across other actions.

---

## 6. The `list_input` Rename — Sound?

**Defensible, but the docstring gap is a friction point.**

The rename from `input` → `list_input` in factory signatures was made to
satisfy ruff `A002` (local variable / argument shadows the built-in `input`).
The underlying dataclass field is still named `input` (it's an attribute, not
an argument in the lint sense that triggers A002 at the class level), so the
rename only applies to factory method parameters.

This creates a split surface: callers using the direct constructor write
`input=my_list`; callers using a factory write `list_input=my_list`. The
class-level docstring mentions the factory signatures correctly in the example
block, but none of the individual factory method docstrings mention that
`list_input` maps to the `input` field. A reader looking at:

```python
GetItemFromList.last(list_input=my_list)
```

and then the underlying field definition (`input: ParamValue`) would need
to trace through the factory body to understand the connection.

**Minor fix:** Add a one-liner to each factory docstring: "``list_input``
maps to the ``input`` field (renamed to avoid shadowing the built-in)."
This is not a blocker but would reduce future confusion.

---

## 7. Issues

**I1 — Round-trip fidelity: `WFItemIndex` alongside `"Last Item"`** (minor)
The corpus contains one Apple-generated block with `WFItemSpecifier="Last Item"`
and `WFItemIndex="2"`. The current schema drops `WFItemIndex` for any specifier
other than `"Item At Index"`, so this combination cannot be reproduced
verbatim. Behaviour is almost certainly runtime-safe but fidelity is imperfect.
Track and revisit if a generic `raw_params` escape hatch is ever added to
`Action`.

**I2 — Factory docstrings missing `list_input` ↔ `input` mapping note** (nit)
Each factory's one-line docstring should note that `list_input` is the
renamed form of the `input` field. Costs three lines; pays for itself the
first time someone grep-searches for `input=` and finds the factory API
confusing.

**I3 — `Count` `Input` key not cross-referenced with `text-combine` pattern** (nit)
The `Count.Input` anomaly is documented in isolation. Linking it to the
`text-combine.md` Jellycore/Apple divergence note would help whoever is
auditing Apple wire-format inconsistencies in bulk.

---

## 8. Merge Recommendation

**Merge.** Both schemas are correct against the corpus. Tests are thorough
(24 tests for `GetItemFromList`, 14 for `Count`), factory ergonomics are
good, and the known gaps (I1–I3) are tracked here rather than being silent.

The `WFItemIndex` co-emission finding (I1) should become an issue file
before or immediately after merge so it is not lost.

## 2026-05-10 merge-readiness pass

**Verdict:** Request-Human

**Branch HEAD:** `ecbea30` (matches _SUMMARY.md record `ecbea30`)

**Merge against main:**
- Result: aborted — dry-run merge denied by permission system; manual inspection performed instead
- Conflict files: `src/shortcut_lib/schema/actions/get_item_from_list.py`, `tests/test_action_get_item_from_list.py`
- Resolution: See drift/observations below — `v15/model-getitemfromlist` (Batch 11) introduces the same two files with a different implementation. These two branches cannot both land without a human deciding which `GetItemFromList` schema wins.

**Pytest on merged state:** 370 passing, 6 skipped, 3 xfailed (branch-only state, not post-merge); prek clean.

**prek:** green (all 8 checks passed on branch state)

**Drift / observations:**
- `v15/model-getitemfromlist` (Batch 11, head `6d7953a`) introduces `src/shortcut_lib/schema/actions/get_item_from_list.py` and `tests/test_action_get_item_from_list.py` — the same file paths as this branch. When both try to land on `main`, the second merge will have a hard conflict on both files.
- The two implementations diverge on three substantive dimensions:
  1. **Specifier Literal strings**: this branch uses `"Item At Index"` / `"Item Range"` (title-case "At", capitalised "Range"); Batch 11 uses `"Item at Index"` / `"Items in Range"` (lowercase "at", plural "Items"). Neither form is corpus-confirmed (no sample shows `WFItemSpecifier` set to either). The correct form requires a fresh corpus sample with a non-default specifier.
  2. **WFItemIndex emission policy**: this branch only emits `WFItemIndex` for `specifier="Item At Index"`, producing round-trip fidelity loss (issue I1 in the original review). Batch 11 always emits `WFItemIndex` whenever set — round-trip faithful per the `tile_last_2_windows.xml:89-92` corpus evidence.
  3. **Python field name**: this branch uses `index`; Batch 11 uses `item_index`.
- Batch 11's resolution of I1 is the more correct design (corpus-faithful `WFItemIndex` emission, documented with exact line citations). If the user intends to merge both branches, the `GetItemFromList` parts of this branch should be **superseded by** `v15/model-getitemfromlist` — only `count.py` and `test_action_count.py` from this branch are unique and conflict-free.
- `count.py` and `test_action_count.py` are not touched by any other branch and will merge cleanly regardless of order.
- No sibling actions on `main` contradict the `Count` schema. The `Input` (bare, AppIntent-style) wire key is consistent with `calculateexpression.py` and `statistics.py` on their respective branches.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- The `GetItemFromList` implementation in this branch is superseded by the more corpus-faithful `v15/model-getitemfromlist` (Batch 11). The user should decide one of: (a) skip merging this branch's `get_item_from_list.py` / `test_action_get_item_from_list.py` and rely on Batch 11, (b) manually cherry-pick only `count.py` + `test_action_count.py` from this branch, or (c) merge in the correct order (Batch 11 first) and accept that this branch's getitemfromlist files will conflict/be overwritten. The `Count` action in this branch is clean and has no conflict.
- The specifier string capitalisation (`"Item At Index"` vs `"Item at Index"`) needs corpus confirmation before either form is treated as authoritative. A fresh sample with a non-default specifier would resolve this.
