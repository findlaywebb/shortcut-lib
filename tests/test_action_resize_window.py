"""Tests for the ResizeWindow action schema."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

import shortcut_lib.schema.actions.resize_window  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.resize_window import ResizeWindow
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
TILE_XML = DECODED / "tile_last_2_windows.xml"
DICTIONARY_XML = DECODED / "dictionary.xml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip UUID and OutputUUID fields so two action dicts are comparable."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    _strip_output_uuids(params)
    return out


def _strip_output_uuids(obj: Any) -> None:
    """Recursively remove OutputUUID keys (they reference other action UUIDs)."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for item in obj:
            _strip_output_uuids(item)


def _load(path: Path) -> dict[str, Any]:
    return plistlib.loads(path.read_bytes())


def _find_all_actions(
    workflow: dict[str, Any], identifier: str
) -> list[dict[str, Any]]:
    """Return all actions matching ``identifier``."""
    return [
        a
        for a in workflow["WFWorkflowActions"]
        if a["WFWorkflowActionIdentifier"] == identifier
    ]


# ---------------------------------------------------------------------------
# Happy-path preset tests
# ---------------------------------------------------------------------------


def test_resize_window_left_half() -> None:
    """Left Half configuration emits WFConfiguration='Left Half'."""
    window_ref = Output(uuid="AABBCCDD-0000-0000-0000-000000000001", name="Windows")
    action = ResizeWindow(window=window_ref, configuration="Left Half")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Left Half"
    assert params["WFWindow"]["WFSerializationType"] == "WFTextTokenAttachment"


def test_resize_window_right_half() -> None:
    """Right Half configuration emits WFConfiguration='Right Half'."""
    window_ref = Output(uuid="AABBCCDD-0000-0000-0000-000000000002", name="Windows")
    action = ResizeWindow(window=window_ref, configuration="Right Half")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Right Half"


def test_resize_window_top_half() -> None:
    """Top Half configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Top Half")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Top Half"


def test_resize_window_bottom_half() -> None:
    """Bottom Half configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Bottom Half")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Bottom Half"


def test_resize_window_top_left_quarter() -> None:
    """Top Left Quarter configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Top Left Quarter")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Top Left Quarter"


def test_resize_window_top_right_quarter() -> None:
    """Top Right Quarter configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Top Right Quarter")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Top Right Quarter"


def test_resize_window_bottom_left_quarter() -> None:
    """Bottom Left Quarter configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Bottom Left Quarter")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Bottom Left Quarter"


def test_resize_window_bottom_right_quarter() -> None:
    """Bottom Right Quarter configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Bottom Right Quarter")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Bottom Right Quarter"


def test_resize_window_fill() -> None:
    """Fill configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Fill")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Fill"


def test_resize_window_center() -> None:
    """Center configuration is accepted and emitted correctly."""
    action = ResizeWindow(configuration="Center")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFConfiguration"] == "Center"


# ---------------------------------------------------------------------------
# Bare invocation (no configuration)
# ---------------------------------------------------------------------------


def test_resize_window_bare_no_configuration() -> None:
    """Bare invocation (window only, no configuration) omits WFConfiguration.

    Confirmed against samples/decoded/dictionary.xml:344 where the
    resizewindow action has WFWindow but no WFConfiguration key.
    """
    window_ref = Output(uuid="AABBCCDD-0000-0000-0000-000000000003", name="Windows")
    action = ResizeWindow(window=window_ref)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFConfiguration" not in params
    assert params["WFWindow"]["WFSerializationType"] == "WFTextTokenAttachment"


def test_resize_window_no_args() -> None:
    """ResizeWindow() with no args emits only UUID — no WFWindow, no WFConfiguration."""
    action = ResizeWindow()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFWindow" not in params
    assert "WFConfiguration" not in params
    assert "UUID" in params


# ---------------------------------------------------------------------------
# WFBringToFront flag
# ---------------------------------------------------------------------------


def test_resize_window_bring_to_front_true() -> None:
    """bring_to_front=True emits WFBringToFront=True."""
    action = ResizeWindow(configuration="Fill", bring_to_front=True)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFBringToFront"] is True


def test_resize_window_bring_to_front_false() -> None:
    """bring_to_front=False emits WFBringToFront=False."""
    action = ResizeWindow(configuration="Fill", bring_to_front=False)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFBringToFront"] is False


def test_resize_window_bring_to_front_omitted_by_default() -> None:
    """bring_to_front defaults to None — WFBringToFront key is absent."""
    action = ResizeWindow(configuration="Left Half")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFBringToFront" not in params


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_resize_window_registered() -> None:
    """ResizeWindow is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.resizewindow")
    assert cls is ResizeWindow


