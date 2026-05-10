"""Tests for the GetDirections action schema.

Corpus source: samples/decoded/dictionary.xml, indices 104 and 321.
Both appearances use WFDestination with a WFTextTokenAttachment envelope.
Jellycore carries no data for is.workflow.actions.getdirections.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_directions import GetDirections
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
DICTIONARY = DECODED / "dictionary.xml"


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID from all dicts so UUIDs don't affect eq."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip UUID and CustomOutputName for structural comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(out)
    return out


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------


def test_getdirections_no_destination_emits_no_params() -> None:
    """When destination is None, no parameters are emitted beyond UUID."""
    action = GetDirections()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    params.pop("UUID", None)
    assert params == {}


def test_getdirections_with_output_destination_emits_wfdestination_key() -> None:
    """Passing an Output as destination emits WFDestination."""
    dest = Output(uuid="AAAA-1111", name="Locations")
    action = GetDirections(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDestination" in params


def test_getdirections_destination_uses_wftexttokenattachment_envelope() -> None:
    """WFDestination serialises as a WFTextTokenAttachment envelope.

    Corpus evidence: both appearances in dictionary.xml (indices 104 and 321)
    use a bare WFTextTokenAttachment (not a WFTextTokenString wrapper).
    This matches the identical slot in the sibling gettraveltime action.
    """
    dest = Output(uuid="BBBB-2222", name="Locations")
    action = GetDirections(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_dest = params["WFDestination"]
    assert wf_dest["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_dest["Value"]["Type"] == "ActionOutput"
    assert wf_dest["Value"]["OutputName"] == "Locations"


def test_getdirections_destination_action_output_ref_is_correct() -> None:
    """Output uuid and name appear correctly inside the attachment envelope."""
    dest = Output(uuid="CCCC-3333", name="Home")
    action = GetDirections(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    value = params["WFDestination"]["Value"]
    assert value["OutputUUID"] == "CCCC-3333"
    assert value["OutputName"] == "Home"
    assert value["Type"] == "ActionOutput"


def test_getdirections_string_destination_passes_through() -> None:
    """A bare address string passes through coerce_value unchanged."""
    action = GetDirections(destination="1 Infinite Loop, Cupertino, CA")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDestination"] == "1 Infinite Loop, Cupertino, CA"


def test_getdirections_prebuilt_dict_passes_through() -> None:
    """A pre-built wire-format dict passes through coerce_value unchanged."""
    envelope = {
        "Value": {
            "OutputName": "Work",
            "OutputUUID": "DDDD-4444",
            "Type": "ActionOutput",
        },
        "WFSerializationType": "WFTextTokenAttachment",
    }
    action = GetDirections(destination=envelope)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDestination"] is envelope


def test_getdirections_no_wrong_keys_emitted() -> None:
    """The emitted params dict does not contain map-sibling keys.

    GetDirections uses WFDestination, not WFInput (searchmaps) or
    WFGetDistanceDestination (getdistance). This guards against cross-
    contamination from sibling actions. The corpus confirms no WFTransportType
    or WFFromAddress keys were present either.
    """
    dest = Output(uuid="EEEE-5555", name="Park")
    action = GetDirections(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params
    assert "WFGetDistanceDestination" not in params
    assert "WFTransportType" not in params
    assert "WFFromAddress" not in params


# ---------------------------------------------------------------------------
# Identifier, registry, and metadata
# ---------------------------------------------------------------------------


def test_getdirections_identifier() -> None:
    """GetDirections.identifier is 'is.workflow.actions.getdirections'."""
    assert GetDirections.identifier == "is.workflow.actions.getdirections"


def test_getdirections_registered() -> None:
    """GetDirections is findable in the action registry by its identifier."""
    cls = lookup("is.workflow.actions.getdirections")
    assert cls is GetDirections


def test_getdirections_default_output_name() -> None:
    """GetDirections.default_output_name is 'Maps'."""
    assert GetDirections.default_output_name == "Maps"


def test_getdirections_uuid_is_fresh_per_instance() -> None:
    """Each GetDirections instance gets a unique UUID by default."""
    a1 = GetDirections()
    a2 = GetDirections()
    assert a1.uuid != a2.uuid


def test_getdirections_uuid_override() -> None:
    """Passing uuid= overrides the auto-generated UUID."""
    action = GetDirections(uuid="FIXED-UUID")
    assert action.to_action_dict()["WFWorkflowActionParameters"]["UUID"] == "FIXED-UUID"


def test_getdirections_action_identifier_in_wire_dict() -> None:
    """to_action_dict includes the correct WFWorkflowActionIdentifier."""
    action = GetDirections()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.getdirections"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus samples
# ---------------------------------------------------------------------------


def test_getdirections_wire_format_dictionary_index104() -> None:
    """GetDirections schema matches corpus sample dictionary.xml, index 104.

    Sample params (after normalisation):
        WFDestination = WFTextTokenAttachment referencing 'Locations'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[104].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][104]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.getdirections"
    )
    sample_norm = _normalise(sample_action)

    locations_output = Output(
        uuid="4EA23489-9671-4DF8-B7F5-806632BB00E2",
        name="Locations",
    )
    schema_action = GetDirections(destination=locations_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_getdirections_wire_format_dictionary_index321() -> None:
    """GetDirections schema matches corpus sample dictionary.xml, index 321.

    Sample params (after normalisation):
        WFDestination = WFTextTokenAttachment referencing 'Travel Time'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[321].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][321]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.getdirections"
    )
    sample_norm = _normalise(sample_action)

    travel_time_output = Output(
        uuid="ADA50399-09A4-4FA1-A076-D6485BABE4EC",
        name="Travel Time",
    )
    schema_action = GetDirections(destination=travel_time_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
