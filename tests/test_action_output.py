"""StopAndOutput — tests for is.workflow.actions.output.

Covers:
  - Basic construction and identifier.
  - Wire-format equivalence against both corpus samples:
      * dictionary.xml  (WFOutput only)
      * sort_lines.xml  (WFOutput + WFNoOutputSurfaceBehavior + WFResponse)
  - Optional-key omission behaviour.
  - Invalid no_surface_behavior guard.
  - Missing output guard.
  - Registry visibility.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema import list_actions
from shortcut_lib.schema.actions.output import StopAndOutput
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
DICTIONARY = DECODED / "dictionary.xml"
SORT_LINES = DECODED / "sort_lines.xml"


# ---------------------------------------------------------------------------
# Helpers (mirrors test_wire_format_equivalence.py conventions)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _find_action(workflow: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return the first action matching *identifier* or raise."""
    for action in workflow["WFWorkflowActions"]:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action
    raise KeyError(f"No action with identifier {identifier!r} in sample")


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID so UUIDs don't cause spurious mismatches."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic fields: UUID, CustomOutputName, OutputUUID."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_identifier() -> None:
    """StopAndOutput carries the correct action identifier."""
    action = StopAndOutput(output="hello")
    assert action.to_action_dict()["WFWorkflowActionIdentifier"] == (
        "is.workflow.actions.output"
    )


def test_basic_string_output() -> None:
    """Plain-string output is passed through without wrapping."""
    action = StopAndOutput(output="hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFOutput"] == "hello"
    assert "WFNoOutputSurfaceBehavior" not in params
    assert "WFResponse" not in params


def test_output_variable_reference() -> None:
    """An Output reference is encoded as WFTextTokenString (one-attachment)."""
    ref = Output(uuid="AAAA-BBBB", name="Combined Text")
    action = StopAndOutput(output=ref)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_output = params["WFOutput"]
    assert wf_output["WFSerializationType"] == "WFTextTokenString"
    # Inner string uses the object-replacement placeholder.
    assert wf_output["Value"]["string"] == "￼"
    # The single attachment is keyed at offset 0.
    assert "{0, 1}" in wf_output["Value"]["attachmentsByRange"]
    token = wf_output["Value"]["attachmentsByRange"]["{0, 1}"]
    assert token["OutputName"] == "Combined Text"
    assert token["Type"] == "ActionOutput"


def test_no_surface_behavior_and_response_emitted_when_set() -> None:
    """Both optional keys appear when *no_surface_behavior* and *response* are given."""
    ref = Output(uuid="AAAA", name="Out")
    action = StopAndOutput(
        output=ref,
        no_surface_behavior="Respond",
        response=ref,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNoOutputSurfaceBehavior"] == "Respond"
    assert "WFResponse" in params
    assert params["WFResponse"]["WFSerializationType"] == "WFTextTokenString"


def test_optional_keys_absent_when_none() -> None:
    """WFNoOutputSurfaceBehavior and WFResponse are absent when both are None."""
    action = StopAndOutput(output="x")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNoOutputSurfaceBehavior" not in params
    assert "WFResponse" not in params


def test_missing_output_raises() -> None:
    """StopAndOutput with output=None raises SchemaError."""
    with pytest.raises(SchemaError, match="requires `output`"):
        StopAndOutput().to_action_dict()


def test_invalid_no_surface_behavior_raises() -> None:
    """An unrecognised no_surface_behavior string raises SchemaError."""
    with pytest.raises(SchemaError, match="no_surface_behavior"):
        StopAndOutput(output="x", no_surface_behavior="Invalid").to_action_dict()


def test_in_registry() -> None:
    """is.workflow.actions.output appears in the action registry."""
    idents = {row["identifier"] for row in list_actions()}
    assert "is.workflow.actions.output" in idents


# ---------------------------------------------------------------------------
# Wire-format equivalence — dictionary.xml sample
# (WFOutput only; no WFNoOutputSurfaceBehavior, no WFResponse)
# ---------------------------------------------------------------------------


def test_wire_format_dictionary_xml() -> None:
    """StopAndOutput matches the dictionary.xml corpus sample.

    Source: samples/decoded/dictionary.xml — first is.workflow.actions.output.
    Sample params (after normalisation):
        WFOutput = WFTextTokenString with one attachment at {0, 1}:
            OutputName="Formatted File Size", Type="ActionOutput"
        (WFNoOutputSurfaceBehavior and WFResponse absent)

    The sample has no WFNoOutputSurfaceBehavior — pass no_surface_behavior=None.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = _find_action(workflow, "is.workflow.actions.output")
    sample_norm = _normalise(sample_action)

    # The sample's WFOutput attachment names the preceding action's output.
    # OutputUUID is stripped by normalisation, so any UUID works here.
    formatted_ref = Output(uuid="dummy", name="Formatted File Size")
    schema_action = StopAndOutput(output=formatted_ref)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Wire-format equivalence — sort_lines.xml sample
# (WFOutput + WFNoOutputSurfaceBehavior="Respond" + WFResponse)
# ---------------------------------------------------------------------------


def test_wire_format_sort_lines_xml() -> None:
    """StopAndOutput matches the sort_lines.xml corpus sample.

    Source: samples/decoded/sort_lines.xml — is.workflow.actions.output.
    Sample params (after normalisation):
        WFNoOutputSurfaceBehavior = "Respond"
        WFOutput  = WFTextTokenString with one attachment at {0, 1}:
            OutputName="Combined Text", Type="ActionOutput"
        WFResponse = WFTextTokenString with one attachment at {0, 1}:
            OutputName="Combined Text", Type="ActionOutput"  (same as WFOutput)

    WFResponse mirrors WFOutput when no_surface_behavior="Respond" — this
    appears to be Shortcuts.app's default: return the same value via the
    share sheet when there is no calling context.
    """
    if not SORT_LINES.exists():
        pytest.skip(f"Sample not found: {SORT_LINES}")

    workflow = _load(SORT_LINES)
    sample_action = _find_action(workflow, "is.workflow.actions.output")
    sample_norm = _normalise(sample_action)

    combined_ref = Output(uuid="dummy", name="Combined Text")
    schema_action = StopAndOutput(
        output=combined_ref,
        no_surface_behavior="Respond",
        response=combined_ref,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
