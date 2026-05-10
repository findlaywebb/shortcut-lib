"""SendMessage — send an iMessage or SMS via Apple Messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_text_field
from shortcut_lib.schema.registry import register

# Recipient encoding note
#
# running_late.xml (line 3) is the only corpus sample with this key present.
# Its WFContactFieldValues array was empty — the user had not filled in contacts
# at shortcut-authoring time.  Apple's WFContactFieldValue envelope holds an
# array of contact-handle dicts whose internal structure (phone numbers, email
# hashes, CNDB record IDs) is non-trivial and varies by iOS version.  V1 models
# the recipients slot as a raw ParamValue; callers pass a pre-built wire dict.
# If recipients is None the key is omitted and Apple prompts on-device.
#
# Batch-4 follow-up: provide a helper wrapping a list of phone / email strings
# once the contact-handle format is confirmed against a populated sample.


@register
@dataclass
class SendMessage(Action):
    """Send an iMessage or SMS through Apple Messages.

    ``WFSendMessageContent`` is a WFTextTokenString slot — plain strings,
    :class:`~shortcut_lib.schema.values.Text` templates, and
    :class:`~shortcut_lib.schema.values.Output` references are all accepted.

    ``recipients`` accepts a pre-built ``WFContactFieldValue`` wire dict.
    Pass ``None`` (the default) to omit the field; Apple will prompt the
    user to choose recipients on-device.

    Minimal example — prompts for recipients at runtime::

        from shortcut_lib.schema.actions.send_message import SendMessage

        msg = SendMessage(message="On my way!")

    Full example — static message body, pre-built recipient envelope::

        from shortcut_lib.schema.actions.send_message import SendMessage
        from shortcut_lib.schema.values import NamedVar, Text

        body = Text("Running {mins} minutes late", substitutions={"mins": NamedVar("Delay")})
        msg = SendMessage(
            message=body,
            recipients={
                "Value": {"WFContactFieldValues": []},
                "WFSerializationType": "WFContactFieldValue",
            },
        )

    Args:
        message: The message body. Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or an
            :class:`~shortcut_lib.schema.values.Output` reference.
            Required — raises :class:`~shortcut_lib.schema.base.SchemaError`
            if empty or ``None``.
        recipients: Pre-built ``WFContactFieldValue`` wire dict, or ``None``
            to omit the field (Apple prompts on-device). The internal contact
            handle format is V1 unverified — pass a raw dict captured from a
            decoded shortcut. See the module-level note for details.
    """

    identifier: ClassVar[str] = "is.workflow.actions.sendmessage"

    message: ParamValue = field(default=None)
    recipients: ParamValue = field(default=None)

    def __post_init__(self) -> None:
        if self.message is None or self.message == "":
            raise SchemaError(
                "SendMessage.message is required — provide the text to send "
                "(a plain string, Text template, or Action output)."
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        # WFSendMessageContent is a WFTextTokenString slot. coerce_text_field
        # wraps Action / Value references into the single-attachment envelope
        # Apple expects; plain strings pass through unchanged.
        # Evidence: dictionary.xml:173, markup_and_send.xml:1, running_late.xml:3.
        out["WFSendMessageContent"] = coerce_text_field(self.message)
        if self.recipients is not None:
            # WFContactFieldValue envelope. Passed through verbatim — the
            # caller is responsible for the inner WFContactFieldValues shape.
            # Evidence: running_late.xml:3 (WFContactFieldValues array was empty).
            out["WFSendMessageActionRecipients"] = self.recipients
        return out
