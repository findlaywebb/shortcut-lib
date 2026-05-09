"""Unit tests for ReadingList schema action.

Wire-format expectations are derived from two decoded corpus samples:
- ``samples/decoded/read_later.xml``:7  — WFURL via ActionOutput (If Result)
- ``samples/decoded/dictionary.xml``:211 — WFURL via ActionOutput (GIFs)

Key distinction pinned by these tests: WFURL on readinglist uses a bare
``WFTextTokenAttachment`` envelope (``coerce_value``), NOT the
``WFTextTokenString`` wrapper that ``DownloadURL.WFURL`` requires.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.reading_list import ReadingList
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
READ_LATER = DECODED / "read_later.xml"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _params(action: ReadingList) -> dict[str, Any]:
    """Extract WFWorkflowActionParameters from a ReadingList action."""
    return action.to_action_dict()["WFWorkflowActionParameters"]


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _find_action(workflow: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return the first action matching *identifier* in the workflow."""
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
    """Strip non-deterministic fields so two action dicts are comparable."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Test 1 — Happy path: URL via NamedVar
# ---------------------------------------------------------------------------


def test_reading_list_named_var_url() -> None:
    """ReadingList with a NamedVar URL emits WFURL as WFTextTokenAttachment."""
    var = NamedVar("my_url")
    action = ReadingList(url=var)
    p = _params(action)

    assert action.to_action_dict()["WFWorkflowActionIdentifier"] == (
        "is.workflow.actions.readinglist"
    )
    assert p["WFURL"]["WFSerializationType"] == "WFTextTokenAttachment"
    assert p["WFURL"]["Value"]["VariableName"] == "my_url"
    assert p["WFURL"]["Value"]["Type"] == "Variable"


# ---------------------------------------------------------------------------
# Test 2 — Happy path: URL via Output (ActionOutput)
# ---------------------------------------------------------------------------


def test_reading_list_output_url() -> None:
    """ReadingList with an Output reference emits WFURL as WFTextTokenAttachment."""
    source = GetText(text="https://example.com")
    action = ReadingList(url=source.output())
    p = _params(action)

    wfurl = p["WFURL"]
    assert wfurl["WFSerializationType"] == "WFTextTokenAttachment"
    assert wfurl["Value"]["Type"] == "ActionOutput"
    assert wfurl["Value"]["OutputUUID"] == source.uuid
    assert wfurl["Value"]["OutputName"] == "Text"


# ---------------------------------------------------------------------------
# Test 3 — Field omission when url is None
# ---------------------------------------------------------------------------


def test_reading_list_no_url_omits_wfurl() -> None:
    """When url is None, WFURL is absent from the parameter dict."""
    action = ReadingList()
    p = _params(action)

    assert "WFURL" not in p
    # UUID is always emitted by Action.to_action_dict().
    assert "UUID" in p


# ---------------------------------------------------------------------------
# Test 4 — Registry lookup
# ---------------------------------------------------------------------------


def test_reading_list_registered() -> None:
    """ReadingList is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.readinglist")
    assert cls is ReadingList


# ---------------------------------------------------------------------------
# Test 5 — Wire-format equivalence vs read_later.xml sample
# ---------------------------------------------------------------------------


def test_reading_list_wire_format_read_later() -> None:
    """ReadingList schema matches the read_later.xml corpus sample.

    Source: samples/decoded/read_later.xml — the ``is.workflow.actions.readinglist``
    action at action index 7 (within the "Reading list" ChooseFromMenu branch).

    Sample params (after normalisation):
        WFURL = {
            Value: {OutputName: "If Result", Type: "ActionOutput"},
            WFSerializationType: "WFTextTokenAttachment"
        }
    """
    if not READ_LATER.exists():
        pytest.skip(f"Sample not found: {READ_LATER}")

    workflow = _load(READ_LATER)
    sample_action = _find_action(workflow, "is.workflow.actions.readinglist")
    sample_norm = _normalise(sample_action)

    # Reconstruct: the sample's WFURL references an ActionOutput named "If Result".
    # We use Output with a placeholder UUID; _normalise strips OutputUUID.
    if_result = Output(uuid="E6255D20-248D-4930-909C-4F8C46F5D9F5", name="If Result")
    schema_action = ReadingList(url=if_result)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 6 — Wire-format equivalence vs dictionary.xml sample
# ---------------------------------------------------------------------------


def test_reading_list_wire_format_dictionary() -> None:
    """ReadingList schema matches the dictionary.xml corpus sample.

    Source: samples/decoded/dictionary.xml — first ``is.workflow.actions.readinglist``
    action (line ~3832), WFURL referencing the "GIFs" ActionOutput.

    Sample params (after normalisation):
        WFURL = {
            Value: {OutputName: "GIFs", Type: "ActionOutput"},
            WFSerializationType: "WFTextTokenAttachment"
        }
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = _find_action(workflow, "is.workflow.actions.readinglist")
    sample_norm = _normalise(sample_action)

    # Reconstruct: WFURL references the "GIFs" ActionOutput.
    gifs_output = Output(uuid="661B8C0B-D80B-4738-8A91-E53011690E28", name="GIFs")
    schema_action = ReadingList(url=gifs_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 7 — WFTextTokenAttachment (NOT WFTextTokenString) is the slot envelope
# ---------------------------------------------------------------------------


def test_readinglist_url_uses_wf_text_token_attachment_not_string() -> None:
    """WFURL on readinglist is WFTextTokenAttachment, not WFTextTokenString.

    This pins the critical distinction from DownloadURL, whose WFURL slot
    Apple reads as a WFTextTokenString (a bare WFTextTokenAttachment would
    render as "No URL Specified" at runtime for DownloadURL). The readinglist
    action accepts the bare attachment directly, as confirmed by both corpus
    samples.
    """
    source = GetClipboard()
    action = ReadingList(url=source.output())
    p = _params(action)

    wfurl = p["WFURL"]

    # Must be the bare attachment envelope — NOT the wrapped string form.
    assert wfurl["WFSerializationType"] == "WFTextTokenAttachment"
    assert wfurl["WFSerializationType"] != "WFTextTokenString"

    # And the inner token must be a direct ActionOutput reference.
    assert wfurl["Value"]["Type"] == "ActionOutput"
    # The WFTextTokenString form would instead have:
    #   {"Value": {"string": "￼", "attachmentsByRange": {...}}, ...}
    # Assert the string/attachmentsByRange wrapper is absent.
    assert "string" not in wfurl["Value"]
    assert "attachmentsByRange" not in wfurl["Value"]


# ---------------------------------------------------------------------------
# Test 8 — default_output_name
# ---------------------------------------------------------------------------


def test_reading_list_default_output_name() -> None:
    """output() resolves to 'Reading List' when no custom name is set."""
    action = ReadingList()
    assert action.output().name == "Reading List"
