"""Tier 0 schema tests — control flow, values, composition, encoding."""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib import decode_file, encode_to_bplist
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import (
    CurrentDate,
    If,
    NamedVar,
    Otherwise,  # noqa: F401  — kept for explicit-import discoverability
    Output,
    Quantity,
    RepeatCount,
    RepeatEach,
    RunWorkflow,
    Text,
    TimeOffset,
    describe_action,
    list_actions,
)
from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.set_clipboard import SetClipboard

SAMPLES = Path(__file__).parent.parent / "samples"


def test_minimal_shortcut_encodes_and_round_trips() -> None:
    """A 2-action shortcut emits a valid bplist that decodes back unchanged."""
    s = Shortcut(name="Dictate Demo", surfaces=["watch", "widget"])
    text = s.add(DictateText())
    s.add(SetClipboard(input=text))

    workflow = s.to_workflow()
    bplist = encode_to_bplist(workflow)
    assert plistlib.loads(bplist) == workflow

    actions = workflow["WFWorkflowActions"]
    assert len(actions) == 2
    assert actions[0]["WFWorkflowActionIdentifier"] == "is.workflow.actions.dictatetext"
    assert (
        actions[1]["WFWorkflowActionIdentifier"] == "is.workflow.actions.setclipboard"
    )
    # Reference resolution: SetClipboard's WFInput points to DictateText's UUID
    set_input = actions[1]["WFWorkflowActionParameters"]["WFInput"]
    assert (
        set_input["Value"]["OutputUUID"]
        == actions[0]["WFWorkflowActionParameters"]["UUID"]
    )


def test_signed_round_trip_via_shortcuts_cli(tmp_path: Path) -> None:
    """Signing through the macOS CLI produces a re-decodable file.

    Apple's bplist format doesn't carry the shortcut name — the name comes
    from the imported file's filename. We only assert structural integrity
    here.
    """
    s = Shortcut(name="Signed Demo")
    s.add(DictateText())
    out = tmp_path / "Signed Demo.shortcut"
    s.save_signed(out)
    assert out.exists()
    decoded = decode_file(out)
    assert "WFWorkflowActions" in decoded.workflow
    assert decoded.signing_issuer.startswith("Apple")


def test_if_emits_flat_grouping_with_close() -> None:
    """If(then=...) with no else emits open + body + end_if (3 actions)."""
    s = Shortcut(name="If Demo")
    text = s.add(DictateText())
    s.add(
        If(
            operand=text,
            op="==",
            value="hello",
            then=[SetClipboard(input="matched")],
        )
    )
    actions = s.to_workflow()["WFWorkflowActions"]

    # 1 dictate + 1 if-open + 1 set-clipboard + 1 if-close = 4
    assert len(actions) == 4
    if_open = actions[1]["WFWorkflowActionParameters"]
    body = actions[2]
    if_close = actions[3]["WFWorkflowActionParameters"]
    assert if_open["WFControlFlowMode"] == 0
    assert if_close["WFControlFlowMode"] == 2
    assert if_open["GroupingIdentifier"] == if_close["GroupingIdentifier"]
    assert body["WFWorkflowActionIdentifier"] == "is.workflow.actions.setclipboard"


def test_if_else_includes_middle_marker() -> None:
    """If with otherwise emits open + then-body + else-marker + else-body + close."""
    s = Shortcut(name="If/Else")
    s.add(
        If(
            operand=NamedVar("x"),
            op="==",
            value=1,
            then=[SetClipboard(input="one")],
            otherwise=[SetClipboard(input="other")],
        )
    )
    actions = s.to_workflow()["WFWorkflowActions"]
    modes = [
        a["WFWorkflowActionParameters"].get("WFControlFlowMode")
        for a in actions
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.conditional"
    ]
    assert modes == [0, 1, 2]


def test_repeat_count_round_trips() -> None:
    s = Shortcut(name="Repeat")
    s.add(RepeatCount(count=3, body=[SetClipboard(input="hi")]))
    actions = s.to_workflow()["WFWorkflowActions"]
    assert actions[0]["WFWorkflowActionParameters"]["WFRepeatCount"] == 3
    assert actions[-1]["WFWorkflowActionParameters"]["WFControlFlowMode"] == 2


