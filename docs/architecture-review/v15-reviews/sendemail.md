# Review: v15/model-sendemail

**Action:** `is.workflow.actions.sendemail`
**Reviewer:** automated (Claude Sonnet 4.6)
**Date:** 2026-05-09
**Head:** 7459b8b

---

## 1. Verdict

LGTM. The schema is correctly grounded in the corpus, the V1 punts are well-reasoned, the equivalence tests are honest about what they skip and why. One minor docstring inconsistency with sendmessage on optional vs required fields; no correctness issues.

---

## 2. Test result

11/11 passed in 0.11 s. All pre-commit hooks pass (ruff lint, ruff format, ty, uv-lock).

```
PASSED test_send_email_basic
PASSED test_send_email_identifier
PASSED test_send_email_omits_none_fields
PASSED test_send_email_show_compose_sheet_true
PASSED test_send_email_show_compose_sheet_false
PASSED test_send_email_body_output_ref_wraps_as_text_token_string
PASSED test_send_email_subject_output_ref_wraps_as_text_token_string
PASSED test_send_email_to_passthrough
PASSED test_send_email_registered
PASSED test_send_email_wire_format_dictionary_body_only
PASSED test_send_email_wire_format_email_last_image_body_and_toggle
```

---

## 3. What landed

- **4 modelled params:** `body` (`WFSendEmailActionInputAttachments`, WFTextTokenString), `subject` (`WFSendEmailActionSubject`, WFTextTokenString), `to` (`WFSendEmailActionToRecipients`, raw pass-through), `show_compose_sheet` (bool)
- **All fields optional** — empty `SendEmail()` opens a blank Mail compose window; matches the bare-action appearance in `dictionary.xml` (two entries with only a body WFTextTokenString, no subject or sheet toggle)
- **11 tests:** 5 construction/unit tests, 2 coerce-text-field slot tests, 1 pass-through test, 1 registry test, 2 wire-format equivalence tests pinned to real corpus samples
- **71 lines** in `send_email.py`, **254 lines** in `test_action_send_email.py`

---

## 4. Recipient encoding inference — sound or needs-sample flag?

The key `WFSendEmailActionToRecipients` was **inferred, not observed**. None of the three corpus appearances carry a recipients field. This is confirmed by `observed_envelope_types.json`, which records only `WFSendEmailActionInputAttachments` and `WFSendEmailActionSubject` for this action — no recipients slot at all.

The inference is plausible by analogy with sendmessage (`WFSendMessageActionRecipients`) but unverified. The naming pattern `WF<Action>Action<Field>` fits Apple's convention across both actions, so the guessed key name is reasonable.

**Assessment:** the handling is correct for V1. The inferred key is not emitted unless the caller explicitly passes a `to` value, so the risk is limited to callers who consciously opt in to the unverified slot. The docstring and test for `to` both say "inferred, not sample-verified" with sufficient clarity.

**Recommendation:** track as a V1.5+ follow-up with a "needs sample" note. If a corpus sample with populated recipients ever surfaces, the key name and envelope shape should be verified before the slot is marked stable. The module docstring already contains the right caveat; no change needed before merge.

---

## 5. Property-aggrandizement strip in equivalence test — sound?

`test_send_email_wire_format_email_last_image_body_and_toggle` pops `WFSendEmailActionSubject` from the sample copy before comparing, because the sample subject uses a `WFPropertyVariableAggrandizement` (a property accessor extracting the `Name` attribute from an output). The test docstring calls this out explicitly:

> "Aggrandizements are beyond V1 modelling; this test validates only the body and show_compose_sheet fields and skips the subject comparison."

This is the right call. The strip is well-documented:

- The test module header lists `WFSendEmailActionSubject` as an observed parameter with a specific corpus location
- The test docstring explains precisely why subject is excluded and what the omitted envelope contains
- A separate unit test (`test_send_email_subject_output_ref_wraps_as_text_token_string`) confirms the subject slot emits the correct `WFSerializationType` when given a plain `Output` reference — the gap is specifically aggrandizement chaining, not subject handling in general

The approach is honest: the test verifies what the schema can model and names what it cannot. This is preferable to either skipping the test entirely or writing an equivalence test that silently masks the aggrandizement.

