"""Tests for DownloadURL schema action.

Wire-format expectations are derived from two decoded samples:
- ``samples/decoded/get_contents_of_url.xml`` (4 invocations, GET + PUT + PATCH + POST)
- ``samples/decoded/private/voice_note_to_github.xml`` (2 PUT invocations with
  Authorization header, JSON body using WFJSONValues, and WFRequestVariable)
"""

from __future__ import annotations

from typing import Any

import pytest

import shortcut_lib.schema.actions.download_url  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Text

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _params(action: DownloadURL) -> dict:
    """Extract WFWorkflowActionParameters from an action."""
    return action.to_action_dict()["WFWorkflowActionParameters"]


# ---------------------------------------------------------------------------
# Test 1 — GET with no body
# ---------------------------------------------------------------------------


def test_get_with_no_body() -> None:
    """GET request emits WFURL as a plain string and omits WFHTTPMethod."""
    action = DownloadURL(url="https://example.com")
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.downloadurl"
    params = d["WFWorkflowActionParameters"]

    # URL lands as a plain string when passed as a plain string.
    assert params["WFURL"] == "https://example.com"

    # GET is the default — Apple omits the key entirely.
    assert "WFHTTPMethod" not in params

    # No body → no body keys.
    assert "WFHTTPBodyType" not in params
    assert "WFJSONValues" not in params
    assert "WFRequestVariable" not in params

    # No headers → ShowHeaders and WFHTTPHeaders absent.
    assert "ShowHeaders" not in params
    assert "WFHTTPHeaders" not in params

    # UUID is always present.
    assert "UUID" in params


# ---------------------------------------------------------------------------
# Test 2 — POST with JSON body
# ---------------------------------------------------------------------------


def test_post_with_json_body() -> None:
    """POST + JSON body emits WFHTTPMethod, WFHTTPBodyType, and WFJSONValues."""
    action = DownloadURL(
        url="https://api.example.com/items",
        method="POST",
        body={"name": "Alice", "score": "100"},
        body_type="JSON",
    )
    params = _params(action)

    assert params["WFHTTPMethod"] == "POST"
    assert params["WFHTTPBodyType"] == "JSON"

    # WFJSONValues must be a WFDictionaryFieldValue envelope.
    json_values = params["WFJSONValues"]
    assert json_values["WFSerializationType"] == "WFDictionaryFieldValue"
    items = json_values["Value"]["WFDictionaryFieldValueItems"]
    assert len(items) == 2

    # Each item must have WFItemType=0, WFKey, and WFValue.
    for item in items:
        assert item["WFItemType"] == 0
        assert "WFKey" in item
        assert "WFValue" in item
        # Key wrapper is a WFTextTokenString envelope.
        assert item["WFKey"]["WFSerializationType"] == "WFTextTokenString"
        assert item["WFValue"]["WFSerializationType"] == "WFTextTokenString"

    # Verify the actual key names survive round-trip.
    keys_in_wire = {item["WFKey"]["Value"]["string"] for item in items}
    assert keys_in_wire == {"name", "score"}

    # Plain-string values become {"string": "..."} inside WFTextTokenString.
    value_by_key = {
        item["WFKey"]["Value"]["string"]: item["WFValue"]["Value"]["string"]
        for item in items
    }
    assert value_by_key["name"] == "Alice"
    assert value_by_key["score"] == "100"

    # No WFRequestVariable when body_type is JSON.
    assert "WFRequestVariable" not in params


# ---------------------------------------------------------------------------
# Test 3 — POST with headers
# ---------------------------------------------------------------------------


