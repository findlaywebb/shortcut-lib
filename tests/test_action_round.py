"""Tests for RoundNumber — is.workflow.actions.round."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.round import RoundNumber
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
POMODORO = DECODED / "start_pomodoro.xml"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers (copied from test_wire_format_equivalence pattern)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID from all dicts."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic UUID fields before comparing."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Constructor and field tests
# ---------------------------------------------------------------------------


def test_round_defaults_all_omitted() -> None:
    """RoundNumber with all defaults emits only WFInput; mode and place absent.

    Apple omits WFRoundMode for "Normal" and WFRoundTo for "Ones Place".
    Confirmed: dictionary.xml:304 and dictionary.xml:4582 carry only WFInput.
    """
    prev = Output(uuid="BB37E983-4ED1-48FD-960D-3AE7FA5BAD3D", name="Random Number")
    action = RoundNumber(input=prev)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFRoundMode" not in params
    assert "WFRoundTo" not in params
    assert "WFInput" in params
    assert params["WFInput"]["WFSerializationType"] == "WFTextTokenAttachment"


def test_round_mode_always_round_up_emitted() -> None:
    """WFRoundMode is emitted when mode != 'Normal'.

    Confirmed: start_pomodoro.xml:45 carries WFRoundMode='Always Round Up'.
    """
    prev = Output(uuid="E27FB393-66E9-441D-A088-5B0674806611", name="Break Length")
    action = RoundNumber(input=prev, mode="Always Round Up")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFRoundMode"] == "Always Round Up"
    assert "WFRoundTo" not in params


def test_round_mode_always_round_down_emitted() -> None:
    """WFRoundMode is emitted when mode == 'Always Round Down'."""
    prev = Output(uuid="AABBCCDD-0000-1111-2222-333344445555", name="Score")
    action = RoundNumber(input=prev, mode="Always Round Down")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFRoundMode"] == "Always Round Down"


def test_round_place_non_default_emitted() -> None:
    """WFRoundTo is emitted when place != 'Ones Place'."""
    prev = Output(uuid="AABBCCDD-0000-1111-2222-333344446666", name="Value")
    action = RoundNumber(input=prev, place="Tenths")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFRoundTo"] == "Tenths"
    assert "WFRoundMode" not in params


def test_round_place_hundreds_and_mode_combined() -> None:
    """Both WFRoundMode and WFRoundTo are emitted when both are non-default."""
    prev = Output(uuid="AABBCCDD-0000-1111-2222-333344447777", name="Price")
    action = RoundNumber(input=prev, mode="Always Round Up", place="Hundreds Place")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFRoundMode"] == "Always Round Up"
    assert params["WFRoundTo"] == "Hundreds Place"


def test_round_no_input_omits_wfinput() -> None:
    """When input is None, WFInput is absent from emitted params."""
    action = RoundNumber()
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFInput" not in params
    assert "WFRoundMode" not in params
    assert "WFRoundTo" not in params


def test_round_identifier() -> None:
    """RoundNumber emits the correct WFWorkflowActionIdentifier."""
    action = RoundNumber()
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.round"


def test_round_default_output_name() -> None:
    """RoundNumber.default_output_name is 'Rounded Number'."""
    assert RoundNumber.default_output_name == "Rounded Number"


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_round_registered() -> None:
    """RoundNumber is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.round")
    assert cls is RoundNumber


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


def test_round_invalid_mode_raises() -> None:
    """An unrecognised mode raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Round Up'"):
        RoundNumber(mode="Round Up")  # ty: ignore[invalid-argument-type]


def test_round_invalid_place_raises() -> None:
    """An unrecognised place raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Custom'"):
        RoundNumber(place="Custom")  # ty: ignore[invalid-argument-type]


def test_round_all_valid_modes_accepted() -> None:
    """All three documented WFRoundMode values construct without error."""
    for mode in ("Normal", "Always Round Up", "Always Round Down"):
        action = RoundNumber(mode=mode)
        params = action.to_action_dict()["WFWorkflowActionParameters"]
        if mode == "Normal":
            assert "WFRoundMode" not in params
        else:
            assert params["WFRoundMode"] == mode


def test_round_all_valid_places_spot_check() -> None:
    """A representative sample of WFRoundPlace values construct without error."""
    spot_check = (
        "Ones Place",
        "Tens Place",
        "Hundreds Place",
        "Thousands",
        "Tenths",
        "Hundredths",
        "Thousandths",
        "Millionths",
    )
    for place in spot_check:
        action = RoundNumber(place=place)
        params = action.to_action_dict()["WFWorkflowActionParameters"]
        if place == "Ones Place":
            assert "WFRoundTo" not in params
        else:
            assert params["WFRoundTo"] == place


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus samples
# ---------------------------------------------------------------------------


def test_round_wire_format_start_pomodoro() -> None:
    """RoundNumber schema matches start_pomodoro.xml round action.

    Source: samples/decoded/start_pomodoro.xml, action index 2.
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "Break Length"
        WFRoundMode = "Always Round Up"
        (WFRoundTo absent — "Ones Place" default)

    OutputUUID stripped by normalisation.
    """
    if not POMODORO.exists():
        pytest.skip(f"Sample not found: {POMODORO}")

    workflow = _load(POMODORO)
    sample_action = workflow["WFWorkflowActions"][2]
    assert sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.round"
    sample_norm = _normalise(sample_action)

    prev = Output(
        uuid="E27FB393-66E9-441D-A088-5B0674806611",
        name="Break Length",
    )
    schema_action = RoundNumber(input=prev, mode="Always Round Up")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_round_wire_format_dictionary_first() -> None:
    """RoundNumber schema matches dictionary.xml first round action.

    Source: samples/decoded/dictionary.xml, action index containing the first
    is.workflow.actions.round (after is.workflow.actions.number.random at line 295).
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "Random Number"
        (WFRoundMode absent — "Normal" default)
        (WFRoundTo absent — "Ones Place" default)
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    # Find the first round action index
    actions = workflow["WFWorkflowActions"]
    first_round_idx = next(
        i
        for i, a in enumerate(actions)
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.round"
    )
    sample_action = actions[first_round_idx]
    sample_norm = _normalise(sample_action)

    prev = Output(
        uuid="BB37E983-4ED1-48FD-960D-3AE7FA5BAD3D",
        name="Random Number",
    )
    schema_action = RoundNumber(input=prev)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_round_wire_format_dictionary_second() -> None:
    """RoundNumber schema matches dictionary.xml second round action.

    Source: samples/decoded/dictionary.xml, action index of second round
    occurrence (around line 4582).
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "Random Number"
        (WFRoundMode absent — default)
        (WFRoundTo absent — default)
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    actions = workflow["WFWorkflowActions"]
    round_actions = [
        (i, a)
        for i, a in enumerate(actions)
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.round"
    ]
    # Second occurrence
    assert len(round_actions) >= 2, (
        "Expected at least 2 round actions in dictionary.xml"
    )
    second_idx, sample_action = round_actions[1]
    sample_norm = _normalise(sample_action)

    prev = Output(
        uuid="E0A873D4-6D4C-44C1-931E-6F6EB7BF32B4",
        name="Random Number",
    )
    schema_action = RoundNumber(input=prev)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
