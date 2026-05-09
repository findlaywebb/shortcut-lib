"""SendEmail — compose and optionally send an email."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class SendEmail(Action):
    """Compose an email, optionally auto-sending without the Mail compose sheet.

    All three corpus appearances carry ``WFSendEmailActionInputAttachments``
    as a WFTextTokenString — the combined body and file-attachment payload.
    ``WFSendEmailActionSubject`` appears in one sample as a WFTextTokenString.
    ``WFSendEmailActionShowComposeSheet`` appears as a boolean in one sample.

    Recipients were not observed in any corpus sample (the action opens a
    compose window pre-filled with whatever is provided). If recipient
    encoding is ever needed, pass a pre-built wire-format dict via
    ``to`` and it will be emitted verbatim — the envelope shape is
    unverified and punted to a future schema revision.

    Note:
        ``WFSendEmailActionInputAttachments`` key name is Apple's own — it
        covers both the email body text and any attached files. Despite the
        name, passing a plain string or a Text template as ``body`` is the
        common case and works correctly at runtime.

    Args:
        body: The email body and attachments (WFTextTokenString slot). Accepts
            a plain string, a :class:`~shortcut_lib.schema.values.Text`
            template, or an :class:`~shortcut_lib.schema.values.Output`
            reference.  ``None`` omits the key.
        subject: The email subject line (WFTextTokenString slot). Same rules
            as ``body``.  ``None`` omits the key.
        to: Recipient address(es). The wire-format encoding was not observed in
            the corpus; pass a pre-built envelope dict for advanced use.
            ``None`` omits the key entirely.
        show_compose_sheet: If ``True``, the Mail compose sheet is shown before
            sending so the user can review or edit.  If ``False``, the email is
            sent automatically.  ``None`` omits the key (Apple default: show
            the sheet).
    """

    body: ParamValue = field(default=None)
    subject: ParamValue = field(default=None)
    to: ParamValue = field(default=None)
    show_compose_sheet: bool | None = None

    identifier: ClassVar[str] = "is.workflow.actions.sendemail"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.body is not None:
            out["WFSendEmailActionInputAttachments"] = coerce_text_field(self.body)
        if self.subject is not None:
            out["WFSendEmailActionSubject"] = coerce_text_field(self.subject)
        if self.to is not None:
            # Recipient envelope shape was not observed in the corpus; emit
            # whatever the caller provides verbatim (pass-through).
            from shortcut_lib.schema.base import coerce_value

            out["WFSendEmailActionToRecipients"] = coerce_value(self.to)
        if self.show_compose_sheet is not None:
            out["WFSendEmailActionShowComposeSheet"] = self.show_compose_sheet
        return out
