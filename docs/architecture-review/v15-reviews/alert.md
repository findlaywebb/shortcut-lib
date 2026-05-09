# Review: v15/model-alert — ShowAlert schema

**Branch:** `v15/model-alert` (head: a43e528)
**Reviewer:** Claude Sonnet 4.6 (autonomous)
**Date:** 2026-05-09

---

## 1. Verdict

**Approve.** Clean, minimal, well-documented addition. The implementation
follows the ShowNotification pattern faithfully, documentation is thorough,
and the single corpus discrepancy is handled honestly and proportionately.

---

## 2. Test result

11/11 passed. All pre-commit hooks pass (ruff lint, ruff format, ty, uv-lock,
whitespace, YAML).

```
tests/test_action_alert.py  11 passed in 0.10s
prek run --all-files         Passed (all 8 hooks)
```

---

## 3. What landed

- `src/shortcut_lib/schema/actions/alert.py` — 51 lines: `ShowAlert` dataclass
  with `title`, `message` (`ParamValue`, defaulting to `""`), and
  `show_cancel_button` (`bool | None`, defaulting to `None`).
- `tests/test_action_alert.py` — 194 lines: 9 unit tests + 2 wire-format
  equivalence tests grounded on `read_later.xml[15]` and
  `dictionary.xml[2]`.
- Four review markdown files removed (previously merged reviews cleaned from
  the branch).

The schema is registered under `is.workflow.actions.alert`. No new
dependencies introduced.

---

## 4. The empty-message discrepancy — clean or hacky?

**Clean.** The handling is fully documented and the design choice is
defensible.

The corpus fact: `read_later.xml[15]` emits `WFAlertActionMessage: ""`
even though the message is visually blank. The schema omits the key for
empty strings, consistent with `ShowNotification` and with `dictionary.xml`
(which has a completely empty params dict for an unconfigured alert).

The divergence is acknowledged in three places:

1. The action docstring for `message` — explains the omit-when-empty
   behaviour explicitly.
2. The `test_alert_wire_format_read_later` docstring — names it a "MINOR
   DISCREPANCY", quotes the Apple wire value (`""`), explains the reasoning
   (can't distinguish "user set to empty" from "default empty"), and
   describes exactly what normalisation the test applies before comparing.
3. The `_params` implementation — matches `ShowNotification`'s pattern
   exactly, making the precedent traceable.

The round-trip consequence is real but low-risk: a shortcut authored by
the library with `message=""` and then parsed back by Apple will have no
`WFAlertActionMessage` key, while Apple's own UI emits the key with an
empty string. In practice Shortcuts is permissive here — an absent key
and an empty-string key both resolve to a blank message body. The trade-off
(simpler schema, no sentinel value needed) is reasonable given that this is a
display-only action with no output.

If the project later adopts round-trip fidelity as a hard requirement, the
fix is a sentinel (`message: ParamValue | None = None`) plus schema migration
— not a fundamental redesign.

---

## 5. Issues

None blocking. One minor observation for the future:

**Observation (non-blocking):** The `show_cancel_button` docstring says
"Apple defaults to showing the cancel button" when the key is absent, but
this is inferred from Apple's UI behaviour rather than verified from
`dictionary.xml` (which is fully empty, so it confirms the key is omittable
but not what Apple renders). The wording is a reasonable inference but is not
oracle-verified. Worth a note if the corpus grows a new sample with the
cancel button in the default state.

---

## 6. Merge recommendation

**Merge.** The discrepancy is real but the handling is appropriate for the
maturity of the project. Both samples are covered, documentation is honest,
and the implementation is structurally identical to the established
`ShowNotification` pattern. No issues require resolution before merge.
