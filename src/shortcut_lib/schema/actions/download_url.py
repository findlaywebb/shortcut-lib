"""DownloadURL — make an HTTP request and return the response body.

This is Apple's "Get Contents of URL" action. It supports all standard HTTP
methods and four body-encoding modes observed in real shortcuts:
- "JSON"       — WFJSONValues dict, encoded as application/json
- "Form"       — WFFormValues dict, encoded as multipart/form-data (TODO: unconfirmed key name)
- "Plain Text" — WFRequestVariable, raw text body
- "File"       — WFRequestVariable, raw binary body

The "JSON" and header shapes were verified against ``get_contents_of_url.xml``
(4 invocations) and ``voice_note_to_github.xml`` (2 complex PUT invocations).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, cast

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
    coerce_value,
)
from shortcut_lib.schema.registry import register

# Apple's default method; omitting WFHTTPMethod from the plist is equivalent to GET.
_DEFAULT_METHOD = "GET"

# Body types where the body is encoded as a WFDictionaryFieldValue dict.
_DICT_BODY_TYPES = {"JSON", "Form"}

# The WFItemType integer for a plain string key/value pair in a WF dict.
# Value 0 = string type. (Other integers exist for other types but are not
# needed for HTTP headers/bodies in the observed samples.)
_WF_ITEM_TYPE_STRING = 0


def _make_wf_text_token_string(value: Any) -> dict[str, Any]:
    """Wrap a *coerced* value as a WFTextTokenString envelope for a dict slot.

    Used inside ``WFHTTPHeaders``/``WFJSONValues`` where every slot — keys
    and values alike — must be a WFTextTokenString. The value comes in
    already coerced (via :func:`coerce_value`), so this helper handles
    plain scalars by wrapping them as ``{string: str(value)}`` and defers
    Action/Value handling to :func:`coerce_text_field`'s envelope rewrap.
    """
    if isinstance(value, dict) and "WFSerializationType" in value:
        # Already an envelope — let coerce_text_field handle the
        # WFTextTokenAttachment → WFTextTokenString rewrap path.
        return coerce_text_field(value)
    return {
        "Value": {"string": str(value)},
        "WFSerializationType": "WFTextTokenString",
    }


def _encode_wf_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Encode a Python dict as a WFDictionaryFieldValue wire structure.

    Each key/value pair becomes a WFDictionaryFieldValueItems entry with:
    - ``WFItemType``: 0  (string type — only variant used for headers/JSON body)
    - ``WFKey``: WFTextTokenString-wrapped key name
    - ``WFValue``: WFTextTokenString-wrapped value (may contain variable tokens)

    This structure is used for both ``WFHTTPHeaders`` and ``WFJSONValues``
    (and, by extension, ``WFFormValues``). The outer envelope is:

    .. code-block:: python

        {
            "Value": {"WFDictionaryFieldValueItems": [...]},
            "WFSerializationType": "WFDictionaryFieldValue",
        }

    Args:
        d: Python dict whose keys are plain strings and whose values may be
            plain strings, or any Value/Action-coerced token envelopes.

    Returns:
        The WFDictionaryFieldValue outer envelope dict.
    """
    items: list[dict[str, Any]] = []
    for k, v in d.items():
        coerced_v = coerce_value(v)
        items.append(
            {
                "WFItemType": _WF_ITEM_TYPE_STRING,
                "WFKey": _make_wf_text_token_string(k),
                "WFValue": _make_wf_text_token_string(coerced_v),
            }
        )
    return {
        "Value": {"WFDictionaryFieldValueItems": items},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


@register
@dataclass
class DownloadURL(Action):
    """Make an HTTP request and return the response body.

    Wraps ``is.workflow.actions.downloadurl`` — Apple's "Get Contents of URL".

    Prefer the request-shape factory methods — they expose only the
    parameters valid for that body type, so an invalid combination is a
    ``TypeError`` at the call site rather than a ``SchemaError`` after
    construction::

        DownloadURL.get("https://api.example.com/items")
        DownloadURL.json("https://api.example.com/items", {"name": "x"})
        DownloadURL.plain_text("https://api.example.com/upload", NamedVar("Body"))
        DownloadURL.file("https://api.example.com/upload", NamedVar("Audio"), method="PUT")

    The direct constructor ``DownloadURL(url=..., method=..., ...)`` still
    works and is preserved for backward compatibility and for cases where
    ``body_type`` is determined at runtime.

    Args:
        url: The target URL. Can be a plain string, a :class:`~shortcut_lib.schema.values.Text`
            template, or any Action whose output is a URL string.  Required.
        method: HTTP verb. Defaults to ``"GET"``. Apple omits the key for GET,
            so it only appears in the plist for non-GET requests.
        headers: Optional dict of header name → value. Values can be plain
            strings or any coercible Value/Action (e.g. a NamedVar). Emitted
            as ``WFHTTPHeaders`` in WFDictionaryFieldValue format.
        body: The request body. Interpretation depends on ``body_type``:
            - ``"JSON"`` or ``"Form"``: ``body`` must be a ``dict[str, Any]``;
              it is encoded as ``WFJSONValues`` / ``WFFormValues``.
            - ``"Plain Text"`` or ``"File"``: ``body`` is any Action or Value
              whose output is used verbatim as ``WFRequestVariable``.
            Omitted when ``None``.
        body_type: Controls how ``body`` is encoded. One of ``"JSON"``,
            ``"Form"``, ``"Plain Text"``, ``"File"``, ``"Multipart"``.
            Required if ``body`` is set; omitted otherwise.

    Note:
        ``ShowHeaders`` (a boolean plist key) is emitted as ``True`` whenever
        headers are provided. It controls whether Shortcuts.app shows the header
        editor in the UI — it has no effect on runtime behaviour but is present
        in every real shortcut that has headers configured.
    """

    identifier: ClassVar[str] = "is.workflow.actions.downloadurl"
    default_output_name: ClassVar[str] = "Contents of URL"

    url: ParamValue = None
    method: str = _DEFAULT_METHOD
    headers: dict[str, Any] | None = field(default=None)
    body: ParamValue = None
    body_type: str | None = None

    # ------------------------------------------------------------------
    # Factory methods — preferred over the direct constructor
    # ------------------------------------------------------------------

    @classmethod
    def get(
        cls,
        url: ParamValue,
        *,
        headers: dict[str, Any] | None = None,
    ) -> DownloadURL:
        """Return a GET request with no body.

        Args:
            url: Target URL — plain string, Text template, or Action output.
            headers: Optional dict of header name → value.

        Returns:
            A DownloadURL configured for GET with no body.
        """
        return cls(url=url, method="GET", headers=headers)

    @classmethod
    def json(
        cls,
        url: ParamValue,
        body: dict[str, Any],
        *,
        method: Literal["POST", "PUT", "PATCH", "DELETE"] = "POST",
        headers: dict[str, Any] | None = None,
    ) -> DownloadURL:
        """Return a request with a JSON body encoded as WFJSONValues.

        Args:
            url: Target URL — plain string, Text template, or Action output.
            body: Dict of key → value pairs. Values may be plain strings or
                any coercible Value/Action token.
            method: HTTP verb. Defaults to ``"POST"``.
            headers: Optional dict of header name → value.

        Returns:
            A DownloadURL configured with body_type="JSON".
        """
        return cls(url=url, method=method, headers=headers, body=body, body_type="JSON")

    @classmethod
    def plain_text(
        cls,
        url: ParamValue,
        body: ParamValue,
        *,
        method: Literal["POST", "PUT", "PATCH", "DELETE"] = "POST",
        headers: dict[str, Any] | None = None,
    ) -> DownloadURL:
        """Return a request with a plain-text body encoded as WFRequestVariable.

        Args:
            url: Target URL — plain string, Text template, or Action output.
            body: Any Value or Action whose output becomes the raw request body.
            method: HTTP verb. Defaults to ``"POST"``.
            headers: Optional dict of header name → value.

        Returns:
            A DownloadURL configured with body_type="Plain Text".
        """
        return cls(
            url=url, method=method, headers=headers, body=body, body_type="Plain Text"
        )

    @classmethod
    def file(
        cls,
        url: ParamValue,
        body: ParamValue,
        *,
        method: Literal["POST", "PUT", "PATCH", "DELETE"] = "POST",
        headers: dict[str, Any] | None = None,
    ) -> DownloadURL:
        """Return a request with a file body encoded as WFRequestVariable.

        Uses the same WFRequestVariable wire encoding as :meth:`plain_text`
        but sets body_type="File", which tells Shortcuts to treat the body
        as binary file data rather than text.

        Args:
            url: Target URL — plain string, Text template, or Action output.
            body: Any Value or Action whose output becomes the raw request body.
            method: HTTP verb. Defaults to ``"POST"``.
            headers: Optional dict of header name → value.

        Returns:
            A DownloadURL configured with body_type="File".
        """
        return cls(url=url, method=method, headers=headers, body=body, body_type="File")

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this HTTP request action."""
        if self.url is None:
            raise SchemaError(
                "DownloadURL requires a url — pass a string, Text template, "
                "or an Action whose output is a URL."
            )

        if self.body is not None and self.body_type is None:
            raise SchemaError(
                "DownloadURL: body_type is required when body is set. "
                "Use 'JSON', 'Form', 'Plain Text', or 'File'."
            )

        if self.body_type == "Form":
            raise SchemaError(
                "body_type='Form' is not yet verified against samples; "
                "use 'JSON' or 'Plain Text' instead"
            )

        out: dict[str, Any] = {}

        # --- URL ---
        # Apple's runtime reads WFURL as a WFTextTokenString — a bare
        # WFTextTokenAttachment imports as "No URL Specified".
        out["WFURL"] = coerce_text_field(self.url)

        # --- Method ---
        # Apple omits WFHTTPMethod for GET (it is the default).
        if self.method.upper() != _DEFAULT_METHOD:
            out["WFHTTPMethod"] = self.method.upper()

        # --- Headers ---
        if self.headers:
            # ShowHeaders is a UI toggle Apple emits when headers are configured.
            # It has no runtime effect but is present in every real shortcut
            # that has headers — omitting it causes the header editor to render
            # collapsed even when headers are set.
            out["ShowHeaders"] = True
            out["WFHTTPHeaders"] = _encode_wf_dict(self.headers)

        # --- Body ---
        if self.body is not None:
            out["WFHTTPBodyType"] = self.body_type

            if self.body_type in _DICT_BODY_TYPES:
                if not isinstance(self.body, dict):
                    raise SchemaError(
                        f"DownloadURL: body must be a dict when body_type={self.body_type!r}. "
                        f"Got {type(self.body).__name__}."
                    )
                # JSON → WFJSONValues; Form → WFFormValues
                # TODO: confirm WFFormValues is the correct key for body_type="Form".
                # It is not present in the currently decoded samples. The JSON key
                # (WFJSONValues) was confirmed from voice_note_to_github.xml.
                wf_body_key = (
                    "WFJSONValues" if self.body_type == "JSON" else "WFFormValues"
                )
                # ty's narrowing through ``self.body`` retains intersections like
                # ``Action & dict`` that are unreachable in practice; cast past it.
                out[wf_body_key] = _encode_wf_dict(cast(dict[str, Any], self.body))
            else:
                # Plain Text / File / Multipart — body is a single variable/action ref.
                out["WFRequestVariable"] = coerce_value(self.body)

        return out
