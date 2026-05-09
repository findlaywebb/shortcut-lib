# Architecture Review Round 1 — Product Evangelist

**Reviewer perspective:** Product Lead / Greenfield Evangelist
**Date:** 2026-05-09
**Scope:** Strategic ceiling, not current floor. What this lib becomes at the limit.
Other agents are pressure-testing feasibility. This document establishes the
strongest version of the thesis that is worth testing.

---

## 1. The Strongest Version of the Thesis

At its limit, shortcut-lib is the **Python SDK for personal AI automation on Apple
platforms** — the layer between a natural-language intent and a signed, running
workflow on your phone. Not a tool for building Shortcuts. A compiler for human
ambition into machine action.

The vault note → polish → GitHub commit shortcut is not a demo. It is proof of
concept for a new computing primitive: **an LLM that can extend itself onto your
device.** Claude Code, running on a laptop, authored a workflow that now lives on
an iPhone and executes without Claude present. That is a capability transfer. The
lib is the transfer medium.

The door this opens: any personal automation that would have required a developer
to manually drag blocks in a GUI can now be expressed in a conversation. "Make me
a shortcut that reads my clipboard, runs it through a writing prompt, and posts it
to my blog's draft API" is now a one-sentence build spec. The lib turns that
sentence into a file. The file runs on 1.5 billion devices.

**Elevator pitch:** "shortcut-lib is the Pydantic of Apple Shortcuts — the type-safe
Python layer that lets any LLM agent author, sign, and deploy iOS automations from
a conversation."

**Talk title:** *"Your AI Agent Can Now Ship to iPhone: Writing Apple Shortcuts in
Python with an LLM as the Author"*

**Pull quote:** "We didn't build a shortcut. We built a compiler. The shortcut was
the output."

What makes the vision worth a year: the lib sits at a genuinely uncrowded
intersection. Every major automation platform — Zapier, Make, n8n — is cloud-first
and connector-centric. They can't produce a signed `.shortcut` that runs offline
on a locked-down iPhone with on-device Apple Intelligence. Apple's own Shortcuts
editor is GUI-only, single-device, and has no API surface for programmatic
authoring. Existing Python Shortcuts libraries (`python-shortcuts` on PyPI, Cherri
as a transpiler) target humans as authors — they have no story for LLM ergonomics,
no registry introspection, no error-as-training-signal design. The lib you have
today already passes that bar. The question is whether it stays a personal tool or
becomes the canonical answer to "how does an LLM write a Shortcut?"

---

## 2. Greenfield Candidates

Ranked by ambition, highest first. Feasibility is the other agents' job.

---

### 2.1 The MCP Server — "Shortcut authoring as a Claude tool"

**Vision.** An MCP server that exposes the lib's authoring surface as Claude tools.
Any Claude Desktop user, any Claude Code session, any Pydantic AI agent — without
installing the lib, without writing Python — can say "create a shortcut that X" and
get a `.shortcut` file dropped onto their Desktop. The lib becomes ambient
infrastructure for the Claude ecosystem on Apple platforms.

The existing `mcp-server-apple-shortcuts` (recursechat) can only *run* existing
shortcuts — it cannot *create* them. That is the gap. A `shortcut-author` MCP
server would expose tools like `list_available_actions`, `build_shortcut` (takes a
workflow spec, returns a signed file path), `decode_shortcut` (takes a file path,
returns buzz format), and `validate_shortcut` (static checks before signing). The
MCP protocol is already how Claude receives custom tools; the lib is already the
implementation. The server is plumbing.

**What changes architecturally.** A thin `mcp/` directory — MCP server scaffold,
tool wrappers over the lib's public API, a schema serialisation layer that converts
workflow specs from Claude's JSON tool calls into `Shortcut` builder calls. The lib
itself does not change; the MCP server is a transport layer over it.

**What it makes possible.** Any agent framework that supports MCP — LangChain,
Pydantic AI, AutoGen, Claude — gets Shortcuts authoring as a first-class tool with
zero install cost for the end user. A Raycast extension, a Claude Desktop plugin,
a Home Assistant automation could all produce and deploy Shortcuts through the
same server. The lib stops being a Python library and becomes an ecosystem
capability.