def test_repeat_each_with_variable_input() -> None:
    s = Shortcut(name="ForEach")
    items = NamedVar("MyList")
    s.add(RepeatEach(items=items, body=[SetClipboard(input="row")]))
    head_input = s.to_workflow()["WFWorkflowActions"][0]["WFWorkflowActionParameters"][
        "WFInput"
    ]
    assert head_input["Type"] == "Variable"
    assert head_input["Variable"]["Value"]["VariableName"] == "MyList"


def test_text_template_computes_utf16_ranges() -> None:
    """Text("hello {x}") puts the placeholder at UTF-16 offset 6."""
    out_ref = Output(uuid="ABC", name="Foo")
    text = Text("hello {x} world", substitutions={"x": out_ref})
    param = text.to_param()
    value: dict[str, Any] = param["Value"]
    assert value["string"] == "hello ￼ world"
    assert "{6, 1}" in value["attachmentsByRange"]
    token = value["attachmentsByRange"]["{6, 1}"]
    assert token == {"OutputName": "Foo", "OutputUUID": "ABC", "Type": "ActionOutput"}


def test_text_template_with_emoji_handles_supplementary_chars() -> None:
    """🎉 (U+1F389) is two UTF-16 units; later placeholders shift."""
    out_ref = Output(uuid="X", name="V")
    text = Text("🎉 {v}", substitutions={"v": out_ref})
    value = text.to_param()["Value"]
    # "🎉" is 2 UTF-16 units, then space = 1 → placeholder at offset 3
    assert "{3, 1}" in value["attachmentsByRange"]


def test_text_missing_substitution_raises() -> None:
    from shortcut_lib.schema import SchemaError

    with pytest.raises(SchemaError, match="no substitution"):
        Text("hello {missing}").to_param()


def test_quantity_with_variable_magnitude() -> None:
    q = Quantity(magnitude=NamedVar("N"), unit="min")
    param = q.to_param()
    assert param["WFSerializationType"] == "WFQuantityFieldValue"
    assert param["Value"]["Unit"] == "min"
    assert param["Value"]["Magnitude"]["VariableName"] == "N"


def test_time_offset_with_variable_value() -> None:
    o = TimeOffset(operation="Add", unit="Minute", value=Output(uuid="U", name="N"))
    param = o.to_param()
    assert param["WFSerializationType"] == "WFTimeOffsetValue"
    inner = param["Value"]
    assert inner["Operation"] == "Add"
    assert inner["Unit"] == "Minute"
    assert inner["Value"]["OutputUUID"] == "U"


def test_run_workflow_self_reference_resolves_at_emit() -> None:
    s = Shortcut(name="Recursive")
    s.add(RunWorkflow(target="self", input="payload"))
    actions = s.to_workflow()["WFWorkflowActions"]
    wf = actions[0]["WFWorkflowActionParameters"]["WFWorkflow"]
    assert wf["isSelf"] is True
    assert wf["workflowIdentifier"] == s.workflow_identifier
    assert wf["workflowName"] == "Recursive"


def test_run_workflow_cross_shortcut_reference() -> None:
    helper = Shortcut(name="Helper")
    orchestrator = Shortcut(name="Orchestrator")
    orchestrator.add(RunWorkflow(target=helper, input="x"))
    wf = orchestrator.to_workflow()["WFWorkflowActions"][0][
        "WFWorkflowActionParameters"
    ]["WFWorkflow"]
    assert wf["isSelf"] is False
    assert wf["workflowIdentifier"] == helper.workflow_identifier
    assert wf["workflowName"] == "Helper"


def test_currentdate_is_a_singleton_token() -> None:
    """Magic vars share their Type identity; tokens stay simple."""
    token = CurrentDate.to_token()
    assert token == {"Type": "CurrentDate"}


def test_registry_lists_tier0_actions() -> None:
    listing = list_actions()
    idents = {row["identifier"] for row in listing}
    assert "is.workflow.actions.dictatetext" in idents
    assert "is.workflow.actions.setclipboard" in idents


def test_describe_action_returns_parameter_signature() -> None:
    desc = describe_action("DictateText")
    assert desc["identifier"] == "is.workflow.actions.dictatetext"
    param_names = {p["name"] for p in desc["parameters"]}
    assert "locale" in param_names
    assert "stop_listening" in param_names
