# Review: v15/model-getdistance — `is.workflow.actions.getdistance`

**Reviewer:** Claude (Sonnet 4.6)
**Date:** 2026-05-10
**Branch:** `v15/model-getdistance` (head: `5a26095`)

---

## 1. Verdict

**Approve.** The implementation is tight, honest about its evidence base, and well-tested. The single question worth discussing before merge is field minimalism (see §6) — but the agent made a defensible call and the review position below agrees.

---

## 2. Test result + prek

```
15 passed in 0.10s
```

All prek hooks pass: trailing-whitespace, EOF, YAML, large-file, ruff lint, ruff format, uv-lock, ty — all green. No issues.

---

## 3. What landed

| File | Lines |
|---|---|
| `src/shortcut_lib/schema/actions/get_distance.py` | 77 |
| `tests/test_action_get_distance.py` | 232 |

Two new files, no modifications to existing code. Diff is self-contained.

---

## 4. Wire-key + envelope verification

**Wire-key distinction confirmed.** Both corpus occurrences use `WFGetDistanceDestination`, not `WFDestination`. The sibling `gettraveltime` action uses `WFDestination` (confirmed in the same corpus). These are distinct keys on distinct actions — the agent called this correctly.

Corpus evidence (both samples identical in structure):

```xml
<key>WFGetDistanceDestination</key>
<dict>
    <key>Value</key>
    <dict>
        <key>OutputName</key><string>Addresses</string>
        <key>OutputUUID</key><string>…</string>
        <key>Type</key><string>ActionOutput</string>
    </dict>
    <key>WFSerializationType</key>
    <string>WFTextTokenAttachment</string>
</dict>
```

**Envelope choice confirmed.** Both samples serialise as `WFTextTokenAttachment` (bare attachment, no `WFTextTokenString` wrapper). `coerce_value` is the correct helper — `coerce_text_field` would produce the wrong envelope shape. The implementation matches.

**Origin omission confirmed.** Neither corpus sample contains `WFFromAddress`, `WFGetDistanceFrom`, `WFFromLocation`, or any other origin-override key. Current-location-as-implicit-origin is the only pattern observed. The docstring and the negative-key guard test (`assert "WFFromAddress" not in params`) both reflect this accurately.

---

## 5. Source-attribution audit

The docstring explicitly states which indices in `dictionary.xml` ground each claim (112, 317). The jellycore null claim is accurate — `jq '.["is.workflow.actions.getdistance"]' data/jellycore_facts.json` returns `null`. No speculative claims are presented as corpus-confirmed. Attribution quality is high.

The inline comment in `_params` notes the `WFTextTokenString` distinction: "not a WFTextTokenString wrapper, mirroring the WFDestination slot in the sibling gettraveltime action." That cross-reference is useful and correct.

---

## 6. Field minimalism question — position

**The minimalist call is correct. Do not speculatively add `WFDistanceUnit` or `WFGetDistanceMode`.**

The corpus has 2 samples, both identical in structure, both showing only `WFGetDistanceDestination`. There is no evidence for unit or mode keys. Adding unobserved fields as `Literal` types would:

1. Risk guessing wrong key names (Apple is inconsistent — compare `WFDestination` vs `WFGetDistanceDestination` on sibling actions).
2. Pollute the public API with fields that may not exist or may behave differently than assumed.
3. Undermine the corpus-grounded discipline the library is building.

A "speculative — not corpus-confirmed" disclaimer on a public field provides false confidence: users will use it, it may silently produce malformed shortcuts, and the disclaimer won't stop that.

The right response to missing field coverage is: add a `# TODO: corpus gap — WFDistanceUnit / WFGetDistanceMode not observed` comment if desired, ship what's confirmed, and revisit when more samples or first-party documentation surface. The docstring already does the equivalent of this clearly.

---

## 7. Doc quality

**Score: 5/5.**

The class docstring covers all four areas that matter for this library:

- What the action does (straight-line distance, current location as origin).
- The parameter key and *why* it differs from the sibling (`WFGetDistanceDestination` vs `WFDestination` — not assumed, explained).
- The envelope type and which coercion helper follows from it.
- What was deliberately omitted and why, with a clear invitation to add when evidence exists.

The Args section correctly describes the `None`-omission behaviour and what Shortcuts.app does in that case. The "Source verification" block inside the docstring is a strong pattern — keeps the derivation co-located with the code.

---

## 8. Issues

None. No pre-existing issues surfaced in adjacent code. No schema, naming, or structural concerns.

---

## 9. Merge recommendation

**Merge as-is.** Tests pass, prek clean, wire key confirmed against corpus, envelope shape verified, jellycore null cross-checked, no speculative fields, documentation is exemplary. This is a clean, honest, minimal action model.

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `5a26095` (matches _SUMMARY.md record `5a26095`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts; the review file (`docs/architecture-review/v15-reviews/getdistance.md`) lives on main (added after the branch was cut) and merges in cleanly.

**Pytest on merged state:** 346 passing, 0 failing (6 skipped, 3 xfailed)

**prek:** green (trailing-whitespace, EOF, YAML, large-file, ruff lint, ruff format, uv-lock, ty — all passed)

**Drift / observations:**
- Branch HEAD `5a26095` matches the recorded SHA in the task brief. No drift.
- The review file was committed to main after the branch was cut; it does not appear in the branch diff but merges in cleanly.
- No sibling actions on main contradict `WFGetDistanceDestination` — the `gettraveltime` review on main explicitly calls out the wire-key distinction (`WFDestination` vs `WFGetDistanceDestination`), consistent with this branch's claims.
- Test count grew from 15 (original branch review) to 346 on merged state, reflecting main advancing with other batch merges. All green.
- `v15/model-getdistance` is not yet listed in `_SUMMARY.md` (it post-dates the last recorded batch). No action required here; the summary update is a main-thread task.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