def test_resize_window_identifier() -> None:
    """ResizeWindow.identifier matches the Apple wire identifier."""
    assert ResizeWindow.identifier == "is.workflow.actions.resizewindow"


def test_resize_window_default_output_name() -> None:
    """ResizeWindow.default_output_name is 'Resize Window'."""
    assert ResizeWindow.default_output_name == "Resize Window"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs real samples
# ---------------------------------------------------------------------------


def test_wire_format_tile_left_half() -> None:
    """Schema-emitted Left Half matches tile_last_2_windows.xml first resizewindow.

    Sample path: samples/decoded/tile_last_2_windows.xml, first resizewindow
    (line 47). Expected WFConfiguration='Left Half', WFWindow as
    WFTextTokenAttachment.
    """
    workflow = _load(TILE_XML)
    sample_actions = _find_all_actions(workflow, "is.workflow.actions.resizewindow")
    assert len(sample_actions) >= 1
    sample = sample_actions[0]  # Left Half

    window_ref = Output(uuid="placeholder", name="Item from List")
    built = ResizeWindow(window=window_ref, configuration="Left Half").to_action_dict()

    assert _normalise(built) == _normalise(sample)


def test_wire_format_tile_right_half() -> None:
    """Schema-emitted Right Half matches tile_last_2_windows.xml second resizewindow.

    Sample path: samples/decoded/tile_last_2_windows.xml, second resizewindow
    (line 97). Expected WFConfiguration='Right Half'.
    """
    workflow = _load(TILE_XML)
    sample_actions = _find_all_actions(workflow, "is.workflow.actions.resizewindow")
    assert len(sample_actions) >= 2
    sample = sample_actions[1]  # Right Half

    window_ref = Output(uuid="placeholder", name="Item from List")
    built = ResizeWindow(window=window_ref, configuration="Right Half").to_action_dict()

    assert _normalise(built) == _normalise(sample)


def test_wire_format_dictionary_bare() -> None:
    """Schema-emitted bare form matches dictionary.xml resizewindow.

    Sample path: samples/decoded/dictionary.xml. That instance has WFWindow
    but no WFConfiguration key — bare window-only invocation.
    """
    workflow = _load(DICTIONARY_XML)
    sample_actions = _find_all_actions(workflow, "is.workflow.actions.resizewindow")
    assert len(sample_actions) >= 1
    sample = sample_actions[0]

    window_ref = Output(uuid="placeholder", name="Windows")
    built = ResizeWindow(window=window_ref).to_action_dict()

    assert _normalise(built) == _normalise(sample)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_resize_window_invalid_configuration_raises() -> None:
    """An unrecognised configuration raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Diagonal'"):
        ResizeWindow(configuration="Diagonal")  # ty: ignore[invalid-argument-type]  # intentional bad value


def test_resize_window_invalid_configuration_typo_raises() -> None:
    """A close-but-wrong configuration string raises SchemaError."""
    with pytest.raises(SchemaError, match="'left half'"):
        ResizeWindow(configuration="left half")  # ty: ignore[invalid-argument-type]  # intentional bad value
