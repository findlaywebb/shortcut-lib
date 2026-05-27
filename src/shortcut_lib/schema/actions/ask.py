"""AskForInput — prompt the user for a typed value via a system dialog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_text_field
from shortcut_lib.schema.registry import register

# Closed set of input types shown in Shortcuts.app's Ask for Input action.
# Apple plist key is WFInputType, not "type" (Jellycore's field name).
WFAskInputType = Literal["Text", "URL", "Number", "Date", "Time", "Date and Time"]
_VALID_TYPES: frozenset[str] = frozenset(get_args(WFAskInputType))

# Maps input_type to the WF* parameter key Apple uses for default_answer.
# "Date and Time" is verified via samples/decoded/add_expiry_reminder.xml.
# "Date" and "Time" alone are inferred by analogy and have not been
# verified against decoded samples — if you find one, update this map.
_DEFAULT_ANSWER_KEY: dict[str, str] = {
    "Text": "WFAskActionDefaultAnswer",
    "URL": "WFAskActionDefaultAnswer",
    "Number": "WFAskActionDefaultAnswerNumber",
    "Date": "WFAskActionDefaultAnswerDate",
    "Time": "WFAskActionDefaultAnswerDate",
    "Date and Time": "WFAskActionDefaultAnswerDateAndTime",
}


@register
@dataclass
class AskForInput(Action):
    """Ask for Input — prompt the user for a typed value via a system dialog.

    Emits ``is.workflow.actions.ask``. Shows a system dialog with a text
    field, number pad, URL field, or date/time picker depending on
    ``input_type``. The user's response is returned as a text string.

    For speech-to-text / dictation flows, use :class:`~shortcut_lib.schema.actions.dictate_text.DictateText`
    instead — it opens the system speech-recognition interface and
    returns transcribed text. Ask shows a text dialog (the on-screen
    keyboard may offer a dictation button, but that's a keyboard
    feature, not part of the action's contract).

    Prefer the type-specific factory methods — they expose only the
    parameters valid for that input type, so an invalid combination is a
    ``TypeError`` at the call site rather than a ``SchemaError`` after
    construction::

        ask = AskForInput.text(prompt="Name?")
        num = AskForInput.number(prompt="How many?", allows_decimal=True)
        dt  = AskForInput.datetime(prompt="When?")

    The ``allows_decimal`` and ``allows_negative`` keyword arguments appear
    only on :meth:`number` — passing them to ``.text()`` or any other
    factory is a ``TypeError`` at the call site (Python's normal kwarg
    check), not a deferred ``SchemaError``.

    Args:
        prompt: The question shown above the input field (``WFAskActionPrompt``).
            Accepts a plain string, a :class:`~shortcut_lib.schema.values.Text`
            template, or any Action/Value. Omitted from the plist when empty.
        input_type: The keyboard/picker mode (``WFInputType``). One of
            ``"Text"``, ``"URL"``, ``"Number"``, ``"Date"``, ``"Time"``,
            ``"Date and Time"``. Defaults to ``"Text"``.
        default_answer: Pre-filled answer. The plist key depends on
            ``input_type``:

            - ``"Text"`` / ``"URL"`` → ``WFAskActionDefaultAnswer``
            - ``"Number"`` → ``WFAskActionDefaultAnswerNumber``
            - ``"Date"`` / ``"Time"`` → ``WFAskActionDefaultAnswerDate`` (inferred)
            - ``"Date and Time"`` → ``WFAskActionDefaultAnswerDateAndTime`` (verified)

            Omitted when ``None``.
        allows_decimal: If ``True``, the number pad allows a decimal point
            (``WFAskActionAllowsDecimalNumbers``). Only valid for
            ``input_type="Number"``; raises :class:`~shortcut_lib.schema.base.SchemaError`
            otherwise. Omitted when ``None``.
        allows_negative: If ``True``, negative numbers are accepted
            (``WFAskActionAllowsNegativeNumbers``). Only valid for
            ``input_type="Number"``. Omitted when ``None``.

    Returns:
        The user's response as a text string (output name: "Provided Input").

    Quirks:
        ``WFAskActionImmediateDictation`` (bool) appears in some corpus samples
        (e.g. ``samples/decoded/add_expiry_reminder.xml:11``) but is not
        exposed here — it enables dictation-first mode and is not configurable
        via this class. Use a :class:`~shortcut_lib.schema.base.RawAction` if
        you need it.

        Jellycore names the field ``type``; the real plist key is
        ``WFInputType``.

    Sample citations:
        samples/decoded/add_expiry_reminder.xml:11 — Text type with prompt.
        samples/decoded/add_expiry_reminder.xml:47 — Date and Time type with
        ``WFAskActionDefaultAnswerDateAndTime``.
    """

    identifier: ClassVar[str] = "is.workflow.actions.ask"
    default_output_name: ClassVar[str] = "Provided Input"

    prompt: ParamValue = ""
    input_type: WFAskInputType = "Text"
    default_answer: str | None = None
    allows_decimal: bool | None = None
    allows_negative: bool | None = None

    def __post_init__(self) -> None:
        if self.input_type not in _VALID_TYPES:
            raise SchemaError(
                f"AskForInput.input_type={self.input_type!r} is not a "
                f"valid Apple input type. Use one of {sorted(_VALID_TYPES)}."
            )
        # Decimal / negative flags are only meaningful for Number type.
        if self.input_type != "Number":
            for flag, name in (
                (self.allows_decimal, "allows_decimal"),
                (self.allows_negative, "allows_negative"),
            ):
                if flag is not None:
                    raise SchemaError(
                        f"AskForInput.{name} only applies to "
                        f"input_type='Number'; got input_type="
                        f"{self.input_type!r}."
                    )

    # ------------------------------------------------------------------
    # Factory methods — preferred over the direct constructor
    # ------------------------------------------------------------------

    @classmethod
    def text(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for plain-text keyboard input."""
        return cls(prompt=prompt, input_type="Text", default_answer=default_answer)

    @classmethod
    def url(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for URL keyboard input."""
        return cls(prompt=prompt, input_type="URL", default_answer=default_answer)

    @classmethod
    def number(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
        allows_decimal: bool | None = None,
        allows_negative: bool | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for numeric keyboard input.

        Only this factory exposes ``allows_decimal`` and
        ``allows_negative`` — the flags are meaningless for other input
        types, so passing them to ``.text()``, ``.url()``, etc. is a
        ``TypeError`` at the call site rather than a deferred
        ``SchemaError``.
        """
        return cls(
            prompt=prompt,
            input_type="Number",
            default_answer=default_answer,
            allows_decimal=allows_decimal,
            allows_negative=allows_negative,
        )

    @classmethod
    def date(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for date picker input."""
        return cls(prompt=prompt, input_type="Date", default_answer=default_answer)

    @classmethod
    def time(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for time picker input."""
        return cls(prompt=prompt, input_type="Time", default_answer=default_answer)

    @classmethod
    def datetime(
        cls,
        *,
        prompt: ParamValue = "",
        default_answer: str | None = None,
    ) -> AskForInput:
        """Return an AskForInput configured for date-and-time picker input."""
        return cls(
            prompt=prompt, input_type="Date and Time", default_answer=default_answer
        )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.prompt:
            # WFAskActionPrompt is a WFTextTokenString slot when not literal —
            # variable refs need the single-attachment templated envelope.
            out["WFAskActionPrompt"] = coerce_text_field(self.prompt)
        out["WFInputType"] = self.input_type
        if self.default_answer is not None:
            out[_DEFAULT_ANSWER_KEY[self.input_type]] = self.default_answer
        if self.input_type == "Number":
            if self.allows_decimal is not None:
                out["WFAskActionAllowsDecimalNumbers"] = self.allows_decimal
            if self.allows_negative is not None:
                out["WFAskActionAllowsNegativeNumbers"] = self.allows_negative
        return out
