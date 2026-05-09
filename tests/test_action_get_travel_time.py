"""Tests for the GetTravelTime action schema."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_travel_time import GetTravelTime
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
RUNNING_LATE = DECODED / "running_late.xml"
DICTIONARY = DECODED / "dictionary.xml"


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID from all dicts so UUIDs don't matter."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip UUID and OutputUUID fields for comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(out)
    return out


# ---------------------------------------------------------------------------
# Basic construction and transport types
# ---------------------------------------------------------------------------


def test_gettraveltime_default_transport_omits_key() -> None:
    """Default transport_type='Driving' omits WFTransportType from emitted dict.

    All 3 corpus samples use the Driving default and carry no WFTransportType
    key: running_late.xml index 1, dictionary.xml index 114, index 320.
    """
    dest = Output(uuid="AAAA-1111", name="Calendar Events")
    action = GetTravelTime(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFTransportType" not in params
    assert action.transport_type == "Driving"


def test_gettraveltime_walking_emits_transport_key() -> None:
    """transport_type='Walking' emits WFTransportType in the params dict."""
    dest = Output(uuid="BBBB-2222", name="Work")
    action = GetTravelTime(destination=dest, transport_type="Walking")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFTransportType"] == "Walking"


def test_gettraveltime_transit_emits_transport_key() -> None:
    """transport_type='Transit' emits WFTransportType in the params dict."""
    dest = Output(uuid="CCCC-3333", name="Station")
    action = GetTravelTime(destination=dest, transport_type="Transit")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFTransportType"] == "Transit"


def test_gettraveltime_cycling_emits_transport_key() -> None:
    """transport_type='Cycling' emits WFTransportType in the params dict."""
    dest = Output(uuid="DDDD-4444", name="Park")
    action = GetTravelTime(destination=dest, transport_type="Cycling")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFTransportType"] == "Cycling"


def test_gettraveltime_invalid_transport_raises() -> None:
    """An unrecognised transport_type raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Subway'"):
        GetTravelTime(
            transport_type="Subway"  # ty: ignore[invalid-argument-type]  # intentional bad value
        )


# ---------------------------------------------------------------------------
# Destination field — WFTextTokenAttachment envelope
# ---------------------------------------------------------------------------


def test_gettraveltime_destination_attachment_envelope() -> None:
    """WFDestination emits a WFTextTokenAttachment envelope for an Output.

    Corpus evidence: all 3 samples use a bare WFTextTokenAttachment (not
    WFTextTokenString) for the destination slot.
    """
    dest = Output(uuid="7BB4AD62-BA5C-4A9D-824A-D1EA6636103E", name="Calendar Events")
    action = GetTravelTime(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_dest = params["WFDestination"]
    assert wf_dest["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_dest["Value"]["Type"] == "ActionOutput"
    assert wf_dest["Value"]["OutputName"] == "Calendar Events"


def test_gettraveltime_no_destination_omits_key() -> None:
    """When destination is None, WFDestination is absent from emitted params."""
    action = GetTravelTime()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDestination" not in params


def test_gettraveltime_origin_emits_wffromaddress() -> None:
    """When origin is set, WFFromAddress appears in emitted params."""
    origin = Output(uuid="EEEE-5555", name="Home")
    dest = Output(uuid="FFFF-6666", name="Office")
    action = GetTravelTime(destination=dest, origin=origin)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFFromAddress" in params
    assert params["WFFromAddress"]["WFSerializationType"] == "WFTextTokenAttachment"


def test_gettraveltime_no_origin_omits_key() -> None:
    """When origin is not set, WFFromAddress is absent from emitted params."""
    dest = Output(uuid="GGGG-7777", name="Work")
    action = GetTravelTime(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFFromAddress" not in params


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_gettraveltime_registered() -> None:
    """GetTravelTime is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.gettraveltime")
    assert cls is GetTravelTime


def test_gettraveltime_default_output_name() -> None:
    """GetTravelTime.default_output_name is 'Travel Time'."""
    assert GetTravelTime.default_output_name == "Travel Time"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus samples
# ---------------------------------------------------------------------------


def test_gettraveltime_wire_format_running_late() -> None:
    """GetTravelTime schema matches the sample in running_late.xml, index 1.

    Sample params (after normalisation):
        WFDestination = WFTextTokenAttachment referencing 'Calendar Events' output
        WFTransportType = absent (Driving default, key omitted)

    Source: samples/decoded/running_late.xml, WFWorkflowActions[1].
    """
    if not RUNNING_LATE.exists():
        pytest.skip(f"Sample not found: {RUNNING_LATE}")

    workflow = _load(RUNNING_LATE)
    sample_action = workflow["WFWorkflowActions"][1]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.gettraveltime"
    )
    sample_norm = _normalise(sample_action)

    # Reconstruct with the same OutputUUID that the sample references.
    # OutputName from the sample: "Calendar Events".
    calendar_output = Output(
        uuid="7BB4AD62-BA5C-4A9D-824A-D1EA6636103E",
        name="Calendar Events",
    )
    schema_action = GetTravelTime(destination=calendar_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_gettraveltime_wire_format_dictionary_index114() -> None:
    """GetTravelTime schema matches the sample in dictionary.xml, index 114.

    Sample params (after normalisation):
        WFDestination = WFTextTokenAttachment referencing 'Halfway Point' output
        WFTransportType = absent (Driving default)

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[114].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][114]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.gettraveltime"
    )
    sample_norm = _normalise(sample_action)

    halfway_output = Output(
        uuid="22558709-DE3D-4E88-87F5-4C79A0D5492E",
        name="Halfway Point",
    )
    schema_action = GetTravelTime(destination=halfway_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_gettraveltime_wire_format_dictionary_index320() -> None:
    """GetTravelTime schema matches the sample in dictionary.xml, index 320.

    Sample params (after normalisation):
        WFDestination = WFTextTokenAttachment referencing 'Maps URL' output
        WFTransportType = absent (Driving default)

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[320].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][320]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.gettraveltime"
    )
    sample_norm = _normalise(sample_action)

    maps_url_output = Output(
        uuid="AEA4228E-D8B2-4968-9312-3DD470EE4309",
        name="Maps URL",
    )
    schema_action = GetTravelTime(destination=maps_url_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
