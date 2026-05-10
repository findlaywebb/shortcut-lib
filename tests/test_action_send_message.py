"""Tests for SendMessage action schema.

Wire-format expectations are derived from three decoded samples:
- ``samples/decoded/markup_and_send.xml`` — message body is an ActionOutput ref
- ``samples/decoded/running_late.xml`` — message body is an ActionOutput ref;
  WFSendMessageActionRecipients present with empty WFContactFieldValues
- ``samples/decoded/dictionary.xml`` — two sendmessage invocations; one with
  WFSendMessageContent (ActionOutput ref), one with no content keys (bare action)
"""

from __future__ import annotations

import pytest

import shortcut_lib.schema.actions.send_message  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.send_message import SendMessage
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output, Text

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _params(action: SendMessage) -> dict:
    """Extract WFWorkflowActionParameters from an action."""
    return action.to_action_dict()["WFWorkflowActionParameters"]


# ---------------------------------------------------------------------------
# Test 1 — Basic happy path: plain string message, no recipients
# ---------------------------------------------------------------------------


def test_basic_plain_string_message() -> None:
    """Plain string message lands in WFSendMessageContent as-is; recipients absent."""
    action = SendMessage(message="On my way!")
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.sendmessage"
    params = d["WFWorkflowActionParameters"]
    assert params["WFSendMessageContent"] == "On my way!"
    assert "WFSendMessageActionRecipients" not in params
    assert "UUID" in params


# ---------------------------------------------------------------------------
# Test 2 — Message as Action output → WFTextTokenString envelope
# ---------------------------------------------------------------------------


def test_message_as_action_output() -> None:
    """An Action output in the message slot is wrapped as WFTextTokenString.

    Matches the pattern in markup_and_send.xml (OutputUUID=03D99811…) and
    running_late.xml where the message body is a single ActionOutput ref.
    Apple's runtime reads WFSendMessageContent as WFTextTokenString — a bare
    WFTextTokenAttachment would leave the message field disconnected.
    """
    # Simulate a previous action whose output we chain into the message.
    ref_uuid = "03D99811-2952-439C-8A29-91668C611407"
    markup_output = Output(uuid=ref_uuid, name="Markup Result")
    action = SendMessage(message=markup_output)
    params = _params(action)

    content = params["WFSendMessageContent"]
    assert isinstance(content, dict)
    assert content["WFSerializationType"] == "WFTextTokenString"
    inner = content["Value"]
    assert inner["string"] == "￼"
    attachments = inner["attachmentsByRange"]
    assert list(attachments) == ["{0, 1}"]
    attachment = attachments["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputUUID"] == ref_uuid
    assert attachment["OutputName"] == "Markup Result"


# ---------------------------------------------------------------------------
# Test 3 — Message as Text template
# ---------------------------------------------------------------------------


def test_message_as_text_template() -> None:
    """A Text template in the message slot produces a WFTextTokenString envelope.

    Matches the running_late.xml pattern where the message content is built
    from a previous Text action output.
    """
    delay = NamedVar("Delay")
    body = Text("Running {delay} minutes late", substitutions={"delay": delay})
    action = SendMessage(message=body)
    params = _params(action)

    content = params["WFSendMessageContent"]
    assert content["WFSerializationType"] == "WFTextTokenString"
    inner = content["Value"]
    assert "￼" in inner["string"]
    assert len(inner["attachmentsByRange"]) == 1
    token = next(iter(inner["attachmentsByRange"].values()))
    assert token["Type"] == "Variable"
    assert token["VariableName"] == "Delay"


# ---------------------------------------------------------------------------
# Test 4 — Recipients field pass-through
# ---------------------------------------------------------------------------


def test_recipients_passthrough() -> None:
    """A pre-built WFContactFieldValue dict is passed through verbatim.

    Derived from running_late.xml:3 — the only sample with recipients present.
    The WFContactFieldValues array was empty in that sample (user hadn't
    filled in contacts at shortcut-authoring time).
    """
    recipient_envelope = {
        "Value": {"WFContactFieldValues": []},
        "WFSerializationType": "WFContactFieldValue",
    }
    action = SendMessage(message="Hello!", recipients=recipient_envelope)
    params = _params(action)

    assert params["WFSendMessageActionRecipients"] == recipient_envelope