Aggrandizements warrant a future schema layer of their own. No issue here.

---

## 6. `coerce_text_field` choices — confirmed against observed envelopes

`observed_envelope_types.json` confirms:

| Param key | Observed envelope | Count | Samples |
|---|---|---|---|
| `WFSendEmailActionInputAttachments` | `WFTextTokenString` | 3 | all 3 corpus appearances |
| `WFSendEmailActionSubject` | `WFTextTokenString` | 1 | `email_last_image.xml:1` |

Both slots are 100% `WFTextTokenString` across all observations. `coerce_text_field` is the correct choice for both. No `WFTextTokenAttachment` ambiguity.

The `show_compose_sheet` field emits a bare boolean — the corpus value is `<true/>` in `email_last_image.xml`, which is what the schema produces. Correct.

---

## 7. All-fields-optional choice

`SendEmail()` with no arguments emits no params beyond the identifier. This is validated by two corpus appearances: `dictionary.xml` index 174 and 313 both carry only `WFSendEmailActionInputAttachments` (a body reference), with no subject, no recipients, and no compose-sheet toggle.

More relevantly, `email_last_image.xml` carries a `ShowComposeSheet = true` flag, which means the empty-params case (no `ShowComposeSheet`) maps to Apple's default — showing the compose sheet. This is consistent with `show_compose_sheet=None` omitting the key and Apple defaulting to show-the-sheet behaviour.

Contrast with `SendMessage`, which marks `message` as required and raises `SchemaError` on `None`. That difference is appropriate: a message with no body is vacuous; an email compose window with no pre-filled content is a valid and common use case (open blank compose, let the user fill it in). The all-optional design is the right call here.

---

## 8. Cross-reference with sendmessage — docstring and style consistency

Both actions follow the same structural pattern: `@register @dataclass`, `ClassVar[str]` identifier, `ParamValue` slots, `_params()` building `out: dict[str, Any]`. Style is consistent.

Minor divergence worth noting:

1. **Docstring usage section.** `SendMessage` provides a code block with a minimal example and a full example in the class docstring. `SendEmail` provides no usage examples. Not a correctness issue, but the sendmessage convention is more user-friendly and could be followed in a follow-up pass.

2. **Module-level comment vs inline comment.** `SendMessage` places its recipient-encoding rationale in a module-level block comment above `@register`. `SendEmail` places the equivalent explanation inside the class docstring. Both approaches are readable; the sendmessage pattern keeps the class docstring focused on the public API. Minor style inconsistency, not a problem.

3. **`coerce_value` import placement.** `send_email.py` imports `coerce_value` inside `_params()` (deferred import). `send_message.py` imports everything at module level. The deferred import in `send_email.py` is unnecessary — `coerce_value` is already available at module scope from `shortcut_lib.schema.base` alongside `coerce_text_field`. This is a nit; it works correctly but the deferred form is inconsistent with the rest of the codebase.

4. **Jellycore coverage.** `jellycore_facts.json` has no entry for `is.workflow.actions.sendemail` — the action is absent from Jellycore's action list entirely. `is.workflow.actions.sendmessage` also has a data quality issue (its entry is attached to `getepisodesforpodcast`'s identifier). Neither issue originates in this PR; both were pre-existing. No action needed here.

---

## 9. Issues

**Minor — deferred import of `coerce_value` inside `_params()`**

`send_email.py` line 59:
```python
from shortcut_lib.schema.base import coerce_value
```
is inside `_params()`. All other `send_email.py` imports are at module level. The import should be hoisted to the top of the file alongside `coerce_text_field`. This is cosmetic; it does not affect correctness or performance at this call frequency.

**Minor — no usage example in class docstring**

`SendMessage` includes a minimal and a full example in its class docstring. `SendEmail` does not. Given the `to` field's unverified status, a note in the docstring showing the plain-string case (body only) would improve discoverability.

Neither issue warrants blocking the merge.

---

## 10. Merge recommendation

**Merge as-is.** All 11 tests pass, pre-commit is clean, corpus grounding is verified, and V1 punts are clearly documented. The deferred import and missing usage example can be addressed in a follow-up. Recipient encoding should be tracked as a "needs sample" follow-up but does not block merge.
