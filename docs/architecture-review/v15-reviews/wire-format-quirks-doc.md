# Review: `v15/wire-format-quirks-doc`

**Branch:** `v15/wire-format-quirks-doc`
**Commit:** `d731fc7`
**Reviewer:** Sonnet (deep review A follow-up)
**Date:** 2026-05-09

## Summary

Pure documentation branch. Adds `docs/wire-format-quirks.md` — a 323-line
LLM-author reference cataloguing:

- 17 bare-key actions (§1)
- 1 confirmed hyphenated key (`Show-text`) + contrast (§2)
- 23 wire-key vs Python field name mismatches (§3)
- 5 slot-envelope conventions (`WFTextTokenString`, `WFTextTokenAttachment`,
  `WFDictionaryFieldValue`, `WFContactFieldValue`, `WFQuantityFieldValue`) (§4)
- Default-omission patterns and known fidelity losses (§5)
- Action-specific quirks (`RawAction`, `If` wrapping, `IntentAppDefinition`,
  `AddNewReminder.alert_enabled`, `DownloadURL.ShowHeaders`) (§6)
- Corpus-over-Jellycore discipline with two concrete counter-examples (§7)

No schema changes, no test changes. No Python files touched.

## Verdict

**GREEN.** Every claim in the doc is traceable to a corpus sample, oracle
entry, or existing action implementation. Source-confidence labels are
consistently applied. The doc fills a genuine gap: agents previously had to
rediscover these conventions per-action, causing repeated mistakes (wrong WF
prefix, wrong envelope, wrong key capitalisation).

## Concerns / follow-ups

- `v15/model-system-controls` and `v15/model-maps` have post-branch findings
  to promote into this doc (dual-envelope `dnd.set` example for §4; map-family
  key-inconsistency table). These are enhancements, not corrections — add on
  merge.
- §5 `count / WFCountType` row notes "always emit" but §1 oracle entry says
  `combine_screenshots_and_share.xml` writes it while `dictionary.xml` omits
  it. The fidelity delta is documented honestly; no fix needed.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `d731fc7` (matches _SUMMARY.md record `d731fc7`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: no conflicts; `docs/wire-format-quirks.md` is a new file not
  touched by any main-branch commit.

**Pytest on merged state:** 330 passed, 6 skipped, 3 xfailed, 8 warnings in 16.48s

**prek:** skipped (pure markdown branch; no Python files; not worth the run)

**Drift / observations:**
- main has advanced 21 commits since branch cut. All additions are new action
  schemas and review files — none touch `docs/wire-format-quirks.md`.
- `v15/model-system-controls` review (now on main) recommends adding a
  concrete dual-envelope row for `dnd.set` `Time`/`Event` to §4 or §6.
  The current doc already names both slots in §1 bare-keys table and §4's
  `WFTextTokenString` table. The dual-envelope angle (same UUID, different
  envelope, confirmed in `start_pomodoro.xml`) is the strongest in-corpus
  example and should be promoted to §6 on merge.
- `v15/model-maps` review (now on main) recommends promoting the map-family
  key-inconsistency table (`WFDestination` / `WFGetDistanceDestination` /
  `WFInput`) to this doc. Not currently present; add to §1 or a new §8 on
  merge.
- Both of the above are doc enhancements, not corrections. Branch is not at
  fault for not knowing future findings.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none. Pure doc branch, clean merge, all tests green.
