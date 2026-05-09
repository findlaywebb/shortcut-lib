"""Tests for GetLastScreenshot action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.get_last_screenshot  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.get_last_screenshot import GetLastScreenshot
from shortcut_lib.schema.registry import lookup


def test_get_last_screenshot_default_emits_correct_identifier() -> None:
    """to_action_dict carries the correct WFWorkflowActionIdentifier."""
    action = GetLastScreenshot()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.getlastscreenshot"


def test_get_last_screenshot_default_omits_count() -> None:
    """Default invocation omits WFGetLatestPhotoCount — matches two dictionary.xml appearances.

    Both dictionary.xml appearances emit only UUID, confirming that omitting
    the count key is valid wire format for the Apple default.
    """
    action = GetLastScreenshot()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFGetLatestPhotoCount" not in params


def test_get_last_screenshot_count_emitted() -> None:
    """count=N writes WFGetLatestPhotoCount to the params dict."""
    action = GetLastScreenshot(count=3)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetLatestPhotoCount"] == 3


def test_get_last_screenshot_uuid_present() -> None:
    """UUID is always included in WFWorkflowActionParameters."""
    action = GetLastScreenshot(uuid="CCCC-DDDD")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "CCCC-DDDD"


def test_get_last_screenshot_output_name() -> None:
    """output() uses the class default_output_name 'Latest Screenshots'."""
    action = GetLastScreenshot()
    out = action.output()
    assert out.name == "Latest Screenshots"


def test_get_last_screenshot_registered() -> None:
    """GetLastScreenshot is discoverable via the registry."""
    cls = lookup("is.workflow.actions.getlastscreenshot")
    assert cls is GetLastScreenshot


def test_get_last_screenshot_wire_format_equivalence() -> None:
    """Wire format matches dictionary.xml sample (UUID-only params dict).

    combine_screenshots_and_share.xml confirms WFGetLatestPhotoCount as the
    parameter key name; dictionary.xml confirms the no-count wire form.
    """
    fixed_uuid = "3B65B4D7-B153-490C-9D9B-0059FBAC7255"
    action = GetLastScreenshot(uuid=fixed_uuid)
    d = action.to_action_dict()

    assert d == {
        "WFWorkflowActionIdentifier": "is.workflow.actions.getlastscreenshot",
        "WFWorkflowActionParameters": {
            "UUID": fixed_uuid,
        },
    }
