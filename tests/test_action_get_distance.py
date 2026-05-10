"""Tests for the GetDistance action schema."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_distance import GetDistance
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
    """Strip UUID and OutputUUID fields for comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(out)
    return out


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------


def test_getdistance_no_destination_emits_no_params() -> None:
    """When destination is None, no parameters are emitted beyond UUID."""
    action = GetDistance()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    params.pop("UUID", None)
    assert params == {}


def test_getdistance_with_output_destination_emits_key() -> None:
    """Passing an Output as destination emits WFGetDistanceDestination."""
    dest = Output(uuid="AAAA-1111", name="Addresses")
    action = GetDistance(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFGetDistanceDestination" in params


def test_getdistance_destination_uses_wftexttokenattachment_envelope() -> None:
    """WFGetDistanceDestination serialises as a WFTextTokenAttachment envelope.

    Corpus evidence: both appearances in dictionary.xml use a bare
    WFTextTokenAttachment (not a WFTextTokenString wrapper).
    """
    dest = Output(uuid="BBBB-2222", name="Addresses")
    action = GetDistance(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_dest = params["WFGetDistanceDestination"]
    assert wf_dest["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_dest["Value"]["Type"] == "ActionOutput"
    assert wf_dest["Value"]["OutputName"] == "Addresses"


def test_getdistance_destination_action_output_ref_is_correct() -> None:
    """Output uuid and name appear correctly inside the attachment envelope."""
    dest = Output(uuid="CCCC-3333", name="My Location")
    action = GetDistance(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    value = params["WFGetDistanceDestination"]["Value"]
    assert value["OutputUUID"] == "CCCC-3333"
    assert value["OutputName"] == "My Location"
    assert value["Type"] == "ActionOutput"


def test_getdistance_string_destination_passes_through() -> None:
    """A bare address string passes through coerce_value unchanged."""
    action = GetDistance(destination="1 Infinite Loop, Cupertino, CA")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetDistanceDestination"] == "1 Infinite Loop, Cupertino, CA"


def test_getdistance_prebuilt_dict_passes_through() -> None:
    """A pre-built wire-format dict passes through coerce_value unchanged."""
    envelope = {
        "Value": {
            "OutputName": "Work",
            "OutputUUID": "DDDD-4444",
            "Type": "ActionOutput",
        },
        "WFSerializationType": "WFTextTokenAttachment",
    }
    action = GetDistance(destination=envelope)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetDistanceDestination"] is envelope


def test_getdistance_no_wrong_keys_emitted() -> None:
    """The emitted params dict does not contain gettraveltime keys.

    GetDistance uses WFGetDistanceDestination, not WFDestination. This test
    guards against copy-paste from the sibling gettraveltime action.
    """
    dest = Output(uuid="EEEE-5555", name="Park")
    action = GetDistance(destination=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDestination" not in params
    assert "WFTransportType" not in params
    assert "WFFromAddress" not in params


# ---------------------------------------------------------------------------
# Identifier, registry, and metadata
# ---------------------------------------------------------------------------


def test_getdistance_identifier() -> None:
    """GetDistance.identifier is 'is.workflow.actions.getdistance'."""
    assert GetDistance.identifier == "is.workflow.actions.getdistance"


def test_getdistance_registered() -> None:
    """GetDistance is findable in the action registry by its identifier."""
    cls = lookup("is.workflow.actions.getdistance")
    assert cls is GetDistance


def test_getdistance_default_output_name() -> None:
    """GetDistance.default_output_name is 'Distance'."""
    assert GetDistance.default_output_name == "Distance"


def test_getdistance_uuid_is_fresh_per_instance() -> None:
    """Each GetDistance instance gets a unique UUID by default."""
    a1 = GetDistance()
    a2 = GetDistance()
    assert a1.uuid != a2.uuid


def test_getdistance_uuid_override() -> None:
    """Passing uuid= overrides the auto-generated UUID."""
    action = GetDistance(uuid="FIXED-UUID")
    assert action.to_action_dict()["WFWorkflowActionParameters"]["UUID"] == "FIXED-UUID"


def test_getdistance_action_identifier_in_wire_dict() -> None:
    """to_action_dict includes the correct WFWorkflowActionIdentifier."""
    action = GetDistance()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.getdistance"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus samples
# ---------------------------------------------------------------------------


def test_getdistance_wire_format_dictionary_index112() -> None:
    """GetDistance schema matches corpus sample dictionary.xml, index 112.

    Sample params (after normalisation):
        WFGetDistanceDestination = WFTextTokenAttachment referencing 'Addresses'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[112].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][112]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.getdistance"
    )
    sample_norm = _normalise(sample_action)

    # The corpus sample references the output of the preceding action (index 111).
    # OutputName from the sample: "Addresses".
    addresses_output = Output(
        uuid="5397DA49-BA97-4147-9997-21AF5544087E",
        name="Addresses",
    )
    schema_action = GetDistance(destination=addresses_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_getdistance_wire_format_dictionary_index317() -> None:
    """GetDistance schema matches corpus sample dictionary.xml, index 317.

    Sample params (after normalisation):
        WFGetDistanceDestination = WFTextTokenAttachment referencing 'Addresses'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[317].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][317]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.getdistance"
    )
    sample_norm = _normalise(sample_action)

    addresses_output = Output(
        uuid="F2297EDD-1BAE-4A16-AE8A-DB27C427401C",
        name="Addresses",
    )
    schema_action = GetDistance(destination=addresses_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
