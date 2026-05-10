"""Tests for the SearchMaps action schema.

Corpus source: samples/decoded/dictionary.xml, indices 105 and 322.
Both appearances use WFInput with a WFTextTokenAttachment envelope.
Jellycore carries no data for is.workflow.actions.searchmaps.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.search_maps import SearchMaps
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


def test_searchmaps_no_query_emits_no_params() -> None:
    """When query is None, no parameters are emitted beyond UUID."""
    action = SearchMaps()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    params.pop("UUID", None)
    assert params == {}


def test_searchmaps_with_output_query_emits_wfinput_key() -> None:
    """Passing an Output as query emits WFInput."""
    dest = Output(uuid="AAAA-1111", name="Locations")
    action = SearchMaps(query=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" in params


def test_searchmaps_query_uses_wftexttokenattachment_envelope() -> None:
    """WFInput serialises as a WFTextTokenAttachment envelope.

    Corpus evidence: both appearances in dictionary.xml (indices 105 and 322)
    use a bare WFTextTokenAttachment (not a WFTextTokenString wrapper).
    """
    dest = Output(uuid="BBBB-2222", name="Locations")
    action = SearchMaps(query=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["Type"] == "ActionOutput"
    assert wf_input["Value"]["OutputName"] == "Locations"


def test_searchmaps_query_action_output_ref_is_correct() -> None:
    """Output uuid and name appear correctly inside the attachment envelope."""
    dest = Output(uuid="CCCC-3333", name="My Search")
    action = SearchMaps(query=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    value = params["WFInput"]["Value"]
    assert value["OutputUUID"] == "CCCC-3333"
    assert value["OutputName"] == "My Search"
    assert value["Type"] == "ActionOutput"


def test_searchmaps_string_query_passes_through() -> None:
    """A bare string query passes through coerce_value unchanged."""
    action = SearchMaps(query="coffee near me")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"] == "coffee near me"


def test_searchmaps_prebuilt_dict_passes_through() -> None:
    """A pre-built wire-format dict passes through coerce_value unchanged."""
    envelope = {
        "Value": {
            "OutputName": "Places",
            "OutputUUID": "DDDD-4444",
            "Type": "ActionOutput",
        },
        "WFSerializationType": "WFTextTokenAttachment",
    }
    action = SearchMaps(query=envelope)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"] is envelope


def test_searchmaps_no_wrong_keys_emitted() -> None:
    """The emitted params dict does not contain map-sibling keys.

    SearchMaps uses WFInput, not WFSearchTerm, WFDestination, or any other
    map-family key. This guards against copy-paste from sibling actions.
    """
    dest = Output(uuid="EEEE-5555", name="Park")
    action = SearchMaps(query=dest)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDestination" not in params
    assert "WFSearchTerm" not in params
    assert "WFGetDistanceDestination" not in params
    assert "WFTransportType" not in params


# ---------------------------------------------------------------------------
# Identifier, registry, and metadata
# ---------------------------------------------------------------------------


def test_searchmaps_identifier() -> None:
    """SearchMaps.identifier is 'is.workflow.actions.searchmaps'."""
    assert SearchMaps.identifier == "is.workflow.actions.searchmaps"


def test_searchmaps_registered() -> None:
    """SearchMaps is findable in the action registry by its identifier."""
    cls = lookup("is.workflow.actions.searchmaps")
    assert cls is SearchMaps


def test_searchmaps_default_output_name() -> None:
    """SearchMaps.default_output_name is 'Maps'."""
    assert SearchMaps.default_output_name == "Maps"


def test_searchmaps_uuid_is_fresh_per_instance() -> None:
    """Each SearchMaps instance gets a unique UUID by default."""
    a1 = SearchMaps()
    a2 = SearchMaps()
    assert a1.uuid != a2.uuid


def test_searchmaps_uuid_override() -> None:
    """Passing uuid= overrides the auto-generated UUID."""
    action = SearchMaps(uuid="FIXED-UUID")
    assert action.to_action_dict()["WFWorkflowActionParameters"]["UUID"] == "FIXED-UUID"


def test_searchmaps_action_identifier_in_wire_dict() -> None:
    """to_action_dict includes the correct WFWorkflowActionIdentifier."""
    action = SearchMaps()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.searchmaps"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus samples
# ---------------------------------------------------------------------------


def test_searchmaps_wire_format_dictionary_index105() -> None:
    """SearchMaps schema matches corpus sample dictionary.xml, index 105.

    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing 'Locations'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[105].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][105]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.searchmaps"
    )
    sample_norm = _normalise(sample_action)

    # The corpus sample references the output of an earlier Maps action.
    # OutputName from the sample: "Locations".
    locations_output = Output(
        uuid="4EA23489-9671-4DF8-B7F5-806632BB00E2",
        name="Locations",
    )
    schema_action = SearchMaps(query=locations_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_searchmaps_wire_format_dictionary_index322() -> None:
    """SearchMaps schema matches corpus sample dictionary.xml, index 322.

    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing 'Travel Time'
        No other keys present.

    Source: samples/decoded/dictionary.xml, WFWorkflowActions[322].
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][322]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.searchmaps"
    )
    sample_norm = _normalise(sample_action)

    travel_time_output = Output(
        uuid="ADA50399-09A4-4FA1-A076-D6485BABE4EC",
        name="Travel Time",
    )
    schema_action = SearchMaps(query=travel_time_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
