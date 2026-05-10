"""ChooseFromList — present a runtime list and let the user pick items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class ChooseFromList(Action):
    """Present a runtime list and prompt the user to pick one or more items.

    Distinct from :class:`ChooseFromMenu` (which has fixed labelled cases
    known at build time): this action operates on a runtime list value.

    The ``prompt`` slot is ``WFTextTokenString`` per observed_envelope_types
    (``bare_string_slots``), so variable references are wrapped in the
    single-attachment template envelope by :func:`coerce_text_field`.

    Confirmed parameters (verified against samples/decoded/set_weekend_chores.xml
    and samples/decoded/dictionary.xml):
        WFInput                          — the list value to choose from
        WFChooseFromListActionPrompt     — optional text prompt shown to the user
        WFChooseFromListActionSelectMultiple — allow picking more than one item
        WFChooseFromListActionSelectAll  — default-select all items initially

    Args:
        input: The list value to present. Pass an Action output, a NamedVar,
            or any Value that resolves to a list at runtime.
        prompt: Text shown above the list. Omitted when empty (matches Apple).
            Coerced as a WFTextTokenString slot — variable references are
            automatically wrapped in the single-attachment template envelope.
        select_multiple: When True the user can tap multiple items. When None
            (default) the key is omitted and Apple defaults to single selection.
        select_all_initially: When True all items start pre-selected. Only
            meaningful alongside ``select_multiple=True``. When None the key
            is omitted.
    """

    identifier: ClassVar[str] = "is.workflow.actions.choosefromlist"
    default_output_name: ClassVar[str] = "Chosen Item"

    input: ParamValue = None
    prompt: ParamValue = ""
    select_multiple: bool | None = None
    select_all_initially: bool | None = None

    def _params(self) -> dict[str, Any]:
        """Emit WFInput, WFChooseFromListActionPrompt, and optional flags."""
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        if self.prompt:
            # bare_string_slots entry confirms this slot is WFTextTokenString.
            out["WFChooseFromListActionPrompt"] = coerce_text_field(self.prompt)
        if self.select_multiple is not None:
            out["WFChooseFromListActionSelectMultiple"] = self.select_multiple
        # WFChooseFromListActionSelectAll: Jellycore-only; absent from all corpus samples.
        if self.select_all_initially is not None:
            out["WFChooseFromListActionSelectAll"] = self.select_all_initially
        return out
