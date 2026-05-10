"""Tests for ChooseFromList — is.workflow.actions.choosefromlist."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.choose_from_list import ChooseFromList
from shortcut_lib.schema.registry import list_actions, lookup
from shortcut_lib.schema.values import NamedVar, Output

_IDENTIFIER = "is.workflow.actions.choosefromlist"
DECODED = Path(__file__).parent.parent / "samples" / "decoded"
SET_WEEKEND = DECODED / "set_weekend_chores.xml"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML and return its top-level dict."""
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
    """Strip non-deterministic UUID/CustomOutputName for comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Happy path — minimal (WFInput only, no prompt, no flags)
# ---------------------------------------------------------------------------


def test_choose_from_list_minimal_emits_wfinput() -> None:
    """Minimal ChooseFromList: only WFInput emitted.

    Verified against samples/decoded/dictionary.xml, action index 13.
    Apple omits WFChooseFromListActionPrompt when there is no prompt and
    omits WFChooseFromListActionSelectMultiple when False/unset.
    """
    source = Output(uuid="91A02720-4C60-4126-8E75-6D344924D765", name="List")
    action = ChooseFromList(input=source)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFInput" in params
    assert params["WFInput"]["WFSerializationType"] == "WFTextTokenAttachment"
    assert params["WFInput"]["Value"]["OutputName"] == "List"
    assert "WFChooseFromListActionPrompt" not in params
    assert "WFChooseFromListActionSelectMultiple" not in params
    assert "WFChooseFromListActionSelectAll" not in params


def test_choose_from_list_correct_identifier() -> None:
    """to_action_dict emits the correct Apple identifier."""
    action = ChooseFromList()
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == _IDENTIFIER


def test_choose_from_list_default_output_name() -> None:
    """default_output_name is 'Chosen Item' (confirmed by set_weekend_chores.xml)."""
    assert ChooseFromList.default_output_name == "Chosen Item"


# ---------------------------------------------------------------------------
# Multi-select happy path (with prompt and select_multiple=True)
# ---------------------------------------------------------------------------


def test_choose_from_list_multi_select_emits_all_fields() -> None:
    """Multi-select config emits WFInput, prompt, and select-multiple flag.

    Verified against samples/decoded/set_weekend_chores.xml, action index 1.
    """
    source = Output(uuid="5ACF1422-8187-4840-9ACF-142281878840", name="List")
    action = ChooseFromList(
        input=source,
        prompt="Which chores do you need to get done today?",
        select_multiple=True,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFChooseFromListActionPrompt"] == (
        "Which chores do you need to get done today?"
    )
    assert params["WFChooseFromListActionSelectMultiple"] is True
    assert "WFChooseFromListActionSelectAll" not in params


def test_choose_from_list_select_all_emitted_when_set() -> None:
    """select_all_initially=True emits WFChooseFromListActionSelectAll."""
    action = ChooseFromList(select_multiple=True, select_all_initially=True)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFChooseFromListActionSelectAll"] is True


# ---------------------------------------------------------------------------
# Field omission when None / falsy
# ---------------------------------------------------------------------------


def test_choose_from_list_empty_prompt_omitted() -> None:
    """An empty prompt string is omitted, matching Apple's behaviour."""
    action = ChooseFromList(prompt="")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFChooseFromListActionPrompt" not in params


def test_choose_from_list_none_input_omitted() -> None:
    """input=None means WFInput is omitted from the emitted dict."""
    action = ChooseFromList(input=None)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params


def test_choose_from_list_select_multiple_none_omitted() -> None:
    """select_multiple=None (default) means the key is omitted."""
    action = ChooseFromList()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFChooseFromListActionSelectMultiple" not in params


def test_choose_from_list_select_all_none_omitted() -> None:
    """select_all_initially=None (default) means the key is omitted."""
    action = ChooseFromList()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFChooseFromListActionSelectAll" not in params


# ---------------------------------------------------------------------------
# select_multiple=False emits the flag (not omitted, unlike None)
# ---------------------------------------------------------------------------


def test_choose_from_list_select_multiple_false_emitted() -> None:
    """select_multiple=False is explicitly emitted as False."""
    action = ChooseFromList(select_multiple=False)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFChooseFromListActionSelectMultiple" in params
    assert params["WFChooseFromListActionSelectMultiple"] is False


# ---------------------------------------------------------------------------
# Variable reference for input chains via coerce_value
# ---------------------------------------------------------------------------


def test_choose_from_list_action_input_resolves_uuid() -> None:
    """Passing an Action as input resolves to that action's OutputUUID."""
    from shortcut_lib.schema.actions.text_split import TextSplit

    split = TextSplit(input="a\nb\nc")
    action = ChooseFromList(input=split)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenAttachment"
    assert wfinput["Value"]["OutputUUID"] == split.uuid
    assert wfinput["Value"]["Type"] == "ActionOutput"


def test_choose_from_list_namedvar_input() -> None:
    """NamedVar as input resolves to a WFTextTokenAttachment variable ref."""
    var = NamedVar("MyList")
    action = ChooseFromList(input=var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenAttachment"
    assert wfinput["Value"]["VariableName"] == "MyList"
    assert wfinput["Value"]["Type"] == "Variable"


# ---------------------------------------------------------------------------
# Registry lookup
# ---------------------------------------------------------------------------


def test_choose_from_list_registered_in_list_actions() -> None:
    """ChooseFromList appears in list_actions() with the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert _IDENTIFIER in identifiers


def test_choose_from_list_registry_lookup() -> None:
    """lookup() returns ChooseFromList for the action identifier."""
    cls = lookup(_IDENTIFIER)
    assert cls is ChooseFromList


# ---------------------------------------------------------------------------
# Wire-format equivalence vs samples
# ---------------------------------------------------------------------------


def test_choose_from_list_wire_format_minimal() -> None:
    """Schema matches the minimal choosefromlist sample (no prompt, no flags).

    Source: samples/decoded/dictionary.xml, action index 13.
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "List" output
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][13]
    assert sample_action["WFWorkflowActionIdentifier"] == _IDENTIFIER
    sample_norm = _normalise(sample_action)

    source = Output(uuid="91A02720-4C60-4126-8E75-6D344924D765", name="List")
    schema_action = ChooseFromList(input=source)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_choose_from_list_wire_format_multi_select() -> None:
    """Schema matches the multi-select choosefromlist sample with prompt.

    Source: samples/decoded/set_weekend_chores.xml, action index 1.
    Sample params (after normalisation):
        WFChooseFromListActionPrompt         = "Which chores do you need…"
        WFChooseFromListActionSelectMultiple = True
        WFInput = WFTextTokenAttachment referencing "List" output
    """
    if not SET_WEEKEND.exists():
        pytest.skip(f"Sample not found: {SET_WEEKEND}")

    workflow = _load(SET_WEEKEND)
    sample_action = workflow["WFWorkflowActions"][1]
    assert sample_action["WFWorkflowActionIdentifier"] == _IDENTIFIER
    sample_norm = _normalise(sample_action)

    source = Output(uuid="5ACF1422-8187-4840-9ACF-142281878840", name="List")
    schema_action = ChooseFromList(
        input=source,
        prompt="Which chores do you need to get done today?",
        select_multiple=True,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
