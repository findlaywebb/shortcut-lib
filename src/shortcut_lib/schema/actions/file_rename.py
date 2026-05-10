"""FileRename — rename a file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
    coerce_value,
)
from shortcut_lib.schema.registry import register


@register
@dataclass
class FileRename(Action):
    """Rename a file. Wraps ``is.workflow.actions.file.rename``.

    Jellycore: display_name "Rename File", iOS 15+, parameter_keys
    ["WFFile", "WFNewFilename"].

    Wire-format evidence (7 corpus appearances across
    samples/decoded/rename_files.xml and samples/decoded/dictionary.xml):

    - ``WFFile`` — always ``WFTextTokenAttachment`` (5/5 observed envelopes).
      Accepts a variable or action output referencing a file object.
    - ``WFNewFilename`` — always ``WFTextTokenString`` (5/5 observed envelopes).
      Accepts a templated string or plain string for the new filename.

    In 2 of 7 appearances (dictionary.xml lines 189, 292) the action has
    only ``WFFile`` and no ``WFNewFilename`` — both are demo/placeholder
    entries where the action was dropped without configuration.  All 5
    *configured* instances carry both keys.  Both fields are therefore
    treated as optional at the schema level (no runtime validation if
    both are None), but a shortcut that omits either will not execute
    usefully on device.

    Args:
        file: The file to rename. Pass an Action whose output is a file,
            an Output reference, or any Value/variable resolving to a file.
            Emitted under the ``WFFile`` key as WFTextTokenAttachment.
        new_name: The new filename. Pass a string, a Text template, or
            any Value resolving to a string.  Emitted under
            ``WFNewFilename`` as WFTextTokenString (Apple's observed format
            for this slot — single variable references are wrapped in the
            one-attachment template-string envelope).
    """

    identifier: ClassVar[str] = "is.workflow.actions.file.rename"
    default_output_name: ClassVar[str] = "Renamed File"

    file: ParamValue = None
    new_name: ParamValue = None

    def __post_init__(self) -> None:
        if self.file is None and self.new_name is not None:
            raise SchemaError(
                "FileRename: file must be set when new_name is set. "
                "Pass an Action output, Output reference, or NamedVar "
                "that resolves to a file."
            )

    def _params(self) -> dict[str, Any]:
        """Emit WFFile (WFTextTokenAttachment) and WFNewFilename (WFTextTokenString).

        Envelope choices follow the observed oracle
        (data/observed_envelope_types.json):
          WFFile       → WFTextTokenAttachment (5/5 corpus samples)
          WFNewFilename → WFTextTokenString    (5/5 corpus samples)
        """
        out: dict[str, Any] = {}
        if self.file is not None:
            # WFFile is a WFTextTokenAttachment slot — Apple emits a bare
            # variable reference envelope, not the template-string form.
            # rename_files.xml:10 / :19 / :6 and dictionary.xml:189 / :292
            # all confirm the plain WFTextTokenAttachment shape here.
            out["WFFile"] = coerce_value(self.file)
        if self.new_name is not None:
            # WFNewFilename is a WFTextTokenString slot — every configured
            # corpus appearance (rename_files.xml:10 / :19 / :51 / :53 / :6)
            # uses WFTextTokenString even for a single variable reference.
            # coerce_text_field rewraps a plain WFTextTokenAttachment into
            # the one-attachment template-string envelope to match this.
            out["WFNewFilename"] = coerce_text_field(self.new_name)
        return out
