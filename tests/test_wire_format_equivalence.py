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

from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.set_clipboard import SetClipboard
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.values import NamedVar, Output, Text

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
POMODORO = DECODED / "start_pomodoro.xml"
DICTATE = DECODED / "dictate_to_clipboard.xml"
GET_CONTENTS = DECODED / "get_contents_of_url.xml"
VOICE_GITHUB = DECODED / "private" / "voice_note_to_github.xml"

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