---

### 2.2 The Natural-Language Compiler — "claude --task X --target ios"

**Vision.** A CLI interface: `shortcut-build "every morning at 7am, text me a
summary of my unread emails" --device ios`. The tool uses an LLM internally to
decompose the intent into actions, maps them to the schema registry, handles gaps
with `RawAction` passthrough, and emits a signed file. The human prompt is the
source code. The `.shortcut` is the binary.

This is not a chat interface. It is a compiler with a natural-language front end.
The compiler metaphor is important: it implies repeatability, diffability, version
control. The prompt goes into git; the `.shortcut` is an artefact. Running the
compiler twice on the same prompt should produce semantically equivalent output.

**What changes architecturally.** An `engine/` module — LLM-backed intent parser
that maps natural language to a structured workflow spec, a planner that resolves
missing actions against the action-facts dataset and `RawAction` fallback, a
validation loop that catches schema errors and retries with correction. The
`uv run shortcut-build` CLI is the entry point. This is essentially the `make-shortcut`
skill promoted to a standalone first-class tool with no manual scaffolding step.

**What it makes possible.** Non-developers — people who use iPhone Shortcuts but
never write code — can describe automations conversationally and receive working
files. RoutineHub contributors could use it to produce shortcuts at scale. Personal
AI systems (Claude, Siri, whatever Apple ships in macOS 27) could use the CLI as
a build tool in their own pipelines.

---

### 2.3 The Reverse Engineering Toolkit — "Explain and improve any Shortcut"

