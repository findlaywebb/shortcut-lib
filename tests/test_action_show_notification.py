"""Tests for ShowNotification action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.show_notification  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Text


def test_notification_basic_strings() -> None:
    """Plain string title and body land in the right WF keys."""
    action = ShowNotification(title="Done", body="All finished.")
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.notification"
    params = d["WFWorkflowActionParameters"]
    assert params["WFNotificationActionTitle"] == "Done"
    assert params["WFNotificationActionBody"] == "All finished."
    assert "WFNotificationActionSound" not in params


def test_notification_with_templated_title() -> None:
    """Text(...) in the title slot renders as a WFTextTokenString envelope."""
    var = NamedVar("Base")
    body = Text("Voice note pushed: {var}", substitutions={"var": var})
    action = ShowNotification(title="Voice Note → GitHub", body=body)
    d = action.to_action_dict()
    params = d["WFWorkflowActionParameters"]

    # Title is a plain string — emitted as-is.
    assert params["WFNotificationActionTitle"] == "Voice Note → GitHub"

    # Body is a Text token — envelope shape must match Apple's wire format.
    body_param = params["WFNotificationActionBody"]
    assert body_param["WFSerializationType"] == "WFTextTokenString"
    inner = body_param["Value"]
    assert "string" in inner
    assert "attachmentsByRange" in inner
    # The substituted placeholder (￼) replaces {var} in the string.
    assert "￼" in inner["string"]
    # There is one attachment keyed by an NSRange string.
    assert len(inner["attachmentsByRange"]) == 1
    token = next(iter(inner["attachmentsByRange"].values()))
    assert token["Type"] == "Variable"
    assert token["VariableName"] == "Base"


def test_notification_play_sound_flag() -> None:
    """play_sound=True/False emits WFNotificationActionSound; None omits it."""
    action_on = ShowNotification(title="Hi", play_sound=True)
    params_on = action_on.to_action_dict()["WFWorkflowActionParameters"]
    assert params_on["WFNotificationActionSound"] is True

    action_off = ShowNotification(title="Hi", play_sound=False)
    params_off = action_off.to_action_dict()["WFWorkflowActionParameters"]
    assert params_off["WFNotificationActionSound"] is False

    action_default = ShowNotification(title="Hi")
    params_default = action_default.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNotificationActionSound" not in params_default


def test_notification_registered() -> None:
    """ShowNotification is discoverable via the registry."""
    cls = lookup("is.workflow.actions.notification")
    assert cls is ShowNotification


def test_show_notification_omits_empty_title() -> None:
    action = ShowNotification(title="", body="Some body")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNotificationActionTitle" not in params
    assert params["WFNotificationActionBody"] == "Some body"


def test_show_notification_omits_empty_body() -> None:
    action = ShowNotification(title="Hello", body="")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNotificationActionTitle"] == "Hello"
    assert "WFNotificationActionBody" not in params


def test_show_notification_empty_title_and_body_both_omitted() -> None:
    """Empty string for both title and body omits both WF keys entirely.

    ShowNotification guards each field with ``if coerced != ""``, so an
    empty string and a missing value (None would bypass coerce_text_field)
    both result in omission. The params dict only carries UUID.
    """
    params = ShowNotification(title="", body="").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "WFNotificationActionTitle" not in params
    assert "WFNotificationActionBody" not in params
