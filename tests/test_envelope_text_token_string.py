"""Regression: variable-ref slots must emit single-attachment WFTextTokenString.

Apple's runtime reads several parameter slots as ``WFTextTokenString``;
a bare ``WFTextTokenAttachment`` envelope imports as a disconnected
field (URL slot becomes "No URL Specified"; date slot produces an
empty string; etc.). The shared
:func:`shortcut_lib.schema.base.coerce_text_field` helper rewraps
``Action`` / ``Value`` references as a single-attachment templated
string. This file pins the wire shape for every action that routes a
parameter through that helper so we catch future drift.

If you add a new action whose parameter is a WFTextTokenString slot in
Apple's samples, add a case here.
"""

from __future__ import annotations

from typing import Any

import pytest

from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.comment import Comment
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.values import CurrentDate, NamedVar


def _params(action: Any) -> dict:
    return action.to_action_dict()["WFWorkflowActionParameters"]


def _assert_single_attachment(envelope: dict, expected_token: dict) -> None:
    """Assert the envelope is a single-attachment WFTextTokenString."""
    assert envelope["WFSerializationType"] == "WFTextTokenString"
    assert envelope["Value"]["string"] == "￼"
    attachments = envelope["Value"]["attachmentsByRange"]
    assert list(attachments) == ["{0, 1}"]
    assert attachments["{0, 1}"] == expected_token


@pytest.mark.parametrize(
    "build_action, slot, expected_token",
    [
        (
            lambda: GetText(text=NamedVar("X")),
            "WFTextActionText",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: ShowNotification(body=NamedVar("X")),
            "WFNotificationActionBody",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: ShowNotification(title=NamedVar("X"), body="ok"),
            "WFNotificationActionTitle",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: UseModel(prompt=NamedVar("X")),
            "WFLLMPrompt",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: AskForInput(prompt=NamedVar("X")),
            "WFAskActionPrompt",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: Comment(text=NamedVar("X")),
            "WFCommentActionText",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: TextReplace(input=NamedVar("Src"), find=NamedVar("X"), replace="-"),
            "WFReplaceTextFind",
            {"Type": "Variable", "VariableName": "X"},
        ),
        (
            lambda: TextReplace(input=NamedVar("Src"), find="x", replace=NamedVar("Y")),
            "WFReplaceTextReplace",
            {"Type": "Variable", "VariableName": "Y"},
        ),
        (
            lambda: FormatDate(input=CurrentDate),
            "WFDate",
            {"Type": "CurrentDate"},
        ),
    ],
)
def test_variable_ref_emits_single_attachment_string(
    build_action: Any, slot: str, expected_token: dict
) -> None:
    """Each templated-string slot wraps a NamedVar/MagicVar as WFTextTokenString."""
    _assert_single_attachment(_params(build_action())[slot], expected_token)


@pytest.mark.parametrize(
    "build_action, slot",
    [
        (lambda: GetText(text="hello"), "WFTextActionText"),
        (lambda: ShowNotification(body="hello"), "WFNotificationActionBody"),
        (lambda: UseModel(prompt="hello"), "WFLLMPrompt"),
        (lambda: AskForInput(prompt="hello"), "WFAskActionPrompt"),
        (lambda: Comment(text="hello"), "WFCommentActionText"),
        (
            lambda: TextReplace(input=NamedVar("Src"), find="hello", replace="-"),
            "WFReplaceTextFind",
        ),
    ],
)
def test_plain_string_passes_through(build_action: Any, slot: str) -> None:
    """Plain string literals are emitted as bare strings (matches Apple's samples)."""
    assert _params(build_action())[slot] == "hello"
