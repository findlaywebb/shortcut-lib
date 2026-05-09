"""ReadingList — add a URL to Safari's Reading List.

Wire-format verified against two decoded corpus samples:
- ``samples/decoded/read_later.xml``:7  (WFURL via ActionOutput)
- ``samples/decoded/dictionary.xml``:211 (WFURL via ActionOutput)

Key distinction from DownloadURL: the WFURL slot here uses a bare
``WFTextTokenAttachment`` envelope (i.e. ``coerce_value``), not the
``WFTextTokenString`` wrapper that DownloadURL requires. Both corpus
appearances use ``WFTextTokenAttachment`` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class ReadingList(Action):
    """Add a URL to Safari's Reading List.

    Wraps ``is.workflow.actions.readinglist``.

    Args:
        url: The URL to add. Pass an Action whose output is a URL, a
            :class:`~shortcut_lib.schema.values.NamedVar`, or any Value.
            When ``None`` the ``WFURL`` key is omitted (the action still
            imports, matching the third corpus appearance where no
            ``WFURL`` key is present).

    Note:
        Unlike ``DownloadURL``, this action's ``WFURL`` slot is serialised
        as a bare ``WFTextTokenAttachment`` (via :func:`coerce_value`), not
        a ``WFTextTokenString`` wrapper. Both corpus appearances confirm
        this. Using ``coerce_text_field`` here would produce a different
        envelope than what Apple emits.
    """

    url: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.readinglist"
    default_output_name: ClassVar[str] = "Reading List"

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this Reading List action."""
        out: dict[str, Any] = {}
        if self.url is not None:
            out["WFURL"] = coerce_value(self.url)
        return out
