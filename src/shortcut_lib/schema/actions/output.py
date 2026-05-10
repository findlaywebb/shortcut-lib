"""StopAndOutput — terminate the shortcut and return a value to the caller.

Corpus coverage: 2 appearances.
  - samples/decoded/dictionary.xml      (WFOutput only)
  - samples/decoded/sort_lines.xml      (WFOutput + WFNoOutputSurfaceBehavior
                                          + WFResponse)

Jellycore facts (queried via
``jq '.actions[] | select(.identifier == "is.workflow.actions.output")'
data/jellycore_facts.json``):
  identifier        : is.workflow.actions.output
  display_name      : Output
  lowest_compat_host: iOS15
  parameter_keys    : WFOutput, noResultBehavior, WFResponse

Wire-key mapping (corpus vs jellycore internal names):
  jellycore key       → wire key
  WFOutput            → WFOutput             (the value to return)
  noResultBehavior    → WFNoOutputSurfaceBehavior  (what to do when there is
                        no run surface, e.g. "Respond")
  WFResponse          → WFResponse           (shared-sheet / share-extension
                        response value; corpus shows it mirrors WFOutput when
                        WFNoOutputSurfaceBehavior="Respond")

Contrast with :class:`~shortcut_lib.schema.actions.exit_shortcut.ExitShortcut`:
  - ``ExitShortcut``  (``is.workflow.actions.exit``) — aborts immediately,
    returns nothing.  No parameters.
  - ``StopAndOutput`` (``is.workflow.actions.output``) — terminates and
    *returns* a value to the caller.  This is what makes a shortcut usable
    as a sub-shortcut: the caller receives ``output`` as its result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_text_field
from shortcut_lib.schema.registry import register

#: Valid values for ``no_surface_behavior`` (``WFNoOutputSurfaceBehavior``).
#: ``None`` means omit the key (Apple omits it in the simplest case).
_VALID_NO_SURFACE_BEHAVIORS: frozenset[str] = frozenset({"Respond", "DoNothing"})


@register
@dataclass
class StopAndOutput(Action):
    """Terminate the shortcut and return *output* to the caller.

    Use this instead of :class:`~shortcut_lib.schema.actions.exit_shortcut.ExitShortcut`
    when your shortcut is designed to be called as a sub-shortcut: the
    return value is passed back to the parent as the result of its "Run
    Shortcut" action.

    When used in an automation (no calling context), ``no_surface_behavior``
    controls fallback behaviour — ``"Respond"`` sends the value to the
    share sheet; ``"DoNothing"`` silently discards it.

    Wire keys emitted (identifier ``is.workflow.actions.output``):

    - ``WFOutput`` — the value being returned (WFTextTokenString envelope).
      Required.
    - ``WFNoOutputSurfaceBehavior`` — optional; omitted when
      *no_surface_behavior* is ``None`` (the default, matching the
      dictionary.xml corpus sample).
    - ``WFResponse`` — optional shared-sheet response value; the
      sort_lines.xml corpus sample shows it mirrors *output* when
      ``WFNoOutputSurfaceBehavior="Respond"``.  Pass explicitly when you
      need a different value, or leave as ``None`` to omit.

    Example — sub-shortcut returns sorted lines::

        from shortcut_lib.schema.actions.output import StopAndOutput
        from shortcut_lib.schema.values import Output

        combined_ref = Output(uuid="E740F761-...", name="Combined Text")
        action = StopAndOutput(output=combined_ref)

    Example — same but also respond via share sheet::

        action = StopAndOutput(
            output=combined_ref,
            no_surface_behavior="Respond",
            response=combined_ref,
        )

    Contrast:

    - :class:`~shortcut_lib.schema.actions.exit_shortcut.ExitShortcut`
      aborts the shortcut without returning any value.

    Args:
        output: The value to return.  Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action`
            / :class:`~shortcut_lib.schema.base.Value` reference.
            Encoded as a ``WFTextTokenString`` slot.
        no_surface_behavior: Controls behaviour when there is no calling
            context.  ``None`` omits the key (simplest case, matches the
            majority of corpus samples).  ``"Respond"`` sends the output
            to the share sheet.  ``"DoNothing"`` silently discards it.
        response: Shared-sheet response value (``WFResponse``).  Only
            meaningful when *no_surface_behavior* is ``"Respond"``.
            ``None`` omits the key.
    """

    output: ParamValue = field(default=None)
    no_surface_behavior: str | None = None
    response: ParamValue = field(default=None)

    identifier: ClassVar[str] = "is.workflow.actions.output"
    default_output_name: ClassVar[str] = ""

    def _params(self) -> dict[str, Any]:
        if self.output is None:
            raise SchemaError(
                "StopAndOutput requires `output` — the value to return to the caller."
            )
        if (
            self.no_surface_behavior is not None
            and self.no_surface_behavior not in _VALID_NO_SURFACE_BEHAVIORS
        ):
            raise SchemaError(
                f"StopAndOutput: no_surface_behavior={self.no_surface_behavior!r} "
                f"is not valid.  Expected one of {sorted(_VALID_NO_SURFACE_BEHAVIORS)} "
                "or None."
            )
        out: dict[str, Any] = {}
        out["WFOutput"] = coerce_text_field(self.output)
        if self.no_surface_behavior is not None:
            out["WFNoOutputSurfaceBehavior"] = self.no_surface_behavior
        if self.response is not None:
            out["WFResponse"] = coerce_text_field(self.response)
        return out
