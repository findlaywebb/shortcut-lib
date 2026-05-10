"""Tests for ShowResult action schema."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

import shortcut_lib.schema.actions.show_result  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.show_result import ShowResult
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output, Text

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
POMODORO = DECODED / "start_pomodoro.xml"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers (mirrors test_wire_format_equivalence pattern)
# ---------------------------------------------------------------------------


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
    """Strip non-deterministic UUID fields for comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_show_result_no_text_emits_empty_params() -> None:
    """ShowResult() with no text produces an empty params dict (no Text key)."""
    action = ShowResult()
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.showresult"
    params = d["WFWorkflowActionParameters"]
    assert "Text" not in params


def test_show_result_none_omits_text_key() -> None:
    """Explicit text=None omits the Text key — same as default."""
    action = ShowResult(text=None)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "Text" not in params


def test_show_result_plain_string() -> None:
    """A plain string in the text slot lands in the Text key as-is."""
    action = ShowResult(text="Hello, world!")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["Text"] == "Hello, world!"


def test_show_result_empty_string_omits_key() -> None:
    """An empty string does not emit the Text key."""
    action = ShowResult(text="")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "Text" not in params


def test_show_result_text_template() -> None:
    """A Text(...) template in the text slot produces a WFTextTokenString envelope."""
    break_output = Output(
        uuid="E27FB393-66E9-441D-A088-5B0674806611", name="Break Length"
    )
    template = Text(
        "Started a timer for {break_len} minutes. "
        "Your focus will stay on until the timer goes off.",
        substitutions={"break_len": break_output},
    )
    action = ShowResult(text=template)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    text_param = params["Text"]
    assert text_param["WFSerializationType"] == "WFTextTokenString"
    inner = text_param["Value"]
    assert "string" in inner
    assert "attachmentsByRange" in inner
    assert "￼" in inner["string"]
    assert len(inner["attachmentsByRange"]) == 1


def test_show_result_output_reference_wraps_as_token_string() -> None:
    """An Output ref in the text slot is wrapped as a single-attachment WFTextTokenString."""
    ref = Output(uuid="AAAA-BBBB", name="My Value")
    action = ShowResult(text=ref)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    text_param = params["Text"]
    assert text_param["WFSerializationType"] == "WFTextTokenString"
    inner = text_param["Value"]
    assert inner["string"] == "￼"
    attachment = next(iter(inner["attachmentsByRange"].values()))
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputName"] == "My Value"


def test_show_result_registered() -> None:
    """ShowResult is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.showresult")
    assert cls is ShowResult


# ---------------------------------------------------------------------------
# Wire-format equivalence tests vs real corpus samples
# ---------------------------------------------------------------------------


def test_show_result_empty_wire_format() -> None:
    """ShowResult() matches the empty-params sample from dictionary.xml.

    Source: samples/decoded/dictionary.xml, action index 1.
    Sample params (after normalisation): {} (no Text key).

    Apple emits ``<dict/>`` for ShowResult with no explicit text; the
    schema matches this by omitting the Text key when text is None.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][1]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.showresult"
    )
    sample_norm = _normalise(sample_action)

    schema_action = ShowResult()
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_show_result_text_template_wire_format() -> None:
    """ShowResult with a Text template matches the start_pomodoro.xml sample.

    Source: samples/decoded/start_pomodoro.xml, action index 10.
    Sample params (after normalisation):
        Text = WFTextTokenString with one attachment at {20, 1}
               referencing OutputName "Break Length" (Type: ActionOutput)
               string: "Started a timer for ￼ minutes. Your focus will
                        stay on until the timer goes off."

    OutputUUID stripped by normalisation.
    """
    if not POMODORO.exists():
        pytest.skip(f"Sample not found: {POMODORO}")

    workflow = _load(POMODORO)
    sample_action = workflow["WFWorkflowActions"][10]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.showresult"
    )
    sample_norm = _normalise(sample_action)

    break_output = Output(
        uuid="E27FB393-66E9-441D-A088-5B0674806611", name="Break Length"
    )
    schema_action = ShowResult(
        text=Text(
            "Started a timer for {break_len} minutes. "
            "Your focus will stay on until the timer goes off.",
            substitutions={"break_len": break_output},
        )
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
