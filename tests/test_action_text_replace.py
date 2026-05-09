"""Unit tests for TextReplace schema action."""

from __future__ import annotations

from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.registry import lookup


def test_text_replace_basic() -> None:
    """Basic find/replace with plain strings emits the expected parameter keys."""
    action = TextReplace(
        input="hello world",
        find="world",
        replace="there",
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFReplaceTextFind"] == "world"
    assert params["WFReplaceTextReplace"] == "there"
    assert params["WFInput"] == "hello world"
    assert "WFReplaceTextCaseSensitive" not in params
    assert "WFReplaceTextRegularExpression" not in params


def test_text_replace_with_action_input() -> None:
    """Passing an Action as input wraps WFInput as a WFTextTokenString.

    Corpus evidence (samples/decoded/rename_files.xml:17,
    samples/decoded/dictionary.xml:42): Apple emits WFInput as a single-
    attachment WFTextTokenString, not a bare WFTextTokenAttachment.
    The schema now uses coerce_text_field to match this wire format.
    """
    source = GetText(text="some text")
    action = TextReplace(input=source, find="some", replace="any")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wf_input = params["WFInput"]
    # WFInput must be a WFTextTokenString (single-attachment templated string).
    assert wf_input["WFSerializationType"] == "WFTextTokenString"
    attachments = wf_input["Value"]["attachmentsByRange"]
    assert len(attachments) == 1
    token = next(iter(attachments.values()))
    assert token["OutputUUID"] == source.uuid
    assert token["OutputName"] == "Text"
    assert token["Type"] == "ActionOutput"


def test_text_replace_with_regex_flag() -> None:
    """Setting regex=True emits WFReplaceTextRegularExpression as True."""
    action = TextReplace(
        input="base64text",
        find=r"\s+",
        replace="",
        regex=True,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFReplaceTextRegularExpression"] is True
    assert params["WFReplaceTextFind"] == r"\s+"
    assert params["WFReplaceTextReplace"] == ""


def test_text_replace_omits_unset_flags() -> None:
    """Flags not provided are absent from the emitted parameter dict."""
    action = TextReplace(find="a", replace="b")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFReplaceTextCaseSensitive" not in params
    assert "WFReplaceTextRegularExpression" not in params


def test_text_replace_registered() -> None:
    """TextReplace must be discoverable via the action registry."""
    cls = lookup("is.workflow.actions.text.replace")
    assert cls is TextReplace
