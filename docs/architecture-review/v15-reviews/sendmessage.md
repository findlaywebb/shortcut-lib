# Review: v15/model-sendmessage

**Action:** `is.workflow.actions.sendmessage`
**Reviewer:** automated (Claude Sonnet 4.6)
**Date:** 2026-05-09
**Head:** 2453ab2

---

## 1. Verdict

LGTM with one minor flag worth noting. The schema is correct, the corpus grounding is solid, and the V1 punt on recipients is well-reasoned and documented. The `IntentAppDefinition` exclusion is defensible but carries a nuance the agent's comment understates — see §5.

---

## 2. Test result

9/9 passed in 0.09 s.

```
PASSED test_basic_plain_string_message
PASSED test_message_as_action_output
PASSED test_message_as_text_template
PASSED test_recipients_passthrough
PASSED test_missing_message_raises
PASSED test_empty_message_raises
PASSED test_send_message_registered
PASSED test_wire_format_equivalence_markup_and_send
PASSED test_wire_format_equivalence_running_late
```

`pre-commit` binary is not installed in the worktree environment. Ruff check and format-check were run directly (`uv run ruff check` / `uv run ruff format --check`) — both clean for the two new files.

---

## 3. What landed

- **2 modelled params:** `message` (`WFSendMessageContent`, WFTextTokenString slot), `recipients` (`WFSendMessageActionRecipients`, raw pass-through)
- **9 tests:** 4 construction/roundtrip tests, 2 validation/error tests, 1 registry test, 2 wire-format equivalence tests pinned to `markup_and_send.xml` and `running_late.xml`
- **94 lines** in `send_message.py`, **240 lines** in `test_action_send_message.py`

---

## 4. Sample-grounding verification

Agent reported 5 corpus appearances across 3 files. Confirmed:

| Sample file | Count | Notes |
|---|---|---|
| `dictionary.xml` | 3 | Lines 2993, 6202, 6260 |
| `markup_and_send.xml` | 1 | Line 32 |
| `running_late.xml` | 1 | Line 115 |

**Total: 5.** Distribution matches the agent's claim exactly.

The three `dictionary.xml` appearances were inspected individually:
- **2993:** `IntentAppDefinition` (com.apple.MobileSMS) + `WFSendMessageContent` (ActionOutput) — standard message to Apple Messages
- **6202:** `IntentAppDefinition` (com.apple.MobileSMS) + no content body — bare action, no WFSendMessageContent present (UUID 86116406)
- **6260:** `IntentAppDefinition` (com.microsoft.Outlook) + no content keys — sendmessage routed through Outlook, bare params

Notable: the appearance at line 6260 routes through **Microsoft Outlook** (TeamIdentifier `UBF8T346G9`), not Apple Messages. This is the `WFSendMessageService` story in practice — the `IntentAppDefinition` is how Apple indicates which messaging app to use. That the agent conflates "service selector" with `WFSendMessageService` is worth tracking; see §5.

`WFSendMessageService` confirmed absent in all 5 corpus appearances and in the full samples directory.

---

## 5. Schema-gap punts — were they the right calls?

### `WFSendMessageService` — correct to omit

Absent from all 5 corpus samples. Not modelling is the right V1 call. The key presumably exists in Shortcuts' internal action definition for routing between Messages vs WhatsApp vs Signal, but there is no evidence of it being emitted by user-authored shortcuts in the corpus. Flag for follow-up if a real sample surfaces with it populated.

### `WFContactFieldValue` pass-through — correct, and well-documented

The only recipients sample (`running_late.xml`) has an empty `WFContactFieldValues` array, giving no signal on the populated wire format. Passing through a raw dict is the right V1 choice. The module-level note and docstring together make it clear: the format is unverified, callers pass a pre-captured wire dict, and a typed helper is deferred to a Batch-4 follow-up. That's a clean handoff.

### `IntentAppDefinition` exclusion — correct direction, but the comment undersells the nuance

The agent's test comment says "Apple writes this at runtime" which is partially accurate but misleading. The corpus shows:

- `running_late.xml`: `IntentAppDefinition` is **absent** — Apple did not inject it in this shortcut
- `markup_and_send.xml` and all 3 `dictionary.xml` samples: `IntentAppDefinition` **is present**

So `IntentAppDefinition` is not purely an import-time injection — it appears in authored shortcuts, and its presence varies. The more accurate read: it is an Apple-managed internal field whose value Apple inserts or infers when the shortcut is saved via the Shortcuts UI. Emitting it from the schema would require knowing the target app's bundle ID and team identifier, which is out of scope for V1. Not emitting it is correct because Apple will either inject it on import or leave it absent (as in `running_late.xml`) without breaking the action.

This differs from `AppIntentDescriptor`, which belongs to third-party App Intents and must be emitted by the schema (the schema for those actions — iBooks, speak text, set clipboard — does include it). The naming is confusingly similar but they serve different purposes. The test comment in `test_wire_format_equivalence_markup_and_send` should be updated from "Apple writes this at runtime" to something like: "Apple injects or omits this field when saving via the Shortcuts UI; not emitted by the schema — the action works without it (confirmed by running_late.xml)."

Functionally this is correct. It is a documentation issue, not a correctness issue.

---

## 6. Issues

**Minor — test comment is imprecise about `IntentAppDefinition` injection semantics**

`test_wire_format_equivalence_markup_and_send` says:

> `IntentAppDefinition` (BundleIdentifier, Name, TeamIdentifier) appears in the decoded sample but is a system-injected field Apple adds at runtime; the schema does not emit it.

"At runtime" implies the runtime adds it during execution. What actually happens is Apple writes it at **shortcut-authoring time** (via Shortcuts.app), and the field is absent in some authored shortcuts (see `running_late.xml`). The action works in both cases. The comment should read: "Apple writes this at shortcut-authoring time; its presence varies across samples (absent in running_late.xml) and the schema intentionally does not emit it."

This is purely a clarity issue for future LLM authors reading the test.

---

## 7. Merge recommendation

**Merge as-is.** The imprecise comment on `IntentAppDefinition` does not affect correctness and can be tightened in a follow-up pass. All 9 tests pass; ruff is clean; corpus grounding is verified.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `b8f5eb1`)

**Branch HEAD:** `b8f5eb1` (diverges from _SUMMARY.md record `2453ab2` — one inline correction commit added)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts; `docs/known_identifiers.md` did not conflict (main version already incorporates the sendmessage identifier and the regen delta).

**Pytest on merged state:** 339 passing, 0 failing, 7 skipped, 3 xfailed

**prek:** skipped (pre-commit binary not installed in worktree; ruff lint and ruff format verified clean via hooks at commit time — both passed on the inline-fix commit)

**Drift / observations:**
- Main has advanced 27 commits since this branch was cut; no new actions were added that contradict sendmessage's wire-key conventions or envelope choices.
- `WFSendMessageContent` (WFTextTokenString) and `WFSendMessageActionRecipients` (raw pass-through) remain consistent with sibling action patterns on main.
- The `v15-reviews/` directory did not exist in the worktree (branch predates its introduction on main); the review file was restored from `main` before appending this section.

**Minor corrections applied:**
- `tests/test_action_send_message.py:176-179` — tightened `IntentAppDefinition` test comment from "Apple adds at runtime / Shortcuts runtime populates it on import" to the accurate framing: Apple writes at shortcut-authoring time; presence varies across samples (absent in running_late.xml). (commit `b8f5eb1`)

**Concerns for higher-tier review:**
- none
