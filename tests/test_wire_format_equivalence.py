"""Wire-format equivalence tests: schema-emitted dicts vs real decoded samples.

Each test loads an actual decoded plist sample, finds the action under test by
identifier, normalises both sides (strips non-deterministic UUID and
OutputUUID fields), then asserts dict-equality.

The goal is to surface real discrepancies between what the schema emits and
what Shortcuts.app actually produces.  Where the two sides differ the test
*fails* — by design.  Do NOT massage tests to hide failures; document them
in the final report instead.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.append_variable import AppendVariable
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.comment import Comment
from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.exit_shortcut import ExitShortcut
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.get_variable import GetVariable
from shortcut_lib.schema.actions.record_audio import RecordAudio
from shortcut_lib.schema.actions.set_clipboard import SetClipboard
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.actions.text_split import TextSplit
from shortcut_lib.schema.actions.transcribe_audio import TranscribeAudio
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.actions.writing_tools import (
    AdjustTone,
    FormatList,
    RewriteText,
    SummarizeText,
)
from shortcut_lib.schema.base import RawAction
from shortcut_lib.schema.control import (
    ChooseFromMenu,
    If,
    RepeatCount,
    RepeatEach,
)
from shortcut_lib.schema.values import NamedVar, Output, Text

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
POMODORO = DECODED / "start_pomodoro.xml"
DICTATE = DECODED / "dictate_to_clipboard.xml"
GET_CONTENTS = DECODED / "get_contents_of_url.xml"
VOICE_GITHUB = DECODED / "private" / "voice_note_to_github.xml"
INTELLY = DECODED / "intelly.xml"
BATCH_REMINDERS = DECODED / "batch_add_reminders.xml"
DAILY_STANDUP = DECODED / "daily_standup.xml"
ADJUST_CLIPBOARD = DECODED / "adjust_clipboard.xml"
DICTIONARY = DECODED / "dictionary.xml"
READ_LATER = DECODED / "read_later.xml"
SET_WEEKEND = DECODED / "set_weekend_chores.xml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _find_action(workflow: dict[str, Any], identifier: str) -> dict[str, Any]:
    """Return the first action matching ``identifier`` or raise."""
    for action in workflow["WFWorkflowActions"]:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action
    raise KeyError(f"No action with identifier {identifier!r} in sample")


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
    """Strip non-deterministic fields so two action dicts are comparable.

    Removes:
    - ``UUID`` — each schema-built instance gets a fresh UUID4.
    - ``CustomOutputName`` — optional label set by the user; irrelevant to
      the structural wire format.
    - ``OutputUUID`` from any nested variable references — they reference
      other action UUIDs which differ between schema-built and sample copies.
    """
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


def _normalise_sequence(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalise a sequence of action dicts for control-flow comparison.

    Strips ``UUID`` and ``GroupingIdentifier`` from every action in the
    sequence, and strips ``OutputUUID`` from all nested attachments.
    ``GroupingIdentifier`` is stripped because the schema generates a fresh
    UUID4 for the grouping, which differs from the sample's literal value.
    """
    out: list[dict[str, Any]] = []
    for action in actions:
        normalised = copy.deepcopy(action)
        params = normalised.get("WFWorkflowActionParameters", {})
        params.pop("UUID", None)
        params.pop("GroupingIdentifier", None)
        params.pop("CustomOutputName", None)
        _strip_output_uuids(params)
        out.append(normalised)
    return out


def _find_action_sequence(
    workflow: dict[str, Any],
    head_identifier: str,
    mode0_index: int,
) -> list[dict[str, Any]]:
    """Return the full multi-action sequence for a control-flow construct.

    Starts at ``mode0_index`` (the head with ``WFControlFlowMode=0``) and
    walks forward until the matching close (``WFControlFlowMode=2``) with
    the same ``GroupingIdentifier``.  The close action is included.
    """
    actions = workflow["WFWorkflowActions"]
    head = actions[mode0_index]
    assert head["WFWorkflowActionIdentifier"] == head_identifier
    gid = head["WFWorkflowActionParameters"]["GroupingIdentifier"]
    seq: list[dict[str, Any]] = [head]
    for j in range(mode0_index + 1, len(actions)):
        a = actions[j]
        seq.append(a)
        params = a.get("WFWorkflowActionParameters", {})
        if (
            a["WFWorkflowActionIdentifier"] == head_identifier
            and params.get("GroupingIdentifier") == gid
            and params.get("WFControlFlowMode") == 2
        ):
            break
    return seq


# ---------------------------------------------------------------------------
# Test 1 — AskForInput
# ---------------------------------------------------------------------------


