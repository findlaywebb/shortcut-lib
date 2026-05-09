"""Tests for GetLastPhoto action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.get_last_photo  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.get_last_photo import GetLastPhoto
from shortcut_lib.schema.registry import lookup


def test_get_last_photo_default_emits_correct_identifier() -> None:
    """to_action_dict carries the correct WFWorkflowActionIdentifier."""
    action = GetLastPhoto()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.getlastphoto"


def test_get_last_photo_default_omits_count() -> None:
    """Default invocation omits WFGetLatestPhotoCount — matches all three corpus appearances.

    email_last_image.xml and both dictionary.xml appearances emit only UUID,
    confirming that omitting the count key is the wire format for Apple's default.
    """
    action = GetLastPhoto()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFGetLatestPhotoCount" not in params


def test_get_last_photo_count_emitted() -> None:
    """count=N writes WFGetLatestPhotoCount to the params dict."""
    action = GetLastPhoto(count=5)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetLatestPhotoCount"] == 5


def test_get_last_photo_uuid_present() -> None:
    """UUID is always included in WFWorkflowActionParameters."""
    action = GetLastPhoto(uuid="AAAA-BBBB")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "AAAA-BBBB"


def test_get_last_photo_output_name() -> None:
    """output() uses the class default_output_name 'Latest Photos'."""
    action = GetLastPhoto()
    out = action.output()
    assert out.name == "Latest Photos"


def test_get_last_photo_registered() -> None:
    """GetLastPhoto is discoverable via the registry."""
    cls = lookup("is.workflow.actions.getlastphoto")
    assert cls is GetLastPhoto


def test_get_last_photo_wire_format_equivalence() -> None:
    """Wire format matches email_last_image.xml sample (UUID-only params dict)."""
    fixed_uuid = "7D446437-212B-42A8-918B-7E04A1CA00AA"
    action = GetLastPhoto(uuid=fixed_uuid)
    d = action.to_action_dict()

    assert d == {
        "WFWorkflowActionIdentifier": "is.workflow.actions.getlastphoto",
        "WFWorkflowActionParameters": {
            "UUID": fixed_uuid,
        },
    }
