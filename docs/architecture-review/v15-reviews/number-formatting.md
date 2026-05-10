# Review: v15/model-number-formatting

**Head:** `d0c75d2`
**Actions modelled:** `is.workflow.actions.format.number` (FormatNumber), `is.workflow.actions.detect.number` (DetectNumber)
**Files:** `src/shortcut_lib/schema/actions/format_number.py`, `src/shortcut_lib/schema/actions/detect_number.py`, `tests/test_action_format_number.py`, `tests/test_action_detect_number.py`

---

## 1. Verdict

**Merge with one doc fix** (see §8). Both actions are correctly modelled, wire-verified against corpus, and properly attributed. The "decimal-places only" scope is defensible given available evidence, but the docstring should explicitly flag the UI-vs-wire gap rather than merely stating the limitation as fact.

---

## 2. Test result + prek

```
20 passed in 0.86s
```

All eight prek hooks pass (trim whitespace, end-of-file, YAML, large files, ruff lint, ruff format, uv-lock, ty). No warnings.

---

## 3. What landed for each

**FormatNumber** (`format_number.py`, 66 lines)

- `number: ParamValue` — emitted under `WFNumber`; omitted when `None`.
- `decimal_places: int | None` — emitted under `WFNumberFormatDecimalPlaces`; omitted when `None`.
- `default_output_name = "Formatted Number"`.
- 13 tests covering: wire attachment shape, corpus equivalence (both UUID appearances), decimal-places at 0 and 4, omission of both keys when fields are `None`, scalar int/float passthrough, registry lookup, `output()` chaining.

**DetectNumber** (`detect_number.py`, 59 lines)

- `input: ParamValue` — emitted under `WFInput`; omitted when `None`.
- No additional parameters.
- `default_output_name = "Numbers"`.
- 7 tests covering: wire attachment shape, corpus equivalence, no-input omission, strict key-set assertion (`{WFInput, UUID}` only), plain-string passthrough, registry lookup, `output()` chaining.

---

## 4. Wire-key verification

**FormatNumber — `WFNumber` confirmed.**

Both corpus appearances are clear:

```xml
<key>WFNumber</key>
<dict>
    <key>Value</key>
    <dict>
        <key>OutputName</key><string>Rounded Number</string>
        <key>OutputUUID</key><string>AC7B3655-7E12-4D60-A7FF-C7F5D9233F9D</string>
        <key>Type</key><string>ActionOutput</string>
    </dict>
    <key>WFSerializationType</key><string>WFTextTokenAttachment</string>
</dict>
```

`WFNumber` is the correct key; `WFInput` would have been wrong. The envelope is `WFTextTokenAttachment` (bare), not `WFTextTokenString` — both appearances agree. The jellycore `parameter_keys` list (`["WFNumber", "WFNumberFormatDecimalPlaces"]`) is consistent.

**DetectNumber — `WFInput` confirmed.**

Both corpus appearances use `WFTextTokenAttachment` on `WFInput`. Consistent with the sibling `detect.*` family (address, contacts, date, email, images, link, phone, text — all `WFInput`-only in jellycore).

---

## 5. The "decimal-places only" finding — defensible scope or under-modelling?

The claim is defensible given available evidence, but the framing should be tightened.

**What the evidence shows:**
- Both corpus appearances of `format.number` contain only `WFNumber` and (in both cases) *no* `WFNumberFormatDecimalPlaces` — the decimal-places key is entirely absent from the wire in the wild. This is expected: when the key is omitted iOS applies its own default (the docstring says 2; that is unverified at the wire level but plausible).
- Jellycore lists exactly two parameter keys: `WFNumber` and `WFNumberFormatDecimalPlaces`. It names no style enum.
- The only other `format.*` entries in jellycore are `format.date` (which carries `WFDateFormatStyle` and `WFTimeFormatStyle`) and `format.filesize` (which carries `FormatSize`). There is no `format.measurement`, `format.currency`, or `format.percent` identifier in jellycore at all.

**The gap:**
The Shortcuts.app UI *does* present a style picker (Decimal, Currency, Scientific, Percent, Spell Out). The open question is whether those styles route to a *different* parameter key within `format.number` (not seen in the 2-appearance corpus), or to a *different* identifier not yet in jellycore. Given the corpus size for this action is minimal (2 appearances, neither exercising the style picker), absence of evidence is not strong evidence of absence.

**Current docstring handling:**
The Quirks section says "No style enum (currency / percent / scientific) is present in the wire format" — which is accurate but reads as a definitive ruling. It should flag it as a known gap in corpus coverage, not a confirmed design fact.

**Recommendation:** Add one sentence to the Quirks block, e.g.:
> "The Shortcuts.app UI exposes style modes (Currency, Percent, Scientific, Spell Out) not seen in the 2-appearance corpus sample; these may live under an additional parameter key not yet observed, or on a sibling identifier. Treat this action as corpus-confirmed decimal-places only — style-mode support is out of scope until a wider corpus sample is available."

---