**Vision.** A tool that takes *any* `.shortcut` file — yours, downloaded from
RoutineHub, exported from a friend's iPhone — and produces: a plain-English
explanation of what it does, a security audit (hardcoded credentials, URL
destinations, data leakage paths), a diff-aware edit ("add a step that also sends
the result to Obsidian"), and a provenance record ("this shortcut calls three
external APIs, here is what each receives"). This is the `decode-shortcut` skill
extrapolated into a full intelligence layer.

The community angle is real: RoutineHub has thousands of shortcuts of unknown
quality. There is no tooling to audit them before running. A `shortcut-audit`
command that flags secrets, identifies external calls, and explains behaviour in
plain language is a genuine security and usability gap that no existing tool fills.
It also creates a natural on-ramp — users come for the auditor, stay for the
author.

**What changes architecturally.** Expand the `--format buzz` decode path into a
structured analysis API. Add an `Analyser` class that walks the decoded action list
and emits typed findings (ExternalCall, HardcodedCredential, DataPath, ControlFlow
summary). Wire LLM interpretation over the top for plain-English narration. The
decoder already does the hard work; the analysis layer is a structured pass over
its output.

**What it makes possible.** A RoutineHub browser extension that shows a security
badge. A `pre-import` hook in a hypothetical Shortcuts management tool. A diff
viewer for shortcut versions. A "what changed between v1 and v2 of this shortcut"
answer that is currently impossible to produce without manually diffing two
unreadable bplist files.

---

### 2.4 The Cross-Platform Automation DSL — "One spec, many runtimes"

**Vision.** The lib's Python builder is already a DSL for describing automation
intent. That DSL could emit to targets other than Apple Shortcuts. Raycast
extensions use TypeScript; Alfred workflows use XML with AppleScript/bash runners;
Hammerspoon uses Lua; n8n uses JSON node graphs. The *intent* — "when I do X, do
Y" — is the same across all of them. The encoding is different.

A `Target` abstraction in the builder layer would let a single Python workflow spec
emit to multiple runtimes. Not every action maps everywhere — that is fine. The
lib ships a `shortcuts` target (current), a `raycast` target (new), an `n8n` target
(new). Actions that have no equivalent on the target platform raise a clear
`NotSupportedOnTarget` error, which the LLM can handle by suggesting an alternative.

**What changes architecturally.** Introduce a `Target` protocol and a `CodegenBackend`
ABC. The current bplist encoder becomes `ShortcutsBackend`. Add `RaycastBackend`
(emits a TypeScript extension scaffold) and `N8nBackend` (emits a node graph JSON).
The schema layer stays; backends are adapters. The `Shortcut` builder gains a
`target=` parameter.

**What it makes possible.** An LLM can author once and deploy anywhere. "Make me a
workflow that, on Mac, I can run from Raycast, and on iPhone, I can run as a
Shortcut" becomes a single build command with two outputs. The lib becomes the
Pandoc of personal automation — a universal intermediate representation between
human intent and platform-specific execution.

---

### 2.5 The Provenance Layer — "AI-authored Shortcuts with receipts"

**Vision.** Every shortcut produced by the lib carries a metadata sidecar: who
authored it (human/LLM), what prompt produced it, what version of the lib and
schema, what date, and a cryptographic hash of the workflow actions. When shared
on RoutineHub or iCloud, the sidecar travels with it. Users can verify origin,
diff versions, and trace edits back to the natural-language spec.

This is the infrastructure for a new kind of shortcut-sharing ecosystem — not "here
is a file," but "here is an auditable automation with a full history." It turns the
lib into a lightweight publishing platform. The RoutineHub model is upload-and-hope;
the provenance model is sign-and-verify.

**What changes architecturally.** A `Provenance` dataclass attached to `Shortcut`
at construction time. `save_signed()` serialises it to a companion `.shortcut.meta.json`
file alongside the binary. A `shortcut-verify` CLI command that reads the sidecar
and reports origin, hash, and diff summary. The bplist format itself cannot carry
arbitrary metadata without breaking Apple's parser, so the sidecar approach is the
right one.

**What it makes possible.** AI-authored shortcuts that are transparent about their
origin. A community norm of "LLM-assisted, human-reviewed" as a quality signal.
An audit trail for shortcuts that access sensitive APIs. Long-term: a registry of
known-good, provenance-stamped shortcuts that any user can pull and trust.

---

### 2.6 (Bonus, furthest out) The App Intents Bridge

**Vision.** App Intents are the future of Apple automation. They are the API surface
that Siri, Spotlight, Focus Filters, the Action Button, and Control Center widgets
all call. They are also entirely developer-authored — there is no visual editor, no
GUI authoring surface. They are Swift code. But they compose with Shortcuts: an
App Intent becomes a Shortcuts action the moment a developer adds
`@available(iOS 16+)` to a `struct` that conforms to `AppIntent`.

The lib could become a Python scaffolding layer for App Intents — not compiling to
Swift (too far), but generating the Swift scaffolding that an LLM (GitHub Copilot,
Xcode Intelligence) can then wire into a real app. "Add an App Intent to my Notes
app that accepts a title and body and creates a note" → Python spec → Swift
scaffold → Xcode. The lib owns the parameter modelling and the metadata; the IDE
owns the compilation.

This is speculative — it requires deep Swift knowledge in the schema layer. But it
is the answer to the question "what does the lib become if Apple shifts everything
to App Intents?" The answer is: it shifts too, because the primitives are the same.
Actions have identifiers, parameters, types, and wire formats. The lib already
knows how to model that.

---

## 3. Top 3 Strategic Moves

These are not features. They are signals — each one commits the lib to a public
thesis that other people can react to.

---

### Move 1 — Publish the MCP server and call it `shortcuts-mcp`

**The move.** Build the MCP server (Greenfield 2.1) and publish it to npm/PyPI as
`shortcuts-mcp`. Submit it to the MCP server directory. Write a single blog post:
*"I built an MCP server that lets Claude write Apple Shortcuts. Here is what
happened."* Ship it with three worked examples: a clipboard-to-GitHub shortcut
(already done), a morning briefing shortcut, and a "reply to this email with a
summary" share-sheet shortcut.

**What it signals.** The lib is not a personal tool — it is infrastructure. It
speaks the protocol that the Claude ecosystem already uses. Every Claude Desktop
user on macOS is now a potential user. The barrier to entry is `claude mcp add
shortcuts-mcp` — one command.

**Why this is the right first move.** The MCP ecosystem is early and the Apple
automation gap is real. `mcp-server-apple-shortcuts` (the existing one) can only
run shortcuts. This one can *create* them. That is a qualitatively different
capability. The first server that fills that gap will own the mindshare. The lib
already has the implementation; the MCP wrapper is a week of work.

---

### Move 2 — Rename the project to `shortcuts-sdk` and add a tagline

**The move.** The name `shortcut-lib` describes an implementation detail. It says
nothing about the role the project plays or the audience it serves. Rename to
`shortcuts-sdk` (or `apple-shortcuts-sdk`, pending namespace availability). Adopt
a tagline: *"The Python SDK for authoring Apple Shortcuts — designed for LLM
agents."*

**What it signals.** This is an SDK — it has a defined audience (developers, LLM
agents), a defined target platform (Apple), and a defined purpose (authoring). The
word "SDK" invites comparison with Anthropic's own Claude Agent SDK, with
`google-genai`, with `pydantic-ai`. It says: this lib takes the same role in the
Apple automation space that those libs take in the LLM space. It is a first-class
developer tool, not a personal script.

**Why this matters beyond vanity.** Names are how projects get discovered. Right
now, someone searching "Python Apple Shortcuts" finds `python-shortcuts` (last
updated years ago, no LLM story) and Cherri (a transpiler with its own syntax, not
Python). The name `apple-shortcuts-sdk` + a README section titled "Why LLM agents
need this" + the MCP server mention will index cleanly on the searches that matter.

---

### Move 3 — Build and publish the `shortcut-audit` tool as a standalone CLI

**The move.** Extract the decode → analyse → explain pipeline into a standalone CLI
that any user can run with `uvx shortcut-audit <file.shortcut>`. It outputs: a
plain-English description of what the shortcut does, a list of external API calls
with destinations, a list of any apparent hardcoded credentials, and an overall
trust rating (green / yellow / red). No authoring, no encoding — pure read-only
intelligence. Give it a README section called "Before you run a shortcut from the
internet."

**What it signals.** The lib is not just for people who want to *write* shortcuts.
It is for anyone who cares about shortcuts — which is everyone who uses iOS
automation. The auditor is the widest possible on-ramp. It creates a reason to
discover the lib that does not require any interest in Python or LLM authoring. The
user who runs `shortcut-audit` on a RoutineHub file today is the user who asks
"wait, can I use this to *make* shortcuts?" tomorrow.

**Why this is the right third move (not the first).** The auditor requires the
decoder to be robust on arbitrary shortcuts, not just ones the lib authored. That
means broader action coverage, better `RawAction` handling, and more surface area
than the current 21 leaf actions. It should follow the MCP server (which validates
the authoring story) and the rename (which establishes the brand). By the time the
auditor ships, the lib has a name, a tagline, and a public track record. The
auditor confirms the lib is a full-cycle Shortcuts tool, not just an author.

---

## Appendix — The Competitive Gap in One Table

| Platform | Can produce `.shortcut` files | LLM ergonomics | Apple-native signing | Offline / on-device |
|---|---|---|---|---|
| Zapier / Make / n8n | No | Yes (workflow authoring) | No | No |
| Apple Shortcuts.app | Yes (GUI only) | No | Yes | Yes |
| `python-shortcuts` (PyPI) | Yes | No (human author) | No | N/A |
| Cherri (transpiler) | Yes | Partial (LLM can write Cherri syntax) | No | N/A |
| `mcp-server-apple-shortcuts` | No (run only) | Yes (MCP tools) | N/A | macOS only |
| **shortcut-lib (today)** | **Yes** | **Yes (designed for it)** | **Yes** | **Yes** |
| **shortcuts-sdk (target)** | **Yes** | **Yes + MCP server** | **Yes** | **Yes** |

The gap is real. No existing tool combines all four columns. The lib already
occupies that intersection; the strategic moves above make it visible.
