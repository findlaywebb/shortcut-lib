"""UseModel + Writing Tools tests."""

from __future__ import annotations

import pytest

from shortcut_lib.schema import NamedVar, SchemaError, list_actions
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.actions.writing_tools import (
    AdjustTone,
    FormatList,
    RewriteText,
    SummarizeText,
)


def test_use_model_default_emits_apple_intelligence() -> None:
    action = UseModel(prompt="Hello").to_action_dict()
    params = action["WFWorkflowActionParameters"]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.askllm"
    assert params["WFLLMModel"] == "Apple Intelligence"
    assert params["WFLLMPrompt"] == "Hello"


def test_use_model_with_named_var_prompt() -> None:
    action = UseModel(prompt=NamedVar("Note")).to_action_dict()
    prompt = action["WFWorkflowActionParameters"]["WFLLMPrompt"]
    assert prompt["Value"]["VariableName"] == "Note"
    assert prompt["WFSerializationType"] == "WFTextTokenAttachment"


def test_use_model_alternate_model() -> None:
    action = UseModel(prompt="x", model="Private Cloud Compute").to_action_dict()
    assert action["WFWorkflowActionParameters"]["WFLLMModel"] == "Private Cloud Compute"


def test_use_model_requires_prompt() -> None:
    with pytest.raises(SchemaError, match="requires `prompt`"):
        UseModel().to_action_dict()


def test_adjust_tone_emits_text_and_tone() -> None:
    action = AdjustTone(text="hello world", tone="friendly").to_action_dict()
    params = action["WFWorkflowActionParameters"]
    assert params["text"] == "hello world"
    assert params["tone"] == "friendly"


def test_format_list_minimal() -> None:
    params = FormatList(text="apples bananas").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["text"] == "apples bananas"
    assert "tone" not in params


def test_rewrite_text_minimal() -> None:
    params = RewriteText(text="bad grammar").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["text"] == "bad grammar"


def test_summarize_text_default_omits_summary_type() -> None:
    params = SummarizeText(text="long text").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["text"] == "long text"
    assert "summaryType" not in params


def test_summarize_text_with_key_points() -> None:
    params = SummarizeText(
        text="long text", summary_type="createKeyPoints"
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["summaryType"] == "createKeyPoints"


def test_writing_tools_require_text() -> None:
    for cls in (AdjustTone, FormatList, RewriteText, SummarizeText):
        with pytest.raises(SchemaError, match="require `text`"):
            cls().to_action_dict()


def test_all_registered() -> None:
    idents = {row["identifier"] for row in list_actions()}
    assert "is.workflow.actions.askllm" in idents
    for tail in (
        "AdjustToneIntent",
        "FormatListIntent",
        "RewriteTextIntent",
        "SummarizeTextIntent",
    ):
        assert (
            f"com.apple.WritingTools.WritingToolsAppIntentsExtension.{tail}" in idents
        )
