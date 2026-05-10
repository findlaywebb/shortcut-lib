"""Tests for FileRename — is.workflow.actions.file.rename."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.file_rename import FileRename
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output, Text

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
RENAME_FILES = DECODED / "rename_files.xml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Strip non-deterministic fields so two action dicts are comparable."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


def _find_action(workflow: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return the first action matching identifier or raise."""
    for action in workflow["WFWorkflowActions"]:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action
    raise KeyError(f"No action with identifier {identifier!r} in sample")


# ---------------------------------------------------------------------------
# Test 1 — basic happy-path construction
# ---------------------------------------------------------------------------


def test_file_rename_basic() -> None:
    """Happy-path construction emits WFFile and WFNewFilename with correct envelopes.

    WFFile   → WFTextTokenAttachment (plain variable reference)
    WFNewFilename → WFTextTokenString (template-string envelope)
    """
    file_var = NamedVar("Repeat Item")
    name_str = "new_name.txt"

    action = FileRename(file=file_var, new_name=name_str)
    result = action.to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.file.rename"
    params = result["WFWorkflowActionParameters"]

    # WFFile should be a WFTextTokenAttachment envelope
    assert "WFFile" in params
    wf_file = params["WFFile"]
    assert wf_file["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_file["Value"]["Type"] == "Variable"
    assert wf_file["Value"]["VariableName"] == "Repeat Item"

    # WFNewFilename should be a bare string (coerce_text_field passes str through)
    assert "WFNewFilename" in params
    assert params["WFNewFilename"] == "new_name.txt"

    # UUID always present (injected by to_action_dict)
    assert "UUID" in params


def test_file_rename_with_action_input() -> None:
    """Passing an Action as file resolves to a WFTextTokenAttachment envelope."""
    from shortcut_lib.schema.actions.get_text import GetText

    get_file = GetText(text="dummy_file_source")
    action = FileRename(file=get_file, new_name="renamed.txt")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_file = params["WFFile"]
    assert wf_file["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_file["Value"]["OutputUUID"] == get_file.uuid


def test_file_rename_variable_new_name_wrapped_as_text_token_string() -> None:
    """A NamedVar new_name is wrapped in WFTextTokenString by coerce_text_field.

    All 5 configured corpus appearances of WFNewFilename use WFTextTokenString
    even for single variable references
    (rename_files.xml lines 10, 19, 51, 53, 6).
    """
    file_var = NamedVar("Repeat Item")
    name_var = NamedVar("Chosen Date")

    action = FileRename(file=file_var, new_name=name_var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_new = params["WFNewFilename"]
    assert wf_new["WFSerializationType"] == "WFTextTokenString"
    inner = wf_new["Value"]
    assert inner["string"] == "￼"
    assert "{0, 1}" in inner["attachmentsByRange"]


def test_file_rename_text_template_new_name() -> None:
    """A Text template new_name is emitted as-is (already WFTextTokenString)."""
    file_var = NamedVar("Repeat Item")
    date_var = NamedVar("Chosen Date")
    name_template = Text(
        "{date} {file}", substitutions={"date": date_var, "file": file_var}
    )

    action = FileRename(file=file_var, new_name=name_template)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_new = params["WFNewFilename"]
    assert wf_new["WFSerializationType"] == "WFTextTokenString"


def test_file_rename_no_file_no_new_name_emits_empty_params() -> None:
    """FileRename() with no args emits parameters with only UUID.

    Two dictionary.xml appearances (lines 189, 292) show file.rename
    actions with only WFFile set and no WFNewFilename — demo/placeholder
    entries.  The schema should not raise when both fields are None.
    """
    action = FileRename()
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFFile" not in params
    assert "WFNewFilename" not in params
    # Only UUID is injected
    assert list(params.keys()) == ["UUID"]


def test_file_rename_file_only_no_new_name() -> None:
    """FileRename with only file set (and no new_name) does not raise.

    Mirrors the dictionary.xml placeholder pattern (lines 189, 292):
    action has WFFile but no WFNewFilename.
    """
    file_var = NamedVar("File")
    action = FileRename(file=file_var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFFile" in params
    assert "WFNewFilename" not in params


# ---------------------------------------------------------------------------
# Test 2 — required-field validation
# ---------------------------------------------------------------------------


def test_file_rename_new_name_without_file_raises() -> None:
    """Setting new_name without file raises SchemaError.

    A rename action with a new_name but no file to rename is nonsensical;
    the schema rejects this combination early.
    """
    with pytest.raises(SchemaError, match="file must be set"):
        FileRename(file=None, new_name="oops.txt")


# ---------------------------------------------------------------------------
# Test 3 — registry lookup
# ---------------------------------------------------------------------------


def test_file_rename_registered() -> None:
    """lookup('is.workflow.actions.file.rename') returns FileRename."""
    assert lookup("is.workflow.actions.file.rename") is FileRename


# ---------------------------------------------------------------------------
# Test 4 — wire-format equivalence against rename_files.xml
# ---------------------------------------------------------------------------


def test_file_rename_wire_format_equivalence() -> None:
    """FileRename schema matches the first configured file.rename in rename_files.xml.

    Source: samples/decoded/rename_files.xml, action index 6 (UUID
    10F96164-026B-4052-8DBA-BC55CDE493AF).  Chosen as the simplest
    configured instance: WFFile = Variable "Repeat Item" (WFTextTokenAttachment),
    WFNewFilename = WFTextTokenString with two attachments (ActionOutput at
    {0,1} and Variable at {1,1}).

    The new_name here is a multi-attachment Text template. We replicate the
    wire shape using a Text with two substitution tokens.  OutputUUID is
    stripped by normalisation.

    Wire shape of the sample (after normalisation):
        WFFile = {Value: {Type: "Variable", VariableName: "Repeat Item"},
                  WFSerializationType: "WFTextTokenAttachment"}
        WFNewFilename = {Value: {string: "￼￼",
                                 attachmentsByRange: {
                                   "{0, 1}": {OutputName: "Provided Input",
                                              Type: "ActionOutput"},
                                   "{1, 1}": {Type: "Variable",
                                              VariableName: "Repeat Item"}}},
                         WFSerializationType: "WFTextTokenString"}
    """
    if not RENAME_FILES.exists():
        pytest.skip(f"Sample not found: {RENAME_FILES}")

    workflow = plistlib.loads(RENAME_FILES.read_bytes())
    # Action index 6 is the first configured file.rename in rename_files.xml.
    sample_action = workflow["WFWorkflowActions"][6]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.file.rename"
    )
    sample_norm = _normalise(sample_action)

    # Reconstruct the wire shape using schema types.
    # WFFile: NamedVar "Repeat Item" → plain WFTextTokenAttachment.
    file_var = NamedVar("Repeat Item")

    # WFNewFilename: "￼￼" — two attachment slots at {0,1} and {1,1}.
    # In the sample: ActionOutput "Provided Input" at {0,1},
    # Variable "Repeat Item" at {1,1}.
    # We use a two-substitution Text template. After _strip_output_uuids the
    # OutputUUID from the ActionOutput token is removed, leaving only
    # {OutputName, Type} for that slot — which must match the sample.
    ask_output = Output(
        uuid="65707666-0C66-41C5-B333-3ED91DE75880", name="Provided Input"
    )
    repeat_var = NamedVar("Repeat Item")
    new_name = Text(
        "{ask}{item}", substitutions={"ask": ask_output, "item": repeat_var}
    )

    schema_action = FileRename(file=file_var, new_name=new_name)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
