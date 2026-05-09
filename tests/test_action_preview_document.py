"""Unit tests for PreviewDocument schema action."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.preview_document import PreviewDocument
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
TURN_TEXT_INTO_AUDIO = DECODED / "turn_text_into_audio.xml"

# ---------------------------------------------------------------------------
# Helpers
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
    """Strip non-deterministic fields (UUID, CustomOutputName, OutputUUID)."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Basic happy path
# ---------------------------------------------------------------------------


def test_preview_document_default() -> None:
    """Default PreviewDocument omits WFInput and emits the correct identifier."""
    action = PreviewDocument()
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.previewdocument"
    assert "WFInput" not in d["WFWorkflowActionParameters"]


def test_preview_document_string_input() -> None:
    """A bare string input is emitted as a plain string in WFInput."""
    action = PreviewDocument(input="hello.pdf")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFInput"] == "hello.pdf"


def test_preview_document_action_input() -> None:
    """Passing an Action as input chains via a WFTextTokenAttachment envelope."""
    source = GetText(text="some text")
    action = PreviewDocument(input=source)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["OutputUUID"] == source.uuid
    assert wf_input["Value"]["OutputName"] == "Text"
    assert wf_input["Value"]["Type"] == "ActionOutput"


def test_preview_document_output_reference() -> None:
    """Passing an Output value chains via a WFTextTokenAttachment envelope."""
    ref = Output(uuid="AAAA-BBBB", name="Spoken Audio")
    action = PreviewDocument(input=ref)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["OutputName"] == "Spoken Audio"
    assert wf_input["Value"]["Type"] == "ActionOutput"


# ---------------------------------------------------------------------------
# Registry lookup
# ---------------------------------------------------------------------------


def test_preview_document_registered() -> None:
    """PreviewDocument is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.previewdocument")
    assert cls is PreviewDocument


# ---------------------------------------------------------------------------
# Default output name
# ---------------------------------------------------------------------------


def test_preview_document_default_output_name() -> None:
    """output() resolves to 'Quick Look' when no custom name is set."""
    action = PreviewDocument()
    assert action.output().name == "Quick Look"


# ---------------------------------------------------------------------------
# Wire-format equivalence — turn_text_into_audio.xml, action index 1
# ---------------------------------------------------------------------------


def test_preview_document_wire_format() -> None:
    """PreviewDocument schema matches the ``is.workflow.actions.previewdocument`` sample.

    Source: samples/decoded/turn_text_into_audio.xml, action index 1.
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "Spoken Audio" output
        (OutputUUID stripped by normalise)

    The action has no UUID in the sample (Apple omits it for terminal actions).
    After normalisation this is irrelevant — both sides lose UUID.
    """
    if not TURN_TEXT_INTO_AUDIO.exists():
        pytest.skip(f"Sample not found: {TURN_TEXT_INTO_AUDIO}")

    workflow = _load(TURN_TEXT_INTO_AUDIO)
    sample_action = workflow["WFWorkflowActions"][1]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.previewdocument"
    )
    sample_norm = _normalise(sample_action)

    # The sample's WFInput references the "Spoken Audio" output of the
    # preceding text-to-speech action.  Build a matching Output reference
    # (UUID is normalised away, OutputName must match the sample's value).
    spoken_audio = Output(
        uuid="B92FA945-4EF4-4B13-9A6D-7A4B43BCA1A3",
        name="Spoken Audio",
    )
    schema_action = PreviewDocument(input=spoken_audio)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