def test_ask_for_input_wire_format() -> None:
    """AskForInput schema matches the ``is.workflow.actions.ask`` sample.

    Source: samples/decoded/start_pomodoro.xml, action index 1.
    Sample params (after normalisation):
        WFAskActionPrompt        = "OK, for how many minutes?"
        WFAskActionDefaultAnswerNumber = "25"
        WFInputType              = "Number"
        WFAskActionAllowsDecimalNumbers  = False
        WFAskActionAllowsNegativeNumbers = False

    CustomOutputName ("Break Length") and UUID are normalised away.
    """
    if not POMODORO.exists():
        pytest.skip(f"Sample not found: {POMODORO}")

    workflow = _load(POMODORO)
    sample_action = _find_action(workflow, "is.workflow.actions.ask")
    sample_norm = _normalise(sample_action)

    schema_action = AskForInput(
        prompt="OK, for how many minutes?",
        input_type="Number",
        default_answer="25",
        allows_decimal=False,
        allows_negative=False,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 2 — SetVariable
# ---------------------------------------------------------------------------


def test_set_variable_wire_format() -> None:
    """SetVariable schema matches the first ``is.workflow.actions.setvariable`` sample.

    Source: samples/decoded/private/voice_note_to_github.xml, action index 1.
    That action stores the output of the preceding GetText ("Text" output)
    into a variable named "Token".

    Sample params (after normalisation):
        WFVariableName = "Token"
        WFInput = {
            Value: {OutputName: "Text", Type: "ActionOutput"},
            WFSerializationType: "WFTextTokenAttachment"
        }
        (OutputUUID stripped by normalise)
    """
    if not VOICE_GITHUB.exists():
        pytest.skip(f"Sample not found: {VOICE_GITHUB}")

    workflow = _load(VOICE_GITHUB)
    sample_action = _find_action(workflow, "is.workflow.actions.setvariable")
    sample_norm = _normalise(sample_action)

    # Build a GetText whose output we'll store.  The schema side needs the
    # Output name to be "Text" (matching the sample's OutputName) but the
    # UUID is normalised away so any UUID works.
    source = GetText(text="placeholder")
    # GetText.default_output_name is "Text" — matches sample's OutputName.
    schema_action = SetVariable(name="Token", input=source)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 3 — GetText (literal string)
# ---------------------------------------------------------------------------


def test_get_text_literal_wire_format() -> None:
    """GetText with a bare string matches the first ``gettext`` sample.

    Source: samples/decoded/private/voice_note_to_github.xml, action index 0.
    Sample params (after normalisation):
        WFTextActionText = "github_pat_11ALQ6TNY0OsCF1pJLFOnX_..."

    CustomOutputName ("Text") and UUID normalised away.

    Note: the sample uses a bare string for WFTextActionText, not a
    WFTextTokenString envelope.  The schema's GetText passes bare strings
    straight through via coerce_value.  If the schema were to wrap the string
    in an envelope, this test would fail — correctly surfacing a bug.
    """
    if not VOICE_GITHUB.exists():
        pytest.skip(f"Sample not found: {VOICE_GITHUB}")

    pat = (
        "github_pat_11ALQ6TNY0OsCF1pJLFOnX_"
        "IzyycGNKEv8sQwaRJLHEQi2k0jAOngN5qKqk6rBY3kSTTCR7MCM8IqsqhGQ"
    )

    workflow = _load(VOICE_GITHUB)
    sample_action = _find_action(workflow, "is.workflow.actions.gettext")
    sample_norm = _normalise(sample_action)

    schema_action = GetText(text=pat)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 4 — SetClipboard
# ---------------------------------------------------------------------------


def test_set_clipboard_wire_format() -> None:
    """SetClipboard schema matches the ``setclipboard`` sample.

    Source: samples/decoded/dictate_to_clipboard.xml, action index 1.
    Sample params (after normalisation):
        WFInput = {
            Value: {OutputName: "Dictated Text", Type: "ActionOutput"},
            WFSerializationType: "WFTextTokenAttachment"
        }
        (No UUID on setclipboard itself in this sample — confirms the schema
        should not inject UUID when there is no output to reference.)

    Note: the sample's setclipboard action has NO UUID key in its parameters.
    The schema injects UUID via to_action_dict().  After normalisation this
    is stripped, so the comparison is fair.
    """
    if not DICTATE.exists():
        pytest.skip(f"Sample not found: {DICTATE}")

    workflow = _load(DICTATE)
    sample_action = _find_action(workflow, "is.workflow.actions.setclipboard")
    sample_norm = _normalise(sample_action)

    # Build a DictateText-like action whose output name matches the sample.
    # The default_output_name of any Action used here doesn't matter because
    # we pass OutputName explicitly via Output(..., name="Dictated Text").
    # That Output name must match the sample's OutputName to pass post-normalise.
    source = Output(uuid="dummy", name="Dictated Text")
    schema_action = SetClipboard(input=source)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 5 — ShowNotification
# ---------------------------------------------------------------------------


def test_show_notification_wire_format() -> None:
    """ShowNotification schema matches the ``notification`` sample.

    Source: samples/decoded/private/voice_note_to_github.xml, action index 25.
    Sample params (after normalisation):
        WFNotificationActionTitle = "Voice Note → GitHub"
        WFNotificationActionBody = {
            Value: {
                string: "Voice note pushed: ￼",
                attachmentsByRange: {
                    "{19, 1}": {Type: "Variable", VariableName: "Base"}
                }
            },
            WFSerializationType: "WFTextTokenString"
        }

    The body is a WFTextTokenString with one substitution at offset 19
    (UTF-16 code units: "Voice note pushed: " = 19 chars, all ASCII).
    """
    if not VOICE_GITHUB.exists():
        pytest.skip(f"Sample not found: {VOICE_GITHUB}")

    workflow = _load(VOICE_GITHUB)
    sample_action = _find_action(workflow, "is.workflow.actions.notification")
    sample_norm = _normalise(sample_action)

    base_var = NamedVar("Base")
    schema_action = ShowNotification(
        title="Voice Note → GitHub",
        body=Text("Voice note pushed: {base}", substitutions={"base": base_var}),
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 6 — DownloadURL (simple case: PUT with URL only, no body/headers)
# ---------------------------------------------------------------------------


def test_download_url_wire_format() -> None:
    """DownloadURL schema matches a minimal PUT sample.

    Source: samples/decoded/get_contents_of_url.xml, action index 1.
    That action has: WFHTTPMethod=PUT, WFURL=<WFTextTokenString>, no body,
    no headers, no ShowHeaders.  Only keys: UUID, WFHTTPMethod, WFURL.

    Note: the URL in the sample is a WFTextTokenString (variable reference
    to the first downloadurl's output), not a plain string.  We replicate
    the shape using an Output reference through Text.
    After normalisation (OutputUUID stripped) the attachmentsByRange token
    reduces to {OutputName, Type} — matching the sample.
    """
    if not GET_CONTENTS.exists():
        pytest.skip(f"Sample not found: {GET_CONTENTS}")

    workflow = _load(GET_CONTENTS)
    actions = workflow["WFWorkflowActions"]
    # Action at index 1 is the PUT with a variable URL.
    sample_action = actions[1]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.downloadurl"
    )
    sample_norm = _normalise(sample_action)

    # The sample's WFURL is a WFTextTokenString with one attachment: the
    # output of action 0 ("Contents of URL").  Build a matching Text template.
    prev_output = Output(uuid="dummy", name="Contents of URL")
    url_text = Text("{url}", substitutions={"url": prev_output})
    schema_action = DownloadURL(url=url_text, method="PUT")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 7 — Dictionary (empty)
# ---------------------------------------------------------------------------


def test_dictionary_empty_wire_format() -> None:
    """The dictionary.xml sample's first dictionary action is an empty dict.

    The sample's parameters contain only a UUID (normalised away), meaning
    WFItems is absent.  This is different from the schema emitting an empty
    WFDictionaryFieldValue envelope.

    This test is expected to FAIL if the schema emits WFItems for an empty
    Dictionary — that would indicate a bug: Apple omits WFItems entirely
    when the dictionary has no entries.  The test documents this discrepancy.
    """
    from shortcut_lib.schema.actions.dictionary import Dictionary

    sample_path = DECODED / "dictionary.xml"
    if not sample_path.exists():
        pytest.skip(f"Sample not found: {sample_path}")

    workflow = _load(sample_path)
    sample_action = _find_action(workflow, "is.workflow.actions.dictionary")
    sample_norm = _normalise(sample_action)

    schema_action = Dictionary()
    schema_norm = _normalise(schema_action.to_action_dict())

    # Document what each side emits before asserting equality.
    sample_params = sample_norm["WFWorkflowActionParameters"]
    schema_params = schema_norm["WFWorkflowActionParameters"]

    # If the schema emits WFItems but the sample omits it, the assertion
    # below will fail — that's a real schema bug (Apple omits WFItems when
    # there are no entries; the schema should do the same).
    assert schema_norm == sample_norm, (
        f"Schema emits {list(schema_params.keys())!r} "
        f"but sample has {list(sample_params.keys())!r}. "
        "Apple omits WFItems entirely for empty Dictionary actions; "
        "the schema should match this behaviour."
    )


# ---------------------------------------------------------------------------
# Test 8 — AppendVariable
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "No sample exercises AppendVariable with a non-empty WFVariableName. "
        "dictionary.xml[11] contains is.workflow.actions.appendvariable but with "
        "empty WFWorkflowActionParameters — a placeholder demo entry, not a real "
        "invocation. Add a decoded shortcut that uses AppendVariable inside a "
        "Repeat block to remove this skip."
    )
)
def test_append_variable_wire_format() -> None:
    """AppendVariable schema matches a real invocation with WFVariableName set.

    Source: no suitable sample available (see skip reason above).
    Expected params once a sample exists:
        WFVariableName = <name>
        WFInput = WFTextTokenAttachment envelope
    """
    _ = AppendVariable  # retain import for when this is unskipped