def test_post_with_headers() -> None:
    """Headers appear in WFHTTPHeaders with WFDictionaryFieldValue shape.

    Matches the Authorization + Accept + X-GitHub-Api-Version pattern observed
    in voice_note_to_github.xml. Also verifies ShowHeaders=True is emitted.
    """
    action = DownloadURL(
        url="https://api.github.com/repos/owner/repo/contents/file.md",
        method="PUT",
        headers={
            "Authorization": "Bearer token123",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        body={"message": "add file", "content": "SGVsbG8="},
        body_type="JSON",
    )
    params = _params(action)

    # ShowHeaders is present and True when headers are configured.
    assert params["ShowHeaders"] is True

    headers = params["WFHTTPHeaders"]
    assert headers["WFSerializationType"] == "WFDictionaryFieldValue"
    items = headers["Value"]["WFDictionaryFieldValueItems"]
    assert len(items) == 3

    # All items must be string type.
    for item in items:
        assert item["WFItemType"] == 0
        assert item["WFKey"]["WFSerializationType"] == "WFTextTokenString"
        assert item["WFValue"]["WFSerializationType"] == "WFTextTokenString"

    header_map = {
        item["WFKey"]["Value"]["string"]: item["WFValue"]["Value"]["string"]
        for item in items
    }
    assert header_map["Authorization"] == "Bearer token123"
    assert header_map["Accept"] == "application/vnd.github+json"
    assert header_map["X-GitHub-Api-Version"] == "2022-11-28"


# ---------------------------------------------------------------------------
# Test 4 — URL with variable (Action output chaining)
# ---------------------------------------------------------------------------


def test_url_with_variable() -> None:
    """An Action output as url is wrapped as a single-attachment WFTextTokenString.

    Apple's runtime reads ``WFURL`` as a WFTextTokenString and shows
    "No URL Specified" if it gets a bare WFTextTokenAttachment envelope.
    The schema promotes a lone Action/Value reference into a templated-
    string envelope with one attachment so the URL slot connects cleanly.
    """
    url_text = GetText(text="https://api.github.com/repos/owner/repo/contents/f.md")
    action = DownloadURL(url=url_text, method="GET")
    params = _params(action)

    url_param = params["WFURL"]
    assert isinstance(url_param, dict)
    assert url_param["WFSerializationType"] == "WFTextTokenString"
    assert url_param["Value"]["string"] == "￼"
    attachments = url_param["Value"]["attachmentsByRange"]
    assert list(attachments) == ["{0, 1}"]
    assert attachments["{0, 1}"]["OutputUUID"] == url_text.uuid
    assert attachments["{0, 1}"]["Type"] == "ActionOutput"


# ---------------------------------------------------------------------------
# Test 5 — Header value as a NamedVar (token in header value)
# ---------------------------------------------------------------------------


def test_header_value_as_named_var() -> None:
    """A NamedVar header value is promoted to a single-attachment WFTextTokenString.

    Apple's wire format puts dictionary slot values (header values, JSON body
    values) inside a WFTextTokenString envelope — even when the value is "just
    a variable reference". A bare WFTextTokenAttachment in this slot imports
    as a disconnected field (cf. the same bug pattern on ``WFURL``). The
    schema rewraps the NamedVar's WFTextTokenAttachment as a one-attachment
    WFTextTokenString so it matches Apple's emission.
    """
    token_var = NamedVar("Token")
    action = DownloadURL(
        url="https://api.example.com/resource",
        method="GET",
        headers={"Authorization": token_var},
    )
    params = _params(action)

    items = params["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"]
    assert len(items) == 1
    wf_value = items[0]["WFValue"]

    assert wf_value["WFSerializationType"] == "WFTextTokenString"
    assert wf_value["Value"]["string"] == "￼"
    attachments = wf_value["Value"]["attachmentsByRange"]
    assert list(attachments) == ["{0, 1}"]
    assert attachments["{0, 1}"]["Type"] == "Variable"
    assert attachments["{0, 1}"]["VariableName"] == "Token"


# ---------------------------------------------------------------------------
# Test 6 — Text template as header value (Bearer {token} pattern)
# ---------------------------------------------------------------------------


def test_header_value_as_text_template() -> None:
    """A Text template in a header value produces the WFTextTokenString envelope.

    This is the exact pattern used by voice_note_to_github.xml:
    ``Authorization: Bearer {Token}`` where Token is a NamedVar.
    """
    token_var = NamedVar("Token")
    bearer = Text("Bearer {tok}", substitutions={"tok": token_var})
    action = DownloadURL(
        url="https://api.example.com/resource",
        method="GET",
        headers={"Authorization": bearer},
    )
    params = _params(action)

    items = params["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"]
    wf_value = items[0]["WFValue"]

    # Text.to_param() → WFTextTokenString, which is already an envelope dict.
    # _make_wf_text_token_string passes it through unchanged.
    assert wf_value["WFSerializationType"] == "WFTextTokenString"
    inner = wf_value["Value"]
    assert "Bearer " in inner["string"]
    assert "￼" in inner["string"]  # object replacement character placeholder
    assert len(inner["attachmentsByRange"]) == 1


# ---------------------------------------------------------------------------
# Test 7 — WFRequestVariable for raw/file body
# ---------------------------------------------------------------------------


def test_plain_text_body_uses_request_variable() -> None:
    """Plain Text body_type emits WFRequestVariable, not WFJSONValues."""
    body_action = GetText(text="raw body content")
    action = DownloadURL(
        url="https://example.com/upload",
        method="POST",
        body=body_action,
        body_type="Plain Text",
    )
    params = _params(action)

    assert params["WFHTTPBodyType"] == "Plain Text"
    assert "WFRequestVariable" in params
    assert "WFJSONValues" not in params

    req_var = params["WFRequestVariable"]
    assert req_var["WFSerializationType"] == "WFTextTokenAttachment"
    assert req_var["Value"]["OutputUUID"] == body_action.uuid


# ---------------------------------------------------------------------------
# Test 8 — Error: missing url
# ---------------------------------------------------------------------------


def test_missing_url_raises() -> None:
    """Omitting url raises SchemaError with a helpful message."""
    action = DownloadURL()
    with pytest.raises(SchemaError, match="url"):
        action.to_action_dict()


# ---------------------------------------------------------------------------
# Test 9 — Error: body without body_type
# ---------------------------------------------------------------------------


def test_body_without_body_type_raises() -> None:
    """Providing body without body_type raises SchemaError."""
    action = DownloadURL(url="https://example.com", body={"key": "val"})
    with pytest.raises(SchemaError, match="body_type"):
        action.to_action_dict()


# ---------------------------------------------------------------------------
# Test 10 — Error: dict body with non-dict body_type=JSON
# ---------------------------------------------------------------------------


def test_non_dict_body_with_json_type_raises() -> None:
    """Passing a string body with body_type='JSON' raises SchemaError."""
    action = DownloadURL(url="https://example.com", body="raw string", body_type="JSON")
    with pytest.raises(SchemaError, match="dict"):
        action.to_action_dict()


# ---------------------------------------------------------------------------
# Test 11 — Registration
# ---------------------------------------------------------------------------


def test_download_url_registered() -> None:
    """DownloadURL is discoverable via the action registry."""
    cls = lookup("is.workflow.actions.downloadurl")
    assert cls is DownloadURL


# ---------------------------------------------------------------------------
# Test 12 — Default output name
# ---------------------------------------------------------------------------


def test_default_output_name() -> None:
    """default_output_name is 'Contents of URL' — Apple's UI label."""
    assert DownloadURL.default_output_name == "Contents of URL"


# ---------------------------------------------------------------------------
# Test 13 — PUT matches voice_note_to_github.xml shape
# ---------------------------------------------------------------------------


def test_put_matches_github_sample() -> None:
    """Validate full shape against voice_note_to_github.xml first downloadurl.

    That action has: PUT, ShowHeaders=True, WFHTTPHeaders (3 entries),
    WFHTTPBodyType=JSON, WFJSONValues (2 entries: message + content),
    WFRequestVariable (a NamedVar pointing to MdBody).
    """
    token = NamedVar("Token")
    base = NamedVar("Base")
    md_b64 = NamedVar("MdB64")

    action = DownloadURL(
        url="https://api.github.com/repos/owner/repo/contents/jots/voice/note.md",
        method="PUT",
        headers={
            "Authorization": Text("Bearer {tok}", substitutions={"tok": token}),
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        body={
            "message": Text("voice: {base}", substitutions={"base": base}),
            "content": md_b64,
        },
        body_type="JSON",
    )
    params = _params(action)

    # Method.
    assert params["WFHTTPMethod"] == "PUT"

    # ShowHeaders present.
    assert params["ShowHeaders"] is True

    # Headers: 3 items.
    header_items = params["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"]
    assert len(header_items) == 3

    # Body type.
    assert params["WFHTTPBodyType"] == "JSON"

    # JSON body: 2 items.
    body_items = params["WFJSONValues"]["Value"]["WFDictionaryFieldValueItems"]
    assert len(body_items) == 2
    body_keys = {item["WFKey"]["Value"]["string"] for item in body_items}
    assert body_keys == {"message", "content"}

    # WFRequestVariable is also present in the sample alongside WFJSONValues.
    # (Apple stores both — WFJSONValues is the active body; WFRequestVariable
    # appears to be a stale/parallel field that Shortcuts writes when the user
    # previously had a variable body and switched to JSON mode. We emit it here
    # only when the caller explicitly sets body_type to a non-dict type.)
    # This test does NOT assert WFRequestVariable since our API doesn't mix them.


# ---------------------------------------------------------------------------
# Test 14 — body_type='Form' raises until verified
# ---------------------------------------------------------------------------


def test_form_body_type_raises() -> None:
    """body_type='Form' raises SchemaError with the exact unverified message."""
    action = DownloadURL(
        url="https://example.com/upload",
        method="POST",
        body={"field": "value"},
        body_type="Form",
    )
    with pytest.raises(
        SchemaError,
        match="body_type='Form' is not yet verified against samples",
    ):
        action.to_action_dict()


# ---------------------------------------------------------------------------
# Tests 15-21 - Factory methods
# ---------------------------------------------------------------------------


def test_get_factory() -> None:
    """DownloadURL.get() produces no WFHTTPMethod, no WFHTTPBodyType, no body keys."""
    action = DownloadURL.get("https://x")
    params = _params(action)

    assert "WFHTTPMethod" not in params
    assert "WFHTTPBodyType" not in params
    assert "WFJSONValues" not in params
    assert "WFRequestVariable" not in params
    assert params["WFURL"] == "https://x"


def test_json_factory_post() -> None:
    """DownloadURL.json() defaults to POST and emits WFHTTPBodyType=JSON."""
    action = DownloadURL.json("url", {"k": "v"})
    params = _params(action)

    assert params["WFHTTPMethod"] == "POST"
    assert params["WFHTTPBodyType"] == "JSON"
    items = params["WFJSONValues"]["Value"]["WFDictionaryFieldValueItems"]
    assert len(items) == 1
    assert items[0]["WFKey"]["Value"]["string"] == "k"
    assert items[0]["WFValue"]["Value"]["string"] == "v"
    assert "WFRequestVariable" not in params


def test_json_factory_put() -> None:
    """DownloadURL.json(..., method='PUT') emits WFHTTPMethod=PUT."""
    action = DownloadURL.json("url", {"k": "v"}, method="PUT")
    params = _params(action)

    assert params["WFHTTPMethod"] == "PUT"
    assert params["WFHTTPBodyType"] == "JSON"


def test_plain_text_factory() -> None:
    """DownloadURL.plain_text() emits WFHTTPBodyType='Plain Text' and WFRequestVariable."""
    body_var = NamedVar("Body")
    action = DownloadURL.plain_text("url", body_var, method="POST")
    params = _params(action)

    assert params["WFHTTPMethod"] == "POST"
    assert params["WFHTTPBodyType"] == "Plain Text"
    assert "WFRequestVariable" in params
    assert "WFJSONValues" not in params

    req_var = params["WFRequestVariable"]
    assert req_var["WFSerializationType"] == "WFTextTokenAttachment"
    assert req_var["Value"]["VariableName"] == "Body"


def test_file_factory() -> None:
    """DownloadURL.file() emits WFHTTPBodyType='File' and WFRequestVariable."""
    audio_var = NamedVar("Audio")
    action = DownloadURL.file("url", audio_var, method="PUT")
    params = _params(action)

    assert params["WFHTTPMethod"] == "PUT"
    assert params["WFHTTPBodyType"] == "File"
    assert "WFRequestVariable" in params
    assert "WFJSONValues" not in params

    req_var = params["WFRequestVariable"]
    assert req_var["WFSerializationType"] == "WFTextTokenAttachment"
    assert req_var["Value"]["VariableName"] == "Audio"


def test_get_factory_no_body_kwarg() -> None:
    """DownloadURL.get() does not accept a body keyword argument.

    We spread a ``dict[str, Any]`` so ty sees a valid ``**kwargs`` expansion
    (the spread type matches ``headers: dict[str, Any] | None``) while the
    runtime rejects the unknown key ``"body"`` with a ``TypeError``.  ty
    already confirms this statically; this test asserts the runtime behaviour.
    """
    bad_kwargs: dict[str, Any] = {"body": NamedVar("X")}
    with pytest.raises(TypeError):
        DownloadURL.get("url", **bad_kwargs)


def test_factory_round_trip_equals_direct() -> None:
    """Factory and direct constructor produce identical to_action_dict() output.

    UUIDs differ per instance, so we compare params minus UUID.
    """
    url = "https://api.example.com/items"
    body = {"k": "v"}
    headers = {"H": "v"}

    via_factory = DownloadURL.json(url, body, headers=headers)
    via_direct = DownloadURL(
        url=url,
        method="POST",
        body=body,
        body_type="JSON",
        headers=headers,
    )

    factory_params = _params(via_factory)
    direct_params = _params(via_direct)

    # Strip UUID before comparison (each instance gets a fresh one).
    factory_params.pop("UUID", None)
    direct_params.pop("UUID", None)

    assert factory_params == direct_params
