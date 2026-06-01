# Designing a library for an LLM consumer

## The thesis

`shortcut-lib` is a Python library for authoring Apple Shortcuts whose primary
user is a language model, not a human. The human (Findlay) says what to build;
the model reads the registry, writes a spec, and emits a signed `.shortcut`
file. Once you accept that the consumer is a model, the design choices that
usually count as polish (error wording, docstring discipline, output size)
become the load-bearing interface. Everything below follows from taking that
premise literally.

## Three load-bearing design moves

### 1. Errors are recovery prompts, not tracebacks

A traceback is written for a human with a debugger. A model has neither, but it
does have one thing a stack frame cannot offer a human: it can act on a plain
instruction immediately. So every failure names the next tool to call.

When `shortcut_get_action_schema` is handed an unknown action, it does not
raise a `KeyError`; it raises with the recovery move spelled out
(`src/shortcut_lib/mcp/server.py:143`):

```python
raise ValueError(
    f"Unknown action {name_or_identifier!r}. "
    f"Call shortcut_list_actions(query={name_or_identifier[:16]!r}) "
    f"to find candidates."
) from None
```

The same contract is documented on `shortcut_validate_spec`: on failure
`error` is "an agent-recoverable message naming the offending action and the
next tool to call" (`server.py:164`). The tool docstrings state the policy
outright: "Errors are recovery prompts, never tracebacks" (`server.py:12`).

### 2. Docstrings are provenance-labelled instructions

The wire format for Apple Shortcuts is undocumented and inconsistent across
sibling actions, so a confidently-wrong docstring is worse than no docstring:
the model will trust it and emit a silently malformed shortcut. The project
encodes a source-confidence ladder, applied to every claim:

```
corpus  >  jellycore (parameter_keys)  >  Shortcuts.app UI  >  inference
```

Every parameter, every literal value, every default is labelled with its rung.
`SetVolume` is a clean example of the discipline under uncertainty: the corpus
contains only empty-parameter occurrences, so the docstring refuses to claim
confirmation it does not have (`src/shortcut_lib/schema/actions/set_volume.py:30`):

> "Jellycore names the key `WFVolume` ... corpus is silent (empty params) so
> no direct confirmation exists in the sample set."

The model reads that disclaimer through `shortcut_get_action_schema`, whose own
docstring tells it to: each parameter "is documented with source-confidence
labels (corpus-confirmed vs jellycore-listed vs UI-inferred) you should
respect" (`server.py:131`). Anti-hallucination is not a guardrail bolted on
after the fact; it is the authoring culture, expressed in the artifact the
model actually reads.

### 3. Output minimization protects the context window

A model pays for every token it reads back, and irrelevant tokens crowd out the
reasoning budget. So tool outputs are deliberately trimmed to the structural
minimum. `shortcut_decode` returns the action list with a few headline fields
and explicitly drops the full parameter blobs
(`server.py:230`):

> "not the full parameter blobs (those bloat context for no benefit; if you
> need the raw workflow dict, use the library directly)."

`shortcut_list_actions` paginates with `limit` / `offset` and reports
`has_more` rather than dumping all registered actions in one response
(`server.py:103`). The default of `coerce_text_field` vs `coerce_value` in the
schema base keeps emitted wire envelopes minimal too: only the fields the slot
semantics require are written. The model's context stays cheap by construction.

## How we measure it

The LLM-UX claim is testable, so there is a harness that tests it directly. The
graders are deterministic: the emitted `.shortcut` is decoded and checked
against structural assertions (`must_contain` identifiers, action-count bounds,
required surfaces), with no LLM-as-judge in the loop
(`evals/mcp/run_evals.py:300`). Each task runs k attempts and reports both
`pass@1` and `pass@k` (`run_evals.py:364`). Alongside correctness it records the
metrics that are specific to a model consumer: tool calls per task, input and
output tokens per task, and a recovery rate, where `recovery_expected` tasks
only pass if the model actually hit an error and recovered from it
(`run_evals.py:344`). Those three numbers are how we know the first three design
moves are paying off rather than just sounding good.

## Why this matters

The same discipline transfers to any tool surface a model consumes: MCP
servers, agent tool definitions, and SDK docstrings. Write the error as the
next instruction, label every claim with its confidence so the model does not
fabricate past the evidence, and spend context tokens only where they buy
reasoning. `shortcut-lib` happens to author Apple Shortcuts, but the artifact it
is really demonstrating is a method for building software that a model can use
well.
