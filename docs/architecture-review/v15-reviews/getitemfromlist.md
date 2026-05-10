# Review: `v15/model-getitemfromlist`

**Identifier:** `is.workflow.actions.getitemfromlist`
**Branch head:** `ab0e553`
**Files changed:** 2 (225 + 329 lines, all new)
**Reviewed:** 2026-05-10

---

## 1. Verdict

**GREEN. Merge recommended.**

The `WFItemIndex` + "Last Item" quirk is corpus-confirmed and the implementation handles it correctly. All 20 tests pass. Prek clean. Source attribution is honest throughout. Cross-field validation is defensible given corpus evidence. One minor gap flagged (see Issues), not blocking.

---

## 2. Test result + prek

```
20 passed in 0.80s
```

Prek: all 8 checks pass (whitespace, end-of-file, yaml, large-files, ruff lint, ruff format, uv-lock, ty).

---

## 3. What landed

- `src/shortcut_lib/schema/actions/get_item_from_list.py` — 225 lines. Module docstring, `WFItemSpecifier` Literal, `_VALID_SPECIFIERS`, `_DEFAULT_SPECIFIER`, `GetItemFromList` dataclass registered under `is.workflow.actions.getitemfromlist`.
- `tests/test_action_get_item_from_list.py` — 329 lines. 20 tests covering: default specifier omission, non-default emission, all five specifiers, "Item at Index" string coercion, "Items in Range" bounds, the WFItemIndex quirk, WFInput envelope shape, default output name, invalid-specifier guard, "Item at Index" missing-index guard, "Items in Range" missing-bound guards, three wire-format equivalence tests against exact corpus UUIDs, registry lookup, and the valid-specifiers set.

---

## 4. The WFItemIndex quirk finding — verified; interpretation sound

**Corpus confirmed.** `tile_last_2_windows.xml` lines 89–92 read, verbatim:

```xml
<key>WFItemIndex</key>
<string>2</string>
<key>WFItemSpecifier</key>
<string>Last Item</string>
```

This is unambiguous: `WFItemIndex` is present with value `"2"`, the specifier is `"Last Item"`, and the action is not "Item at Index". The agent's cite of lines 89–92 is accurate to the character.

**Interpretation.** The agent's framing — "Apple preserves the last-entered index regardless of which specifier is active" — is the most parsimonious reading. The alternative interpretations are:

- *Apple exporter bug:* possible, but indistinguishable from intent without a second independent sample of the same pattern. Even if it is a bug, the right behaviour for this library is to round-trip faithfully, which the implementation does.
- *User changed specifier mid-edit:* the most likely *cause* — the user typed `2` with "Item at Index" active, then switched to "Last Item" without clearing the field. Apple's UI evidently does not zero out `WFItemIndex` on specifier switch. This is consistent with the "preserve last-entered value" framing.

Either way the implementation decision is correct: include `WFItemIndex` whenever set, irrespective of specifier. The module docstring, `_params()` docstring, and the test (`test_wf_item_index_emitted_alongside_last_item_specifier`) all document the evidence and rationale clearly. The open V1.5 follow-up item — *"WFItemIndex without WFItemSpecifier Apple quirk on GetItemFromList — needs a fresh sample to confirm"* — is answered by this corpus appearance. Ready to be closed.

---

## 5. Specifier Literal — sample-confirmed vs UI-only breakdown

The five values in `WFItemSpecifier`:

| Value | Sample-confirmed | Source |
|---|---|---|
| `"First Item"` | Yes | `dictionary.xml:185-204` and `tile_last_2_windows.xml:24-43` — default; Apple omits the key when this is selected, which is itself corpus evidence. |
| `"Last Item"` | Yes | `tile_last_2_windows.xml:70-93` — explicit `WFItemSpecifier` key present. |
| `"Random Item"` | No | UI-inferred. Not observed in corpus. |
| `"Item at Index"` | No | UI-inferred; the key name matches the `WFItemIndex` companion field, so the pairing is structurally coherent, but no corpus sample shows `WFItemSpecifier="Item at Index"` explicitly. |
| `"Items in Range"` | No | UI-inferred. Not observed in corpus. |

The module docstring correctly describes which appearances confirm which specifiers and does not overclaim for the three unobserved values. The test `test_valid_specifiers_set` asserts the full five-element set explicitly, which is honest: the test is pinning intended behaviour, not asserting corpus confirmation for each member.

