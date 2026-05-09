"""Unit tests for the Share schema action."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.share import Share
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
DAILY_STANDUP = DECODED / "daily_standup.xml"
COMBINE = DECODED / "combine_screenshots_and_share.xml"


# ---------------------------------------------------------------------------
# Helpers (mirrors test_wire_format_equivalence.py conventions)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file."""
    return plistlib.loads(path.read_bytes())


def _find_action(workflow: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return the first action matching ``identifier`` or raise."""
    for action in workflow["WFWorkflowActions"]:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action
    raise KeyError(f"No action with identifier {identifier!r} in sample")


def _strip_ref_uuids(obj: Any) -> None:
    """Recursively strip reference UUIDs so non-deterministic IDs don't drive comparisons.

    Strips both ``OutputUUID`` (action-output references) and ``VariableUUID``
    (named-variable references).  Both are author-time UUIDs that the schema
    cannot reproduce deterministically — ``NamedVar`` omits ``VariableUUID``
    by design, just as ``Output`` references strip ``OutputUUID`` on the sample
    side during normalisation.
    """
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        obj.pop("VariableUUID", None)
        for v in obj.values():
            _strip_ref_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_ref_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic fields (UUID, CustomOutputName, OutputUUID, VariableUUID)."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_ref_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Happy-path / field-presence tests
# ---------------------------------------------------------------------------


def test_share_identifier() -> None:
    """Share emits the correct WFWorkflowActionIdentifier."""
    action = Share()
    assert (
        action.to_action_dict()["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.share"
    )


def test_share_with_string_input() -> None:
    """A literal string input is forwarded verbatim as WFInput."""
    action = Share(input="Hello, world!")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFInput"] == "Hello, world!"


def test_share_with_action_input() -> None:
    """Passing an Action chains its output reference into WFInput.

    coerce_value on an Action produces a WFTextTokenAttachment envelope
    pointing at the action's UUID.
    """
    source = GetText(text="report body")
    action = Share(input=source)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["Type"] == "ActionOutput"
    assert wf_input["Value"]["OutputName"] == "Text"  # GetText.default_output_name
    assert wf_input["Value"]["OutputUUID"] == source.uuid


def test_share_with_named_var() -> None:
    """A NamedVar reference is emitted as a WFTextTokenAttachment with Type=Variable."""
    var = NamedVar("Screenshots")
    action = Share(input=var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["Type"] == "Variable"
    assert wf_input["Value"]["VariableName"] == "Screenshots"


# ---------------------------------------------------------------------------
# Field-omission tests
# ---------------------------------------------------------------------------


def test_share_no_input_omits_wfinput() -> None:
    """When input is None, WFInput is absent from the parameters dict."""
    action = Share()
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFInput" not in params


def test_share_params_only_wfinput_when_set() -> None:
    """Parameters dict contains exactly WFInput + UUID when input is set."""
    action = Share(input="data")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    # UUID is always injected by to_action_dict; no other keys expected.
    assert set(params.keys()) == {"WFInput", "UUID"}


def test_share_no_default_output_name() -> None:
    """Share produces no output — default_output_name is empty."""
    assert Share.default_output_name == ""


# ---------------------------------------------------------------------------
# Registry lookup
# ---------------------------------------------------------------------------


def test_share_registered() -> None:
    """Share is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.share")
    assert cls is Share


# ---------------------------------------------------------------------------
# Wire-format equivalence — daily_standup.xml (ActionOutput reference)
# ---------------------------------------------------------------------------


def test_share_wire_format_daily_standup() -> None:
    """Share schema matches the ``is.workflow.actions.share`` action in daily_standup.xml.

    Source: samples/decoded/daily_standup.xml, action index 37.
    Sample params (after normalisation):
        WFInput = {
            Value: {OutputName: "Text", Type: "ActionOutput"},
            WFSerializationType: "WFTextTokenAttachment"
        }
        (OutputUUID and action UUID stripped by normalisation)

    The sample carries no UUID on the share action itself — it has no
    output so Shortcuts doesn't need a stable reference UUID here.  After
    normalisation both sides reduce to the same structure.
    """
    if not DAILY_STANDUP.exists():
        pytest.skip(f"Sample not found: {DAILY_STANDUP}")

    workflow = _load(DAILY_STANDUP)
    sample_action = workflow["WFWorkflowActions"][37]
    assert sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.share"
    sample_norm = _normalise(sample_action)

    # The sample's WFInput references the output of the preceding Text action
    # named "Text".  OutputUUID is stripped by normalisation, so we only need
    # the OutputName to match.
    text_output = Output(uuid="BAF04A43-1854-4E28-8641-0E293CF4EAA1", name="Text")
    schema_action = Share(input=text_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Wire-format equivalence — combine_screenshots_and_share.xml (NamedVar)
# ---------------------------------------------------------------------------


def test_share_wire_format_combine_screenshots() -> None:
    """Share schema matches the ``is.workflow.actions.share`` action in combine_screenshots_and_share.xml.

    Source: samples/decoded/combine_screenshots_and_share.xml.
    Sample params (after normalisation):
        WFInput = {
            Value: {Type: "Variable", VariableName: "Screenshots"},
            WFSerializationType: "WFTextTokenAttachment"
        }
        (VariableUUID stripped by normalisation)

    The sample also carries no UUID on the action itself, consistent with
    the share action producing no output.
    """
    if not COMBINE.exists():
        pytest.skip(f"Sample not found: {COMBINE}")

    workflow = _load(COMBINE)
    sample_action = _find_action(workflow, "is.workflow.actions.share")
    sample_norm = _normalise(sample_action)

    screenshots_var = NamedVar("Screenshots")
    schema_action = Share(input=screenshots_var)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
