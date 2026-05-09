"""Tests for SendEmail action schema.

Corpus evidence (3 appearances):
- samples/decoded/email_last_image.xml:1  — body + subject + ShowComposeSheet
- samples/decoded/dictionary.xml:174      — body only (demo placeholder)
- samples/decoded/dictionary.xml:313      — body only (demo placeholder)

Parameters observed in corpus:
- WFSendEmailActionInputAttachments (WFTextTokenString) — body/attachments
- WFSendEmailActionSubject          (WFTextTokenString) — subject line
- WFSendEmailActionShowComposeSheet (bool)              — compose-sheet toggle

Parameters NOT observed (punted):
- Recipient encoding: no sample carried a recipients field. The ``to``
  parameter is exposed as a raw pass-through dict slot with the working key
  name ``WFSendEmailActionToRecipients`` (inferred; not sample-verified).
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

import shortcut_lib.schema.actions.send_email  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.send_email import SendEmail
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output, Text

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
EMAIL_LAST_IMAGE = DECODED / "email_last_image.xml"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers (mirror test_wire_format_equivalence.py conventions)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID from all dicts."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip UUID and OutputUUID for deterministic comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_send_email_basic() -> None:
    """Plain string subject and a Text body land in the correct WF keys."""
    action = SendEmail(subject="Hello", body="World")
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFSendEmailActionSubject"] == "Hello"
    assert params["WFSendEmailActionInputAttachments"] == "World"
    assert "WFSendEmailActionShowComposeSheet" not in params
    assert "WFSendEmailActionToRecipients" not in params


def test_send_email_identifier() -> None:
    """Action identifier matches the Apple wire-format identifier."""
    action = SendEmail()
    assert action.to_action_dict()["WFWorkflowActionIdentifier"] == (
        "is.workflow.actions.sendemail"
    )


def test_send_email_omits_none_fields() -> None:
    """Fields left as None produce no keys in the emitted params dict."""
    action = SendEmail()
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "WFSendEmailActionInputAttachments" not in params
    assert "WFSendEmailActionSubject" not in params
    assert "WFSendEmailActionShowComposeSheet" not in params
    assert "WFSendEmailActionToRecipients" not in params


def test_send_email_show_compose_sheet_true() -> None:
    """show_compose_sheet=True emits the boolean key."""
    action = SendEmail(show_compose_sheet=True)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSendEmailActionShowComposeSheet"] is True


def test_send_email_show_compose_sheet_false() -> None:
    """show_compose_sheet=False emits the boolean key as False."""
    action = SendEmail(show_compose_sheet=False)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSendEmailActionShowComposeSheet"] is False


def test_send_email_body_output_ref_wraps_as_text_token_string() -> None:
    """An Output reference in ``body`` is wrapped as WFTextTokenString.

    Apple's wire format for WFSendEmailActionInputAttachments is always
    WFTextTokenString (not WFTextTokenAttachment), even when the value is
    a single variable reference.  coerce_text_field handles the rewrap.
    Source: all three corpus appearances use WFTextTokenString.
    """
    prev = Output(uuid="AAAAAAAA-0000-0000-0000-000000000001", name="My Photos")
    action = SendEmail(body=prev)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    env = params["WFSendEmailActionInputAttachments"]

    assert env["WFSerializationType"] == "WFTextTokenString"
    inner = env["Value"]
    assert "string" in inner
    assert "attachmentsByRange" in inner
    assert "￼" in inner["string"]  # U+FFFC object replacement char
    token = next(iter(inner["attachmentsByRange"].values()))
    assert token["OutputName"] == "My Photos"
    assert token["Type"] == "ActionOutput"


def test_send_email_subject_output_ref_wraps_as_text_token_string() -> None:
    """An Output reference in ``subject`` is wrapped as WFTextTokenString.

    The single corpus appearance of WFSendEmailActionSubject
    (email_last_image.xml:1) uses WFTextTokenString.
    """
    prev = Output(uuid="BBBBBBBB-0000-0000-0000-000000000002", name="Photo Name")
    action = SendEmail(subject=prev)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    env = params["WFSendEmailActionSubject"]

    assert env["WFSerializationType"] == "WFTextTokenString"


def test_send_email_to_passthrough() -> None:
    """A pre-built dict in ``to`` is emitted verbatim (pass-through).

    Recipient encoding was not observed in the corpus.  The slot key
    ``WFSendEmailActionToRecipients`` is inferred, not sample-verified.
    Callers who need recipients should pass a pre-built wire-format dict.
    """
    raw_recipient = {"some": "envelope"}
    action = SendEmail(to=raw_recipient)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSendEmailActionToRecipients"] == raw_recipient


def test_send_email_registered() -> None:
    """SendEmail is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.sendemail")
    assert cls is SendEmail


