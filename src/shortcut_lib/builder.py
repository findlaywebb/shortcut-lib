"""Shortcut builder — collects schema actions and emits the workflow dict."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar
from uuid import NAMESPACE_DNS, uuid5

from shortcut_lib.encode import SignMode, encode_to_bplist, sign_to_file
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.base import Action, RawAction, SchemaError
from shortcut_lib.schema.compose import RunWorkflow, _BoundSelf, _SelfRef
from shortcut_lib.schema.values import NamedVar


@dataclass(frozen=True)
class ImportQuestion:
    """A Setup-section prompt shown when the shortcut is imported.

    Apple's wire format calls this WFWorkflowImportQuestions; each
    entry targets a specific action's parameter and replaces it with
    the user's answer at import time.

    Args:
        action: The Action whose parameter receives the answer.
        parameter_key: The WF* slot on that action (e.g. WFTextActionText).
        question: The text shown to the user on the import sheet.
        default: Optional default value. Shape depends on the parameter:
            - text/string slots: a plain str
            - other slots: a dict matching Apple's expected shape (see
              start_pomodoro.xml for a Focus default of
              {DisplayString, Identifier})
        category: Wire-format Category. Defaults to "Parameter"
            (the only value seen in samples).
    """

    action: Action
    parameter_key: str
    question: str
    default: Any | None = None
    category: str = "Parameter"


def _derive_workflow_uuid(name: str) -> str:
    """Stable UUID derived from the shortcut's name.

    Re-running the same build script produces the same identifier, so an
    orchestrator that bakes a helper's UUID into a ``RunWorkflow`` keeps
    working across re-runs. Renaming a shortcut changes its identifier.
    """
    return str(uuid5(NAMESPACE_DNS, name)).upper()


# Subset of WFWorkflowTypes / WFQuickActionSurfaces values. Apple's full
# enum is in `~/Documents/FMP/tech/Apple_Shortcuts/Design_Intent.md` (or
# the iOS-Shortcuts-Reference attribution in docs/sources.md). Strings
# pass through verbatim, so unknowns aren't a hard error.
SURFACE_TO_TYPE: dict[str, str] = {
    "watch": "Watch",
    "widget": "NCWidget",
    "share": "ActionExtension",
    "menubar": "MenuBar",
    "quick-action": "QuickActions",
    "sleep": "Sleep",
}

# WFWorkflowClientVersion shipped with the iOS / macOS Shortcuts client used
# to extract our reference samples (iOS 26.x / macOS 26.x). Apple historically
# tolerates older client-version strings on import; bump this if a future
# release starts rejecting stale values. Tracked as FU-2 in docs/handoff.md.
_CLIENT_VERSION = "4033.0.4.3"


@dataclass
class Shortcut:
    """An authored shortcut.

    Build by adding Actions or control-flow constructs. Each ``add()``
    returns the same object for chaining and so the caller can reference
    its output:

        s = Shortcut(name="Demo")
        text = s.add(DictateText())
        s.add(SetClipboard(input=text))
        s.save_signed("Demo.shortcut")

    Args:
        name: Display name shown in the Shortcuts app.
        surfaces: Where this shortcut appears — any of "watch",
            "widget", "share", "menubar", "quick-action", "sleep". Or
            pass the raw Apple strings directly.
        min_client: Minimum Shortcuts client version. Defaults to 900
            (~iOS 16); raise for actions that need newer features.
    """

    name: str = "Untitled"
    surfaces: list[str] = field(default_factory=list)
    min_client: int = 900
    icon_glyph: int = 61512  # default to a generic icon
    icon_color: int = 4282601983  # red
    # Defaults to a UUID derived from `name` (stable across runs). Pass an
    # explicit value to override — useful when lifting an existing shortcut
    # that already has a UUID assigned in the wild.
    workflow_identifier: str | None = None
    accepted_input: list[str] = field(default_factory=list)
    output_classes: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    setup_questions: list[ImportQuestion] = field(default_factory=list)
    # Top-level WFWorkflow* keys not represented by an explicit attribute
    # above. Populated by `from_workflow` so a lift→emit round-trip preserves
    # everything (e.g. WFWorkflowNoInputBehavior, WFQuickActionSurfaces, the
    # original WFWorkflowClientVersion). On emit, values here override the
    # hardcoded defaults in `to_workflow`. WFWorkflowImportQuestions is now
    # managed by setup_questions, so it is no longer captured into _extra.
    _extra: dict[str, Any] = field(default_factory=dict)

    # Top-level keys derived from the explicit attributes above. Anything in
    # a decoded workflow NOT in this set is captured into `_extra`.
    _ATTRIBUTE_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "WFWorkflowMinimumClientVersion",
            "WFWorkflowMinimumClientVersionString",
            "WFWorkflowIcon",
            "WFWorkflowTypes",
            "WFWorkflowInputContentItemClasses",
            "WFWorkflowOutputContentItemClasses",
            "WFWorkflowActions",
            # Lifted into setup_questions, not _extra.
            "WFWorkflowImportQuestions",
        }
    )

    def __post_init__(self) -> None:
        if self.workflow_identifier is None:
            self.workflow_identifier = _derive_workflow_uuid(self.name)

    def add(self, action: Action) -> Action:
        """Append an action; return it so its output can be referenced."""
        if not isinstance(action, Action):
            raise SchemaError(
                f"Shortcut.add expects an Action, got {type(action).__name__}"
            )
        # Reject re-adds: each Action carries a UUID that's used for
        # output-reference resolution, so adding the same instance twice (or
        # adding it to a second Shortcut) silently produces a workflow with
        # duplicate UUIDs. Construct fresh Action instances per add site.
        for existing in self.actions:
            if existing is action:
                raise SchemaError(
                    f"Action instances aren't shareable: this "
                    f"{type(action).__name__} (uuid={action.uuid}) is already in "
                    f"this shortcut. Construct a new instance per add site."
                )
        # Bind any Self sentinel (including ones nested in control-flow
        # bodies) to this containing shortcut so emit doesn't need a second
        # pass over the action dicts.
        self._bind_self(action)
        self.actions.append(action)
        return action

    def _bind_self(self, action: Action) -> None:
        """Recursively rebind ``Self`` sentinels under ``action``.

        Walks the known control-flow body containers (``then``, ``otherwise``,
        ``body``, ``cases``). Some leaf actions reuse one of those names for
        unrelated state (e.g. ``DownloadURL.body`` is the request payload),
        so we type-guard on ``list`` before recursing.
        """
        if isinstance(action, RunWorkflow) and isinstance(action.target, _SelfRef):
            action.target = _BoundSelf(self)
        for attr in ("then", "otherwise", "body"):
            container = getattr(action, attr, None)
            if isinstance(container, list):
                for child in container:
                    if isinstance(child, Action):
                        self._bind_self(child)
        cases = getattr(action, "cases", None)
        if isinstance(cases, list):
            for case in cases:
                if isinstance(case, tuple) and len(case) == 2:
                    for child in case[1]:
                        if isinstance(child, Action):
                            self._bind_self(child)

    def extend(self, actions: list[Action]) -> None:
        """Append several actions in order."""
        for a in actions:
            self.add(a)

    def set(self, name: str, value: Any) -> NamedVar:
        """Bind ``value`` to a named variable; return a typed handle.

        Convenience wrapper for the common pattern::

            s.add(SetVariable(name=name, input=value))
            ref = NamedVar(name)

        Equivalent in wire format, but the returned :class:`NamedVar[T]`
        lives on a Python identifier — typos at later use sites become
        :class:`NameError` at static-type-check time rather than silent
        empty values on iOS.

        Example:

        .. code-block:: python

            token = s.set("Token", token_text)
            auth = Text("Bearer {t}", substitutions={"t": token})

        The phantom type parameter ``T`` is informational; annotate
        explicitly if you want it to read at the call site::

            token: NamedVar[str] = s.set("Token", token_text)
        """
        self.add(SetVariable(name=name, input=value))
        return NamedVar(name)

    def ask_on_import(
        self,
        action: Action,
        parameter_key: str,
        question: str,
        default: Any | None = None,
        category: str = "Parameter",
    ) -> None:
        """Register a Setup-section prompt targeting an action's parameter.

        The prompt is shown to the user when the shortcut is imported;
        their answer is written into ``parameter_key`` on ``action``
        before the shortcut is saved.  ``action`` must already have been
        add()ed to this Shortcut — ``to_workflow()`` will raise if not.

        Args:
            action: The action whose parameter slot receives the answer.
            parameter_key: The WF* key on that action (e.g. WFTextActionText).
            question: The text shown to the user on the import sheet.
            default: Optional pre-filled value.  Pass a plain ``str`` for
                text slots; pass a dict matching Apple's wire shape for
                other slots (e.g. ``{DisplayString, Identifier}`` for a
                Focus mode — see start_pomodoro.xml).
            category: Wire-format Category string. "Parameter" is the only
                value observed in samples; override only if needed.
        """
        if not isinstance(action, Action):
            raise SchemaError(
                f"ask_on_import expects an Action, got {type(action).__name__}"
            )
        self.setup_questions.append(
            ImportQuestion(
                action=action,
                parameter_key=parameter_key,
                question=question,
                default=default,
                category=category,
            )
        )

    def ask_text_on_import(self, question: str, default: str = "") -> Action:
        """Add a GetText action wired as a Setup prompt on import.

        Sugar for the common case where the caller wants the user to supply
        a text value at import time (e.g. a GitHub token or repo path).

        Internally:
        1. Adds a ``GetText(text=default)`` action via ``self.add()``.
        2. Registers an ``ImportQuestion`` targeting ``WFTextActionText``.
        3. Returns the ``GetText`` Action so its output can be referenced
           downstream (e.g. ``s.set("Token", token_text)``).

        Args:
            question: The text shown to the user on the import sheet.
            default: Pre-filled value shown in the prompt. Defaults to "".

        Returns:
            The newly added GetText Action.
        """
        get_text = self.add(GetText(text=default))
        self.ask_on_import(
            action=get_text,
            parameter_key="WFTextActionText",
            question=question,
            default=default if default else None,
        )
        return get_text

    def to_workflow(self) -> dict[str, Any]:
        """Emit the WFWorkflow* top-level dict ready for encoding."""
        # Build a Python-identity → flat-index map in a single pass.
        # Using id() rather than UUID avoids the problem of actions that have
        # no UUID key in their plist (e.g. is.workflow.actions.dnd.set in
        # start_pomodoro); those round-trip through RawAction(uuid="") and the
        # empty UUID can't distinguish one action from another.
        #
        # Each top-level Action in self.actions maps its Python id() to the
        # flat-index of its *first* emitted action dict (the head). Control-flow
        # constructs (If, ChooseFromMenu, …) expand to multiple flat entries;
        # setup questions targeting actions nested inside control-flow bodies
        # are out of scope for V1 — only the head action of each top-level
        # entry in self.actions is a valid question target.
        action_dicts: list[dict[str, Any]] = []
        flat_index_by_id: dict[int, int] = {}
        for action in self.actions:
            flat_index_by_id[id(action)] = len(action_dicts)
            action_dicts.extend(action.to_actions())

        # Emit WFWorkflowImportQuestions from setup_questions.
        import_questions: list[dict[str, Any]] = []
        for iq in self.setup_questions:
            idx = flat_index_by_id.get(id(iq.action))
            if idx is None:
                raise SchemaError(
                    f"ImportQuestion references an action "
                    f"(type={type(iq.action).__name__}) "
                    f"that is not present in this Shortcut. Call add() before "
                    f"ask_on_import()."
                )
            entry: dict[str, Any] = {
                "ActionIndex": idx,
                "Category": iq.category,
                "ParameterKey": iq.parameter_key,
                "Text": iq.question,
            }
            if iq.default is not None:
                entry["DefaultValue"] = iq.default
            import_questions.append(entry)

        # NB: WFWorkflowName is intentionally not emitted. None of the decoded
        # samples contain it; the Shortcuts app derives the display name from
        # the imported file's filename. Keeping it in self.name for
        # composition (RunWorkflow.workflowName) and signed-file naming only.
        types = [SURFACE_TO_TYPE.get(s, s) for s in self.surfaces]
        out: dict[str, Any] = {
            "WFWorkflowMinimumClientVersion": self.min_client,
            "WFWorkflowClientVersion": _CLIENT_VERSION,
            "WFWorkflowIcon": {
                "WFWorkflowIconGlyphNumber": self.icon_glyph,
                "WFWorkflowIconStartColor": self.icon_color,
            },
            "WFWorkflowTypes": types,
            "WFQuickActionSurfaces": [],
            "WFWorkflowInputContentItemClasses": list(self.accepted_input),
            "WFWorkflowOutputContentItemClasses": list(self.output_classes),
            "WFWorkflowImportQuestions": import_questions,
            "WFWorkflowHasOutputFallback": False,
            "WFWorkflowHasShortcutInputVariables": False,
            "WFWorkflowActions": action_dicts,
        }
        # Apple omits WFWorkflowMinimumClientVersionString when min_client is 0
        # (gallery shortcuts with no minimum). Otherwise it duplicates the int
        # as a string. Match that behaviour so lift→emit is a no-op.
        if self.min_client:
            out["WFWorkflowMinimumClientVersionString"] = str(self.min_client)
        # Captured non-attribute keys (from a prior lift) override the
        # hardcoded defaults. Newly-authored shortcuts have an empty _extra
        # so the defaults flow through unchanged.
        out.update(self._extra)
        return out

    def to_bplist(self) -> bytes:
        """Encode as a binary plist (unsigned)."""
        return encode_to_bplist(self.to_workflow())

    def save_signed(
        self, path: Path | str | None = None, *, mode: SignMode = "anyone"
    ) -> Path:
        """Encode, sign via the macOS shortcuts CLI, and write to disk.

        Args:
            path: Where to write the signed file. Defaults to
                ``~/Desktop/<name>.shortcut`` so the filename matches the
                shortcut's display name. Pass an explicit path to override.
            mode: Signing mode passed to ``shortcuts sign`` (``anyone`` for
                share-sheet imports, ``people-who-know-me`` for stricter
                distribution).

        Returns the resolved output path.
        """
        if path is None:
            path = Path.home() / "Desktop" / f"{self.name}.shortcut"
        else:
            path = Path(path)
        sign_to_file(self.to_workflow(), path, mode=mode)
        return path

    @classmethod
    def from_file(cls, path: Path | str, *, name: str | None = None) -> Shortcut:
        """Load a signed `.shortcut` file as an editable Shortcut wrapper.

        Convenience for ``decode_file(path).workflow → from_workflow(...)``.

        Args:
            path: Path to the signed `.shortcut` file.
            name: Display name for the resulting wrapper. Defaults to the
                file's stem.
        """
        from shortcut_lib.decode import decode_file

        path = Path(path)
        decoded = decode_file(path)
        return cls.from_workflow(decoded.workflow, name=name or path.stem)

    @classmethod
    def from_workflow(
        cls, workflow: dict[str, Any], *, name: str = "Lifted"
    ) -> Shortcut:
        """Lift a decoded workflow dict into a Shortcut for round-trip / edit.

        Each action in ``WFWorkflowActions`` becomes a :class:`RawAction`
        — bypasses the typed schema layer entirely so this works for
        any identifier, modelled or not. Use ``shortcut_lib.decode`` to
        get the source dict.

        Args:
            workflow: A decoded WFWorkflow* dict.
            name: Display name for the resulting Shortcut wrapper. The
                source dict doesn't carry a name (Apple uses the
                filename), so the caller passes one for our composition
                bookkeeping.
        """
        types = workflow.get("WFWorkflowTypes") or []
        icon = workflow.get("WFWorkflowIcon") or {}
        # Some gallery samples store min_client=0; preserve literal-zero
        # rather than coercing to the default.
        min_client = workflow.get("WFWorkflowMinimumClientVersion", 900)
        # Capture any top-level keys not represented by an explicit Shortcut
        # attribute so a lift→emit round-trip preserves the full dict.
        extra = {k: v for k, v in workflow.items() if k not in cls._ATTRIBUTE_KEYS}
        out = cls(
            name=name,
            surfaces=list(types),
            min_client=int(min_client),
            icon_glyph=icon.get("WFWorkflowIconGlyphNumber", 61512),
            icon_color=icon.get("WFWorkflowIconStartColor", 4282601983),
            accepted_input=list(
                workflow.get("WFWorkflowInputContentItemClasses") or []
            ),
            output_classes=list(
                workflow.get("WFWorkflowOutputContentItemClasses") or []
            ),
            _extra=extra,
        )
        for action in workflow.get("WFWorkflowActions") or []:
            ident = action.get("WFWorkflowActionIdentifier", "")
            params = action.get("WFWorkflowActionParameters") or {}
            uuid = params.get("UUID", "")
            out.actions.append(
                RawAction(uuid=uuid, raw_identifier=ident, raw_params=dict(params))
            )

        # Lift WFWorkflowImportQuestions into setup_questions.
        # All lifted actions are RawAction instances (from_workflow never
        # produces typed Action subclasses), so we reconstruct ImportQuestion
        # by looking up the action at ActionIndex. If an entry is malformed
        # (missing ActionIndex, or index out of range), fall back to storing
        # the raw dict in _extra under a private key so the wire format is
        # preserved without crashing. This is documented as the intended
        # fallback for RawAction-backed round-trips.
        raw_questions = workflow.get("WFWorkflowImportQuestions") or []
        fallback_raw: list[dict[str, Any]] = []
        for raw_q in raw_questions:
            idx = raw_q.get("ActionIndex")
            if idx is None or not (0 <= idx < len(out.actions)):
                # Malformed or out-of-range entry — preserve verbatim.
                fallback_raw.append(dict(raw_q))
                continue
            target_action = out.actions[idx]
            out.setup_questions.append(
                ImportQuestion(
                    action=target_action,
                    parameter_key=raw_q.get("ParameterKey", ""),
                    question=raw_q.get("Text", ""),
                    default=raw_q.get("DefaultValue"),
                    category=raw_q.get("Category", "Parameter"),
                )
            )
        if fallback_raw:
            # Store unlifted questions so to_workflow can re-emit them.
            # _extra keys override to_workflow's defaults; this key is
            # intentionally not in _ATTRIBUTE_KEYS so it flows through
            # out.update(self._extra) cleanly.
            out._extra["WFWorkflowImportQuestions"] = fallback_raw

        return out