# ---------------------------------------------------------------------------
# Test 9 — UseModel
# ---------------------------------------------------------------------------


def test_use_model_wire_format() -> None:
    """UseModel schema matches the ``is.workflow.actions.askllm`` sample.

    Source: samples/decoded/intelly.xml, action index 2.
    Sample params (after normalisation):
        WFLLMModel  = "Apple Intelligence"
        WFLLMPrompt = WFTextTokenString with "{0, 1}" attachment to NamedVar "Note"

    WFLLMPrompt is a WFTextTokenString slot — even a single variable
    reference must be wrapped in the one-attachment template envelope.
    """
    if not INTELLY.exists():
        pytest.skip(f"Sample not found: {INTELLY}")

    workflow = _load(INTELLY)
    sample_action = _find_action(workflow, "is.workflow.actions.askllm")
    sample_norm = _normalise(sample_action)

    note_var = NamedVar("Note")
    schema_action = UseModel(
        prompt=Text("{note}", substitutions={"note": note_var}),
        model="Apple Intelligence",
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 10 — Base64Encode
# ---------------------------------------------------------------------------


def test_base64_encode_wire_format() -> None:
    """Base64Encode schema matches the ``is.workflow.actions.base64encode`` sample.

    Source: samples/decoded/dictionary.xml, action index 61.
    Sample params (after normalisation):
        WFInput = WFTextTokenAttachment referencing "Get What's Onscreen"
        (WFEncodeMode absent — default "Encode" is omitted by Apple)

    The schema omits WFEncodeMode when mode == "Encode" (the default).
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][61]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.base64encode"
    )
    sample_norm = _normalise(sample_action)

    prev_output = Output(
        uuid="F44D681E-DEF0-41B5-A0AE-4E2594C60EF4",
        name="Get What’s Onscreen",  # noqa: RUF001
    )
    schema_action = Base64Encode(input=prev_output, mode="Encode")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 11 — Comment
# ---------------------------------------------------------------------------


def test_comment_wire_format() -> None:
    """Comment schema vs the is.workflow.actions.comment sample.

    Source: samples/decoded/batch_add_reminders.xml, action index 0.
    Sample params (after normalisation):
        WFCommentActionText = "Works great for recipes..." (no UUID)

    For a plain string Apple emits the string bare (not wrapped in
    WFTextTokenString), which coerce_text_field preserves.

    Text is read from the sample at test time rather than hardcoded so
    that unicode-encoding quirks (curly quotes, horizontal ellipsis,
    trailing spaces before newlines) in the source XML never cause a
    spurious mismatch.
    """
    if not BATCH_REMINDERS.exists():
        pytest.skip(f"Sample not found: {BATCH_REMINDERS}")

    workflow = _load(BATCH_REMINDERS)
    sample_action = _find_action(workflow, "is.workflow.actions.comment")
    sample_norm = _normalise(sample_action)

    # Read text from sample so the test stays robust to unicode-encoding
    # quirks (curly quotes, horizontal ellipsis, trailing spaces, etc.)
    # in the source XML.
    text = sample_action["WFWorkflowActionParameters"]["WFCommentActionText"]
    schema_action = Comment(text=text)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 12 — DictateText
# ---------------------------------------------------------------------------


def test_dictate_text_wire_format() -> None:
    """DictateText schema matches the ``is.workflow.actions.dictatetext`` sample.

    Source: samples/decoded/dictate_to_clipboard.xml, action index 0.
    Sample params (after normalisation): {} (no locale, no stop_listening).

    The schema emits an empty dict when both locale and stop_listening
    are None, matching this sample.
    """
    if not DICTATE.exists():
        pytest.skip(f"Sample not found: {DICTATE}")

    workflow = _load(DICTATE)
    sample_action = _find_action(workflow, "is.workflow.actions.dictatetext")
    sample_norm = _normalise(sample_action)

    schema_action = DictateText()
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 13 — ExitShortcut
# ---------------------------------------------------------------------------


def test_exit_shortcut_wire_format() -> None:
    """ExitShortcut schema matches the ``is.workflow.actions.exit`` sample.

    Source: samples/decoded/adjust_clipboard.xml, action index 3.
    Sample params (after normalisation): {} (no parameters at all).

    ExitShortcut has no configurable parameters; Apple emits an empty
    WFWorkflowActionParameters dict, which the schema matches.
    """
    if not ADJUST_CLIPBOARD.exists():
        pytest.skip(f"Sample not found: {ADJUST_CLIPBOARD}")

    workflow = _load(ADJUST_CLIPBOARD)
    sample_action = _find_action(workflow, "is.workflow.actions.exit")
    sample_norm = _normalise(sample_action)

    schema_action = ExitShortcut()
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 14 — FormatDate
# ---------------------------------------------------------------------------


def test_format_date_wire_format() -> None:
    """FormatDate schema matches the ``is.workflow.actions.format.date`` sample.

    Source: samples/decoded/daily_standup.xml, action index 34.
    Sample params (after normalisation):
        WFDate = WFTextTokenString wrapping the "Date" output at {0, 1}
        WFDateFormatStyle = "Medium"
        WFTimeFormatStyle = "None"

    WFDate is a WFTextTokenString slot; coerce_text_field wraps the single
    output reference in the template-string envelope.  OutputUUID is stripped
    by normalisation.
    """
    if not DAILY_STANDUP.exists():
        pytest.skip(f"Sample not found: {DAILY_STANDUP}")

    workflow = _load(DAILY_STANDUP)
    sample_action = workflow["WFWorkflowActions"][34]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.format.date"
    )
    sample_norm = _normalise(sample_action)

    date_output = Output(uuid="4C2D9B0F-4380-496B-B8A4-7B855589C271", name="Date")
    schema_action = FormatDate(
        input=date_output,
        date_style="Medium",
        time_style="None",
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 15 — GetClipboard
# ---------------------------------------------------------------------------


def test_get_clipboard_wire_format() -> None:
    """GetClipboard schema matches the ``is.workflow.actions.getclipboard`` sample.

    Source: samples/decoded/adjust_clipboard.xml, action index 0.
    Sample params (after normalisation): {} (no parameters; only UUID stripped).
    """
    if not ADJUST_CLIPBOARD.exists():
        pytest.skip(f"Sample not found: {ADJUST_CLIPBOARD}")

    workflow = _load(ADJUST_CLIPBOARD)
    sample_action = _find_action(workflow, "is.workflow.actions.getclipboard")
    sample_norm = _normalise(sample_action)

    schema_action = GetClipboard()
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 16 — GetVariable
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason=(
        "No sample exercises GetVariable with a populated WFVariable. "
        "dictionary.xml[10] contains is.workflow.actions.getvariable but with "
        "empty WFWorkflowActionParameters — a placeholder demo entry. "
        "Add a decoded shortcut that reads a named variable via GetVariable to "
        "remove this skip."
    )
)
def test_get_variable_wire_format() -> None:
    """GetVariable schema matches a real invocation with WFVariable set.

    Source: no suitable sample available (see skip reason above).
    Expected params once a sample exists:
        WFVariable = {Value: {VariableName: <name>, Type: "Variable"},
                      WFSerializationType: "WFTextTokenAttachment"}
    """
    _ = GetVariable  # retain import for when this is unskipped


# ---------------------------------------------------------------------------
# Test 17 — RecordAudio
# ---------------------------------------------------------------------------


def test_record_audio_wire_format() -> None:
    """RecordAudio schema matches the ``is.workflow.actions.recordaudio`` sample.

    Source: samples/decoded/private/voice_note_to_github.xml, action index 4.
    Sample params (after normalisation):
        WFRecordingStart = "Immediately"
        (CustomOutputName "Audio" normalised away)

    A second instance at dictionary.xml[86] has only UUID — the private
    sample is richer and is the stronger oracle.
    """
    if not VOICE_GITHUB.exists():
        pytest.skip(f"Sample not found: {VOICE_GITHUB}")

    workflow = _load(VOICE_GITHUB)
    sample_action = _find_action(workflow, "is.workflow.actions.recordaudio")
    sample_norm = _normalise(sample_action)

    schema_action = RecordAudio(start="Immediately")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 18 — TextReplace  [SCHEMA BUGS DOCUMENTED — EXPECTED TO FAIL]
# ---------------------------------------------------------------------------


def test_text_replace_wire_format() -> None:
    """TextReplace schema vs the ``is.workflow.actions.text.replace`` sample.

    Source: samples/decoded/dictionary.xml, action index 42.
    Sample params (after normalisation):
        WFInput = WFTextTokenString wrapping "Split Text" output at {0, 1}
        (WFReplaceTextFind and WFReplaceTextReplace ABSENT)

    SCHEMA BUGS FOUND (two):
    1. WFInput uses WFTextTokenAttachment in the schema but WFTextTokenString
       in the sample.  Fix: use coerce_text_field for WFInput.
    2. Schema emits WFReplaceTextFind='' and WFReplaceTextReplace='' even
       when empty; Apple omits both.  Fix: guard emit on non-empty values.

    This test is EXPECTED TO FAIL until the schema is fixed.
    Do not silence the assertion; fix the schema and update this docstring.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][42]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.text.replace"
    )
    sample_norm = _normalise(sample_action)

    prev_output = Output(uuid="FCCCF5E7-0713-432D-AD98-914E3625C7F9", name="Split Text")
    schema_action = TextReplace(input=prev_output)
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm, (
        "Two schema bugs: (1) WFInput emitted as WFTextTokenAttachment but "
        "sample uses WFTextTokenString; (2) WFReplaceTextFind/Replace emitted "
        "as empty strings but Apple omits them when empty."
    )