# ---------------------------------------------------------------------------
# Wire-format equivalence — dictionary.xml (index 174, body-only demo entry)
# ---------------------------------------------------------------------------


def test_send_email_wire_format_dictionary_body_only() -> None:
    """SendEmail schema matches the body-only demo entry in dictionary.xml.

    Source: samples/decoded/dictionary.xml, action index 174.
    Sample params (after normalisation):
        WFSendEmailActionInputAttachments = WFTextTokenString with one
            ActionOutput reference to "Details of Podcast Episodes" at {0, 1}.
        (no subject, no ShowComposeSheet)

    OutputUUID is stripped by normalisation.
    """
    if not DICTIONARY.exists():
        pytest.skip(f"Sample not found: {DICTIONARY}")

    workflow = _load(DICTIONARY)
    sample_action = workflow["WFWorkflowActions"][174]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.sendemail"
    )
    sample_norm = _normalise(sample_action)

    prev = Output(
        uuid="53951798-AAF3-40E6-A819-037878C6DD32",
        name="Details of Podcast Episodes",
    )
    schema_action = SendEmail(body=Text("{body}", substitutions={"body": prev}))
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


# ---------------------------------------------------------------------------
# Wire-format equivalence — email_last_image.xml (body + show_compose_sheet)
# ---------------------------------------------------------------------------


def test_send_email_wire_format_email_last_image_body_and_toggle() -> None:
    """SendEmail schema matches the email_last_image.xml sample (partial).

    Source: samples/decoded/email_last_image.xml, action index 1.
    Sample params (after normalisation, subject omitted from schema side):
        WFSendEmailActionInputAttachments = WFTextTokenString with one
            ActionOutput reference to "Latest Photos" at {0, 1}.
        WFSendEmailActionShowComposeSheet = True

    The subject in this sample uses a WFPropertyVariableAggrandizement
    (property accessor on the output, extracting the ``Name`` property).
    Aggrandizements are beyond V1 modelling; this test validates only the
    body and show_compose_sheet fields and skips the subject comparison.
    """
    if not EMAIL_LAST_IMAGE.exists():
        pytest.skip(f"Sample not found: {EMAIL_LAST_IMAGE}")

    workflow = _load(EMAIL_LAST_IMAGE)
    sample_action = workflow["WFWorkflowActions"][1]
    assert (
        sample_action["WFWorkflowActionIdentifier"] == "is.workflow.actions.sendemail"
    )

    # Build a normalised copy of the sample with subject stripped so we can
    # compare only the fields the schema can model in V1.
    sample_trimmed = copy.deepcopy(sample_action)
    sample_trimmed["WFWorkflowActionParameters"].pop("WFSendEmailActionSubject", None)
    sample_norm = _normalise(sample_trimmed)

    prev = Output(
        uuid="7D446437-212B-42A8-918B-7E04A1CA00AA",
        name="Latest Photos",
    )
    schema_action = SendEmail(
        body=Text("{body}", substitutions={"body": prev}),
        show_compose_sheet=True,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm
