"""Tests for the Comment action schema."""

from __future__ import annotations

from shortcut_lib.schema.actions.comment import Comment
from shortcut_lib.schema.registry import lookup


def test_comment_emits_text() -> None:
    """Comment.to_action_dict() emits WFCommentActionText with the given text."""
    result = Comment(text="hello").to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert params["WFCommentActionText"] == "hello"


def test_comment_multiline_preserved() -> None:
    """Newlines inside Comment.text are preserved verbatim."""
    result = Comment(text="line 1\nline 2").to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert params["WFCommentActionText"] == "line 1\nline 2"


def test_comment_registered() -> None:
    """Comment is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.comment")
    assert cls is Comment