## 6. Source-attribution audit

| Claim | Source | Verdict |
|---|---|---|
| `WFNumber` wire key | corpus (2 appearances) | Confirmed |
| `WFNumberFormatDecimalPlaces` wire key | jellycore `parameter_keys` | Confirmed; not seen in corpus (key absent in both appearances) |
| `WFNumber` uses `WFTextTokenAttachment` | corpus (2 appearances) | Confirmed |
| `WFInput` wire key | corpus (2 appearances) | Confirmed |
| `WFInput` uses `WFTextTokenAttachment` | corpus (2 appearances) | Confirmed |
| `default_output_name = "Formatted Number"` | downstream `OutputName` reference in corpus | Confirmed — both detect.number corpus appearances carry `OutputName = "Formatted Number"` pointing at the format.number UUID |
| `default_output_name = "Numbers"` | downstream `OutputName` reference in corpus | Confirmed — the math action immediately after the first detect.number appearance carries `OutputName = "Numbers"` pointing at UUID `77CAA732` |
| `minimum host: iOS 14` | jellycore `lowest_compatible_host: "iOS14"` | Confirmed for both actions |
| No additional config keys on detect.number | jellycore + corpus key-set | Confirmed |
| Decimal-places only on format.number | jellycore + corpus (2 samples) | Partially confirmed — see §5 |

No false jellycore claims found. Line number citations in both files (`lines 332-345`, `lines 355-368`, `lines 4523-4536`, `lines 4546-4559`) are accurate.

---

## 7. Doc quality

**FormatNumber — 8/10**

Strong. The Args block is thorough: each field documents the wire key, the envelope type, the corpus source, and the omission behaviour. The Quirks block is clear and the jellycore attribution is correct. Minor deduction for the under-hedged style-mode claim (§5). The "Apple defaults to 2 decimal places" claim is plausible but not corpus-verified — a small hedge (`"Apple's runtime default appears to be 2"`) would be more precise.

**DetectNumber — 9/10**

Crisp and well-attributed. The "mirrors the pattern of other `detect.*` actions" framing is accurate and useful context. The key-set assertion (`{WFInput, UUID}`) in the test is excellent — best practice for this family. No false claims.

---

## 8. Issues

**Issue 1 (minor — doc): Style-mode scope under-stated in FormatNumber docstring**

The Quirks block asserts no style enum exists in the wire format but does not flag this as a corpus-coverage limitation. Given the app UI clearly offers style modes, future contributors reading this as a definitive statement may model against it without re-checking. Add a sentence (see §5 for draft text).

**Issue 2 (observation — not a bug): `default_output_name = "Numbers"` is plural; jellycore display name is "Get Numbers From Input"**

The output name "Numbers" is corpus-confirmed via the downstream math action reference. There is no mismatch. Flagging only to document that this was verified rather than inferred from the display name.

**Issue 3 (observation): `WFNumberFormatDecimalPlaces` is jellycore-attested but zero corpus appearances**

Both corpus appearances have no `WFNumberFormatDecimalPlaces` key (users left decimal places at the default). The key is correctly gated behind `if self.decimal_places is not None` so the default-omission behaviour matches corpus. The test suite covers the non-None case. No action required; noted for the record.

---

## 9. Merge recommendation

**Merge.** Both actions are correct, fully tested, cleanly attributed, and pass all checks. The one required touch before merge is a single sentence in `FormatNumber`'s Quirks block to explicitly flag the style-mode gap as a known corpus-coverage limitation rather than a confirmed design fact. That is a two-line edit in the docstring — no schema or test changes needed.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `1889e1e` (matches _SUMMARY.md record — _SUMMARY.md recorded `d0c75d2` which was the initial commit; `1889e1e` is the follow-up inline fix applied per this review's §8 recommendation, ahead of the merge-readiness pass)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Git merged all four branch files (`format_number.py`, `detect_number.py`, `test_action_format_number.py`, `test_action_detect_number.py`) against main's doc/config additions without conflict. The `docs/known_identifiers.md` file is absent from this branch entirely, so no conflict arose there.

**Pytest on merged state:** 352 passing, 0 failing (6 skipped, 3 xfailed — pre-existing)

**prek:** `pre-commit` binary not available in worktree venv path; ruff check run directly on branch files — green. The original review confirmed all 8 prek hooks passed at d0c75d2; the 1889e1e fix is a docstring-only change that cannot introduce lint failures.

**Drift / observations:**
- The style-modes gap fix (commit `1889e1e`) was already applied before this merge-readiness pass — the §8 required doc edit from the prior review is done. No outstanding issues remain.
- `coerce_value` (bare `WFTextTokenAttachment`) usage in both actions is consistent with corpus evidence and with sibling `format_date.py` on main. No drift.
- Main added CLAUDE.md, `.claude/rules/action-modelling.md`, and several other review batch files — none touch the schema or test surface of this branch.
- `docs/known_identifiers.md` is not present on this branch; it is regenerated deterministically so identifiers added here will re-appear post-merge.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