# ---------------------------------------------------------------------------
# Test 5 — Missing message raises SchemaError
# ---------------------------------------------------------------------------


def test_missing_message_raises() -> None:
    """Omitting message (None) raises SchemaError at construction time."""
    with pytest.raises(SchemaError, match="message"):
        SendMessage()


# ---------------------------------------------------------------------------
# Test 6 — Empty string message raises SchemaError
# ---------------------------------------------------------------------------


def test_empty_message_raises() -> None:
    """Empty-string message raises SchemaError with helpful text."""
    with pytest.raises(SchemaError, match="message"):
        SendMessage(message="")


# ---------------------------------------------------------------------------
# Test 7 — Registry lookup
# ---------------------------------------------------------------------------


def test_send_message_registered() -> None:
    """SendMessage is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.sendmessage")
    assert cls is SendMessage


# ---------------------------------------------------------------------------
# Test 8 — Wire-format equivalence vs markup_and_send.xml
# ---------------------------------------------------------------------------


def test_wire_format_equivalence_markup_and_send() -> None:
    """Validate emitted shape against markup_and_send.xml SendMessage action.

    That action has:
    - UUID: D5558113-E153-4790-9BB9-4D6B01717FC3
    - WFSendMessageContent: WFTextTokenString wrapping OutputUUID 03D99811…
      (OutputName: "Markup Result", Type: ActionOutput)
    - No WFSendMessageActionRecipients
    - No WFSendMessageService (not present in any corpus sample)

    Note: IntentAppDefinition (BundleIdentifier, Name, TeamIdentifier) appears
    in the decoded sample but is a field Apple writes at shortcut-authoring time
    via the Shortcuts UI. Its presence varies across samples — it is absent in
    running_late.xml, confirming the action works without it. The schema
    intentionally does not emit it.
    """
    ref_uuid = "03D99811-2952-439C-8A29-91668C611407"
    markup_output = Output(uuid=ref_uuid, name="Markup Result")
    action = SendMessage(
        message=markup_output,
        uuid="D5558113-E153-4790-9BB9-4D6B01717FC3",
    )
    d = action.to_action_dict()
    params = d["WFWorkflowActionParameters"]

    # Identifier
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.sendmessage"

    # UUID
    assert params["UUID"] == "D5558113-E153-4790-9BB9-4D6B01717FC3"

    # WFSendMessageContent shape
    content = params["WFSendMessageContent"]
    assert content["WFSerializationType"] == "WFTextTokenString"
    assert content["Value"]["string"] == "￼"
    att = content["Value"]["attachmentsByRange"]["{0, 1}"]
    assert att["Type"] == "ActionOutput"
    assert att["OutputUUID"] == ref_uuid
    assert att["OutputName"] == "Markup Result"

    # Recipients and service absent — no keys in sample
    assert "WFSendMessageActionRecipients" not in params


# ---------------------------------------------------------------------------
# Test 9 — Wire-format equivalence vs running_late.xml
# ---------------------------------------------------------------------------


def test_wire_format_equivalence_running_late() -> None:
    """Validate emitted shape against running_late.xml SendMessage action.

    That action has:
    - WFSendMessageActionRecipients: WFContactFieldValue with empty array
    - WFSendMessageContent: WFTextTokenString wrapping OutputUUID 40C0462C…
      (OutputName: "Text", Type: ActionOutput)
    """
    text_uuid = "40C0462C-4B36-4B70-8DEE-7CAED381A497"
    text_output = Output(uuid=text_uuid, name="Text")
    recipient_envelope = {
        "Value": {"WFContactFieldValues": []},
        "WFSerializationType": "WFContactFieldValue",
    }
    action = SendMessage(message=text_output, recipients=recipient_envelope)
    params = _params(action)

    # Content slot
    content = params["WFSendMessageContent"]
    assert content["WFSerializationType"] == "WFTextTokenString"
    att = content["Value"]["attachmentsByRange"]["{0, 1}"]
    assert att["Type"] == "ActionOutput"
    assert att["OutputUUID"] == text_uuid

    # Recipients slot
    recipients = params["WFSendMessageActionRecipients"]
    assert recipients["WFSerializationType"] == "WFContactFieldValue"
    assert recipients["Value"]["WFContactFieldValues"] == []
