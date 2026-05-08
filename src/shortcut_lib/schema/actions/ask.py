"""AskForInput — prompt the user to type or speak a value."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError
from shortcut_lib.schema.registry import register

# Apple plist key is WFInputType, not "type" (Jellycore's field name).
_VALID_TYPES: frozenset[str] = frozenset(
    {"Text", "URL", "Number", "Date", "Time", "Date and Time"}
)

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
    """Prompt the user to enter a value.

    Input type controls the keyboard/picker shown. The ``default_answer``
    is routed to a type-specific WF* key:

    - ``Text`` / ``URL`` → ``WFAskActionDefaultAnswer``
    - ``Number`` → ``WFAskActionDefaultAnswerNumber``
    - ``Date`` / ``Time`` → ``WFAskActionDefaultAnswerDate`` (inferred)
    - ``Date and Time`` → ``WFAskActionDefaultAnswerDateAndTime`` (verified)

    Decimal/negative flags only emit for ``input_type="Number"``.

    Note: ``Ask`` is taken as a magic-variable singleton in
    ``shortcut_lib.schema.values``; this class is ``AskForInput``.

    Divergence from Jellycore: Jellycore's ``AskForInputParameter.swift``
    declares ``type`` as the field name; the real Apple plist key is
    ``WFInputType``.
    """

    identifier: ClassVar[str] = "is.workflow.actions.ask"
    default_output_name: ClassVar[str] = "Provided Input"

    prompt: str = ""
    input_type: str = "Text"
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

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.prompt:
            out["WFAskActionPrompt"] = self.prompt
        out["WFInputType"] = self.input_type
        if self.default_answer is not None:
            out[_DEFAULT_ANSWER_KEY[self.input_type]] = self.default_answer
        if self.input_type == "Number":
            if self.allows_decimal is not None:
                out["WFAskActionAllowsDecimalNumbers"] = self.allows_decimal
            if self.allows_negative is not None:
                out["WFAskActionAllowsNegativeNumbers"] = self.allows_negative
        return out
