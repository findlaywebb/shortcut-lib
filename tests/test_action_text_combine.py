"""Tests for TextCombine — is.workflow.actions.text.combine."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.text_combine import TextCombine
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
DICTIONARY = DECODED / "dictionary.xml"
SORT_LINES = DECODED / "sort_lines.xml"


# ---------------------------------------------------------------------------
# Helpers (inline subset — no shared conftest dependency)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file."""
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
    """Strip UUID and OutputUUID — non-deterministic fields."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Test 1 — basic happy path
# ---------------------------------------------------------------------------


def test_text_combine_basic() -> None:
    """TextCombine with a literal string input emits the correct structure."""
    result = TextCombine(input="hello").to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.text.combine"
    params = result["WFWorkflowActionParameters"]
    assert params["text"] == "hello"
    assert "WFTextSeparator" not in params  # default "New Lines" is omitted
    assert "WFTextCustomSeparator" not in params
    assert "Show-text" not in params


# ---------------------------------------------------------------------------
# Test 2 — default separator is omitted from wire output
# ---------------------------------------------------------------------------


def test_text_combine_default_separator_omitted() -> None:
    """Default "New Lines" separator is not emitted.

    Apple omits WFTextSeparator for the default value.
    dictionary.xml action index 40 confirms: no WFTextSeparator key present.
    """
    explicit_default = TextCombine(input="a\nb", separator="New Lines").to_action_dict()
    implicit_default = TextCombine(input="a\nb").to_action_dict()

    for result in (explicit_default, implicit_default):
        params = result["WFWorkflowActionParameters"]
        assert "WFTextSeparator" not in params, (
            "WFTextSeparator should be omitted for the default 'New Lines'"
        )


def test_text_combine_non_default_separator_emitted() -> None:
    """Non-default separators are emitted as WFTextSeparator."""
    result = TextCombine(input="a b", separator="Spaces").to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert params["WFTextSeparator"] == "Spaces"


# ---------------------------------------------------------------------------
# Test 3 — Custom separator requires custom_separator value
# ---------------------------------------------------------------------------


def test_text_combine_custom_requires_separator() -> None:
    """Custom separator without custom_separator raises SchemaError at emit time."""
    action = TextCombine(input="a,b,c", separator="Custom")
    with pytest.raises(SchemaError, match="custom_separator"):
        action.to_action_dict()


def test_text_combine_custom_with_separator_emits_both_keys() -> None:
    """Custom separator emits WFTextSeparator and WFTextCustomSeparator."""
    result = TextCombine(
        input="a,b,c", separator="Custom", custom_separator=","
    ).to_action_dict()
    params = result["WFWorkflowActionParameters"]

    assert params["WFTextSeparator"] == "Custom"
    assert params["WFTextCustomSeparator"] == ","


# ---------------------------------------------------------------------------
# Test 4 — invalid separator raises SchemaError with helpful message
# ---------------------------------------------------------------------------


def test_text_combine_invalid_separator_raises() -> None:
    """An unrecognised separator raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Every Character'"):
        # "Every Character" is valid for TextSplit but not TextCombine.
        TextCombine(
            input="a",
            separator="Every Character",  # ty: ignore[invalid-argument-type]
        )


def test_text_combine_invalid_separator_arbitrary_raises() -> None:
    """An arbitrary bad separator string raises SchemaError."""
    with pytest.raises(SchemaError, match="'Commas'"):
        TextCombine(
            input="a,b",
            separator="Commas",  # ty: ignore[invalid-argument-type]
        )


# ---------------------------------------------------------------------------
# Test 5 — registry lookup
# ---------------------------------------------------------------------------


def test_text_combine_registered() -> None:
    """TextCombine appears in list_actions() with the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.text.combine" in identifiers


# ---------------------------------------------------------------------------
# Test 6 — show_text field
# ---------------------------------------------------------------------------


def test_text_combine_show_text_emitted() -> None:
    """show_text=True emits the Show-text key.

    sort_lines.xml action index 0 carries Show-text = True.
    """
    result = TextCombine(input="lines", show_text=True).to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert params["Show-text"] is True


def test_text_combine_show_text_none_omitted() -> None:
    """show_text=None (default) does not emit Show-text."""
    result = TextCombine(input="lines").to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert "Show-text" not in params


# ---------------------------------------------------------------------------
# Test 7 — action-output input (chaining)
# ---------------------------------------------------------------------------


def test_text_combine_action_input_resolves() -> None:
    """Passing another Action as input resolves to WFTextTokenAttachment."""
    from shortcut_lib.schema.actions.text_split import TextSplit

    split = TextSplit(input="hello\nworld")
    combine = TextCombine(input=split, separator="Spaces")

    params = combine.to_action_dict()["WFWorkflowActionParameters"]

    assert "text" in params
    text_param = params["text"]
    assert text_param["Value"]["OutputUUID"] == split.uuid
    assert text_param["WFSerializationType"] == "WFTextTokenAttachment"


# ---------------------------------------------------------------------------
# Test 8 — wire-format equivalence (dictionary.xml action index 40)
# ---------------------------------------------------------------------------


def test_text_combine_wire_format_equivalence() -> None:
    """TextCombine schema matches dictionary.xml action index 40.

    That action has:
    - No WFTextSeparator key (default "New Lines" omitted by Apple).
    - ``text`` = WFTextTokenAttachment referencing "Updated Text" output.
    - No WFTextCustomSeparator, no Show-text.

    After normalisation (UUID and OutputUUID stripped) the dicts must match.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][40]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.text.combine"
    ), "dictionary.xml action 40 must be text.combine"
    sample_norm = _normalise(sample_action)

    # The sample's ``text`` references the "Updated Text" output (OutputUUID
    # normalised away; OutputName must match).
    updated_text_output = Output(
        uuid="43C7FE65-5A01-45C8-B018-D54939C7CB03",
        name="Updated Text",
    )
    schema_action = TextCombine(input=updated_text_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 9 — wire-format for sort_lines.xml (Show-text case)
# ---------------------------------------------------------------------------


def test_text_combine_wire_format_show_text() -> None:
    """TextCombine with show_text=True matches sort_lines.xml action index 2.

    That action has:
    - Show-text = True
    - ``text`` = WFTextTokenAttachment referencing "Files" output.
    - No WFTextSeparator key (default "New Lines" omitted).
    """
    if not SORT_LINES.exists():
        pytest.skip(f"Sample not found: {SORT_LINES}")

    workflow = _load(SORT_LINES)
    sample_action = workflow["WFWorkflowActions"][2]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.text.combine"
    ), "sort_lines.xml action 2 must be text.combine"
    sample_norm = _normalise(sample_action)

    files_output = Output(
        uuid="C94FDD5A-048F-4798-9AE8-0300F33AB1DC",
        name="Files",
    )
    schema_action = TextCombine(input=files_output, show_text=True)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