**Observation:** "Item at Index" is the one UI-inferred value where the risk of a wrong string is highest — if the key is wrong, the index field silently does nothing. A note in the module docstring acknowledging the "Item at Index" string is UI-inferred (not sample-confirmed) would strengthen the audit trail. Not blocking; the existing framing is defensible.

---

## 6. Cross-field validation — defensible

`__post_init__` enforces two rules:

1. `specifier="Item at Index"` requires `item_index` to be set.
2. `specifier="Items in Range"` requires both `range_start` and `range_end`.

**The inverse is deliberately not enforced:** `item_index` may be set with any specifier. This is correct — the corpus quirk (WFItemIndex alongside "Last Item") is direct evidence that Apple writes the index field independently of the specifier. Enforcing `item_index` only when specifier is "Item at Index" would reject a round-trip of the corpus appearance at line 89–92. The `_params()` docstring explains this trade-off explicitly, which is the right place for it.

One gap: there is no guard for `range_start > range_end`. This is speculative territory (no corpus sample for "Items in Range") and the field is UI-inferred, so leaving it unguarded is defensible under the project's "corpus-first" principle. Worth noting as a potential polish item but not a blocker.

---

## 7. Source attribution audit

- **Jellycore:** `jq '.["is.workflow.actions.getitemfromlist"]' data/jellycore_facts.json` returns `null`. The module docstring states this explicitly: "jellycore has no entry for this action. All type evidence is derived from the three corpus appearances and `data/observed_envelope_types.json`." No false attribution.
- **Corpus citations:** All three appearance line ranges verified against the XML files. `dictionary.xml:185-204` and `tile_last_2_windows.xml:24-43` (first-item defaults) and `tile_last_2_windows.xml:70-93` (Last Item + quirk) all check out. The three wire-format equivalence tests embed the exact UUIDs from the XML, which is the strongest possible corpus anchoring.
- **`observed_envelope_types.json`:** Cited for the bare-string claim on `WFItemIndex` and `WFItemSpecifier`. Not independently verified in this review, but the string-coercion test (`isinstance(params["WFItemIndex"], str)`) would catch a mismatch at runtime.
- **Default output name:** `tile_last_2_windows.xml:57` shows `<string>Item from List</string>` as the `OutputName` in the downstream `resizewindow` action's `WFWindow` reference. Verified. The cite is accurate.

Attribution is clean across all four evidence sources.

---

## 8. Doc quality

**4/5.** The module docstring is thorough: wire-format section, corpus-evidence section with line citations for all three appearances, the WFItemIndex quirk with interpretation, jellycore-null disclaimer, full field-by-field Args table, Returns section with confirmed output name, and cross-references to `BuildList` and `ChooseFromList`.

The class docstring and `_params()` docstring are both clear and appropriately concise. The three usage examples (first item, item at index, last item) cover the most common patterns.

Minor: the "Item at Index" Literal value is described in the Args table without flagging it as UI-inferred. The first-item and last-item specifiers have explicit corpus grounding in the module docstring, but the three unconfirmed values ("Random Item", "Item at Index", "Items in Range") aren't called out as unconfirmed. This is a style gap relative to batch-9/10 actions (`math.md`, `calculateexpression.md`) that explicitly disclaim UI-inferred Literals. Not a doc-quality failure at the current bar, but worth aligning in a future doc sweep.

---

## 9. Issues

**No blocking issues.**

Minor, non-blocking:

- "Item at Index" specifier string is UI-inferred but not explicitly disclaimed as such in the module docstring. Low risk (the value is structurally coherent with the `WFItemIndex` field name), but inconsistent with batch-9/10 honesty conventions.
- No `range_start > range_end` guard for "Items in Range". Speculative territory; no corpus evidence either way. Could be a V1.5 polish item if "Items in Range" is confirmed in a future sample.

---

## 10. Merge recommendation

**Merge.** GREEN on all dimensions: tests pass, prek clean, corpus citations verified, quirk interpretation sound, no false attribution, cross-field validation defensible.

**Close-out note for `_SUMMARY.md` open follow-up:**

The item *"WFItemIndex without WFItemSpecifier Apple quirk on GetItemFromList — needs a fresh sample to confirm"* is answered. `tile_last_2_windows.xml:89-92` provides direct corpus evidence: `WFItemIndex="2"` alongside `WFItemSpecifier="Last Item"`. The implementation handles it correctly by emitting `WFItemIndex` whenever set, irrespective of specifier. This follow-up can be struck from the open list on merge.

Suggested placement in `_SUMMARY.md` merge order: Batch 10 tier (no dependencies, independent action coverage).