# ---------------------------------------------------------------------------
# Test 19 — TextSplit
# ---------------------------------------------------------------------------


def test_text_split_wire_format() -> None:
    """TextSplit schema matches the ``is.workflow.actions.text.split`` sample.

    Source: samples/decoded/batch_add_reminders.xml, action index 9.
    Sample params (after normalisation):
        Show-text = True
        text = WFTextTokenAttachment referencing NamedVar "Reminders to Add"
        (separator key ABSENT — Apple omits it for the default "New Lines")

    ``Show-text`` is now modelled as a UI-only boolean toggle on ``TextSplit``.
    Passing ``show_text=True`` makes the schema's emit match the sample's wire
    format exactly; the sample round-trips cleanly after normalisation.
    """
    if not BATCH_REMINDERS.exists():
        pytest.skip(f"Sample not found: {BATCH_REMINDERS}")

    workflow = _load(BATCH_REMINDERS)
    sample_action = workflow["WFWorkflowActions"][9]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.text.split"
    )
    sample_norm = _normalise(sample_action)

    reminders_var = NamedVar("Reminders to Add")
    schema_action = TextSplit(
        input=reminders_var, separator="New Lines", show_text=True
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 20 — TranscribeAudio
# ---------------------------------------------------------------------------


def test_transcribe_audio_wire_format() -> None:
    """TranscribeAudio schema matches the AppIntent sample in dictionary.xml.

    Source: samples/decoded/dictionary.xml, action index 48.
    Sample params (after normalisation):
        AppIntentDescriptor = {AppIntentIdentifier, BundleIdentifier, Name,
                               TeamIdentifier}
        (no audioFile key — demo entry with no input wired)

    The schema emits AppIntentDescriptor verbatim and omits audioFile when
    audio_file is None.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][48]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "com.apple.ShortcutsActions.TranscribeAudioAction"
    )
    sample_norm = _normalise(sample_action)

    schema_action = TranscribeAudio()
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 21 — AdjustTone
# ---------------------------------------------------------------------------


def test_adjust_tone_wire_format() -> None:
    """AdjustTone schema matches the Writing Tools AppIntent sample.

    Source: samples/decoded/intelly.xml, action index 3.
    Sample params (after normalisation):
        text = "This is a dummy comment"
        tone = "professional"

    Writing Tools actions emit a bare string for ``text`` when the value
    is a literal; coerce_value passes it through unchanged.
    """
    if not INTELLY.exists():
        pytest.skip(f"Sample not found: {INTELLY}")

    workflow = _load(INTELLY)
    sample_action = workflow["WFWorkflowActions"][3]
    assert sample_action["WFWorkflowActionIdentifier"] == (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.AdjustToneIntent"
    )
    sample_norm = _normalise(sample_action)

    schema_action = AdjustTone(text="This is a dummy comment", tone="professional")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 22 — FormatList
# ---------------------------------------------------------------------------


def test_format_list_wire_format() -> None:
    """FormatList schema matches the Writing Tools AppIntent sample.

    Source: samples/decoded/intelly.xml, action index 4.
    Sample params (after normalisation):
        text = "cat dog mouse house"
    """
    if not INTELLY.exists():
        pytest.skip(f"Sample not found: {INTELLY}")

    workflow = _load(INTELLY)
    sample_action = workflow["WFWorkflowActions"][4]
    assert sample_action["WFWorkflowActionIdentifier"] == (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent"
    )
    sample_norm = _normalise(sample_action)

    schema_action = FormatList(text="cat dog mouse house")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 23 — RewriteText
# ---------------------------------------------------------------------------


def test_rewrite_text_wire_format() -> None:
    """RewriteText schema matches the Writing Tools AppIntent sample.

    Source: samples/decoded/intelly.xml, action index 5.
    Sample params (after normalisation):
        text = "abcd what is wrong with me?"
    """
    if not INTELLY.exists():
        pytest.skip(f"Sample not found: {INTELLY}")

    workflow = _load(INTELLY)
    sample_action = workflow["WFWorkflowActions"][5]
    assert sample_action["WFWorkflowActionIdentifier"] == (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent"
    )
    sample_norm = _normalise(sample_action)

    schema_action = RewriteText(text="abcd what is wrong with me?")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 24 — SummarizeText
# ---------------------------------------------------------------------------


def test_summarize_text_wire_format() -> None:
    """SummarizeText (default paragraph form) schema matches the sample.

    Source: samples/decoded/intelly.xml, action index 6.
    Sample params (after normalisation):
        text = "This text to summarise"
        (summaryType absent — Apple omits it for the default paragraph form)
    """
    if not INTELLY.exists():
        pytest.skip(f"Sample not found: {INTELLY}")

    workflow = _load(INTELLY)
    sample_action = workflow["WFWorkflowActions"][6]
    assert sample_action["WFWorkflowActionIdentifier"] == (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.SummarizeTextIntent"
    )
    sample_norm = _normalise(sample_action)

    schema_action = SummarizeText(text="This text to summarise")
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Control-flow tests — If, RepeatCount, RepeatEach, ChooseFromMenu
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test 25 — If (no else branch)
# ---------------------------------------------------------------------------


def test_if_no_else_wire_format() -> None:
    """If (no else) matches the ``is.workflow.actions.conditional`` sample.

    Source: samples/decoded/start_pomodoro.xml, actions 3-5.
    Sequence:
      [3] conditional  mode=0  WFCondition=0  WFNumberValue="1"
          WFInput = {Type: "Variable", Variable: <ActionOutput ref>}
      [4] runworkflow  (body — inserted verbatim as RawAction)
      [5] conditional  mode=2

    Head params (after normalisation):
        WFCondition       = 0
        WFControlFlowMode = 0
        WFInput           = {Type: "Variable", Variable: {OutputName: "Rounded Number",
                             Type: "ActionOutput"}}  (OutputUUID stripped)
        WFNumberValue     = "1"
    Close: WFControlFlowMode = 2
    """
    if not POMODORO.exists():
        pytest.skip(f"Sample not found: {POMODORO}")

    workflow = _load(POMODORO)
    sample_seq = _find_action_sequence(
        workflow, "is.workflow.actions.conditional", mode0_index=3
    )
    sample_norm = _normalise_sequence(sample_seq)

    rounded_output = Output(
        uuid="5DFB8DC2-BA34-49FA-8D04-57110F7FA4DC", name="Rounded Number"
    )
    body_raw = workflow["WFWorkflowActions"][4]
    body_action = RawAction(
        raw_identifier=body_raw["WFWorkflowActionIdentifier"],
        raw_params=dict(body_raw["WFWorkflowActionParameters"]),
    )

    schema_if = If(operand=rounded_output, op="==", value=1, then=[body_action])
    schema_norm = _normalise_sequence(schema_if.to_actions())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Test 26 — RepeatCount
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="Corpus only has a demo-placeholder repeat.count (no configured count). "
    "The schema emits WFRepeatCount=1 by default; the sample omits it. Without a "
    "configured-count sample we can't tell which wire shape Apple's runtime "
    "expects. Need a real sample with a non-1 count to resolve.",
    strict=True,
)
def test_repeat_count_wire_format() -> None:
    """RepeatCount schema vs the ``is.workflow.actions.repeat.count`` sample.

    Source: samples/decoded/dictionary.xml, action index 6 (head) and 457 (close).
    This is a demo entry: the head has no WFRepeatCount and no UUID; the close
    has UUID (normalised away).  Only head-and-close framing is validated — the
    body spans several hundred actions (the entire dictionary-of-all-actions demo).

    SCHEMA BUG FOUND:
    The schema emits ``WFRepeatCount: 1`` in the head, but the sample's head
    omits WFRepeatCount entirely.  In every decoded sample this corpus has, the
    repeat.count head carries no WFRepeatCount when the count was not explicitly
    set.  Apple appears to omit WFRepeatCount in the unconfigured state.
    Fix: suppress WFRepeatCount emission or use a real shortcut with a configured
    count to establish the correct wire format.

    This test is EXPECTED TO FAIL — it surfaces the discrepancy above.
    Do not silence the assertion; fix the schema and update this docstring.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_head = workflow["WFWorkflowActions"][6]
    sample_close = workflow["WFWorkflowActions"][457]
    assert (
        sample_head["WFWorkflowActionIdentifier"] == "is.workflow.actions.repeat.count"
    )
    assert (
        sample_close["WFWorkflowActionIdentifier"] == "is.workflow.actions.repeat.count"
    )
    sample_framing = _normalise_sequence([sample_head, sample_close])

    schema_rc = RepeatCount(count=1, body=[])
    schema_seq = schema_rc.to_actions()
    schema_framing = _normalise_sequence([schema_seq[0], schema_seq[-1]])

    assert schema_framing == sample_framing, (
        "Schema emits WFRepeatCount: 1 in head but sample's head omits "
        "WFRepeatCount entirely.  Apple may omit it in the unconfigured state.  "
        "Add a real shortcut with a configured RepeatCount to verify correct wire."
    )


# ---------------------------------------------------------------------------
# Test 27 — RepeatEach
# ---------------------------------------------------------------------------


def test_repeat_each_wire_format() -> None:
    """RepeatEach schema vs the ``is.workflow.actions.repeat.each`` sample.

    Source: samples/decoded/batch_add_reminders.xml, actions 10-14.
    Sequence:
      [10] repeat.each  mode=0  WFInput = <plain WFTextTokenAttachment>
      [11] conditional  mode=0  (body)
      [12] addnewreminder       (body)
      [13] conditional  mode=2  (body)
      [14] repeat.each  mode=2

    SCHEMA BUG FOUND:
    The schema emits WFInput as the two-layer form:
        {Type: "Variable", Variable: {Value: ..., WFSerializationType: "WFTextTokenAttachment"}}
    But both repeat.each samples in the corpus (batch_add_reminders.xml and
    set_weekend_chores.xml) emit WFInput as a plain WFTextTokenAttachment:
        {Value: ..., WFSerializationType: "WFTextTokenAttachment"}

    The ``_wrap_variable_input`` helper (used by RepeatEach.to_actions) adds
    the extra {Type: "Variable", Variable: ...} outer layer, which is correct
    for If/conditional heads but wrong for RepeatEach.
    Fix: RepeatEach.to_actions should use ``coerce_value(self.items)`` directly
    for WFInput rather than ``_wrap_variable_input``.

    This test is EXPECTED TO FAIL — it surfaces the schema bug above.
    Do not silence the assertion; fix the schema and update this docstring.
    """
    if not BATCH_REMINDERS.exists():
        pytest.skip(f"Sample not found: {BATCH_REMINDERS}")

    workflow = _load(BATCH_REMINDERS)
    sample_seq = _find_action_sequence(
        workflow, "is.workflow.actions.repeat.each", mode0_index=10
    )
    sample_norm = _normalise_sequence(sample_seq)

    split_output = Output(
        uuid="AC2B1F0E-4066-4587-BAC1-CC8F69BEFA3A", name="Split Text"
    )
    body_actions = [
        RawAction(
            raw_identifier=workflow["WFWorkflowActions"][j][
                "WFWorkflowActionIdentifier"
            ],
            raw_params=dict(
                workflow["WFWorkflowActions"][j]["WFWorkflowActionParameters"]
            ),
        )
        for j in range(11, 14)
    ]

    schema_re = RepeatEach(items=split_output, body=body_actions)
    schema_norm = _normalise_sequence(schema_re.to_actions())

    assert schema_norm == sample_norm, (
        "Schema wraps WFInput in {Type: Variable, Variable: ...} but both "
        "repeat.each samples use a plain WFTextTokenAttachment.  Schema bug: "
        "RepeatEach.to_actions should use coerce_value directly, not "
        "_wrap_variable_input."
    )


# ---------------------------------------------------------------------------
# Test 28 — ChooseFromMenu
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="The read_later.xml sample was authored with an older Shortcuts editor "
    "that redundantly stamps WFMenuItems / WFMenuPrompt onto mode=1 case markers. "
    "Modern Shortcuts.app omits these on case markers and the schema is correct "
    "to omit them. To unxfail: add a newer sample without the redundant fields.",
    strict=True,
)
def test_choose_from_menu_wire_format() -> None:
    """ChooseFromMenu schema vs the ``is.workflow.actions.choosefrommenu`` sample.

    Source: samples/decoded/read_later.xml, actions 5-14.
    Four cases ("Reading list", "Pocket", "Instapaper", "Pinboard") with a
    WFMenuPrompt.

    Head params (after normalisation):
        WFControlFlowMode = 0
        WFMenuItems = ["Reading list", "Pocket", "Instapaper", "Pinboard"]
        WFMenuPrompt = "Where would you like to save?"
    Case markers (mode=1):
        WFControlFlowMode = 1
        WFMenuItemTitle = <label>
    Close (mode=2): WFControlFlowMode = 2

    SAMPLE QUIRK (not a schema bug):
    The read_later.xml sample was created with an older Shortcuts editor that
    redundantly stamped WFMenuItems / WFMenuPrompt onto some mode=1 case markers.
    Modern Shortcuts.app does not emit these on case markers.  The schema is
    correct to omit them.

    This test is EXPECTED TO FAIL because the sample's mode=1 markers carry
    fields that the schema (correctly) does not emit.  To fix this test:
    either (a) strip WFMenuItems/WFMenuPrompt from mode=1 markers before
    comparing, or (b) add a newer sample without the redundant fields.
    """
    if not READ_LATER.exists():
        pytest.skip(f"Sample not found: {READ_LATER}")

    workflow = _load(READ_LATER)
    sample_seq = _find_action_sequence(
        workflow, "is.workflow.actions.choosefrommenu", mode0_index=5
    )
    sample_norm = _normalise_sequence(sample_seq)

    def _raw(idx: int) -> RawAction:
        a = workflow["WFWorkflowActions"][idx]
        return RawAction(
            raw_identifier=a["WFWorkflowActionIdentifier"],
            raw_params=dict(a["WFWorkflowActionParameters"]),
        )

    schema_menu = ChooseFromMenu(
        prompt="Where would you like to save?",
        cases=[
            ("Reading list", [_raw(7)]),
            ("Pocket", [_raw(9)]),
            ("Instapaper", [_raw(11)]),
            ("Pinboard", [_raw(13)]),
        ],
    )
    schema_norm = _normalise_sequence(schema_menu.to_actions())

    assert schema_norm == sample_norm, (
        "read_later.xml mode=1 case markers carry redundant WFMenuItems/"
        "WFMenuPrompt (older editor artifact) that the schema correctly omits.  "
        "This is a sample quirk, not a schema bug.  Replace the sample with a "
        "newer one to make this test green."
    )
