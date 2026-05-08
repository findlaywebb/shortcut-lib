"""Unit tests for Base64Encode schema action."""

from __future__ import annotations

from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.registry import lookup


def test_base64_encode_default() -> None:
    """Default encode omits WFEncodeMode and emits WFInput as a plain string."""
    action = Base64Encode(input="hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert action.to_action_dict()["WFWorkflowActionIdentifier"] == (
        "is.workflow.actions.base64encode"
    )
    assert params["WFInput"] == "hello"
    # WFEncodeMode must be absent when mode is the default ("Encode").
    assert "WFEncodeMode" not in params


def test_base64_decode_mode() -> None:
    """mode='Decode' emits WFEncodeMode='Decode' in the parameter dict."""
    action = Base64Encode(input="aGVsbG8=", mode="Decode")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFEncodeMode"] == "Decode"
    assert params["WFInput"] == "aGVsbG8="


def test_base64_with_action_input() -> None:
    """Passing an Action as input chains the output reference into WFInput."""
    source = GetText(text="markdown body")
    action = Base64Encode(input=source)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    # coerce_value on an Action yields its output token in WFTextTokenAttachment form.
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["OutputUUID"] == source.uuid
    assert wf_input["Value"]["OutputName"] == "Text"
    assert wf_input["Value"]["Type"] == "ActionOutput"
    assert "WFEncodeMode" not in params


def test_base64_registered() -> None:
    """Base64Encode is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.base64encode")
    assert cls is Base64Encode


def test_base64_default_output_name() -> None:
    """output() resolves to 'Base64 Encoded' when no custom name is set."""
    action = Base64Encode()
    assert action.output().name == "Base64 Encoded"


def test_base64_no_input_omits_wfinput() -> None:
    """When input is None, WFInput is absent from the parameters."""
    action = Base64Encode()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params
