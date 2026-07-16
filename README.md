<h1>miniagent</h1>

**xAI's coding agent is 1,300,000 lines of Rust. Its user interface is bigger
than its agent.**

This is the 309-line spine underneath — a working coding agent that reads, edits,
and runs code in your repo — and a map of what the other 1,299,691 lines are
actually for.

[![license](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![code](https://img.shields.io/badge/code-309%20lines-brightgreen)](#the-numbers)
[![tests](https://img.shields.io/badge/tests-39%20offline-brightgreen)](#tests)

The map is **[REFERENCE.md](REFERENCE.md)**. The code is the exhibit.

---

## The whole agent

```python
messages = [system_prompt, user_prompt]
for turn in range(max_turns):
    reply = llm(messages, tools=SCHEMAS)
    if not reply.tool_calls:
        return reply.content           # the model stopped asking. it's done.
    for call in reply.tool_calls:
        result = dispatch(call)        # your code runs it, not the model
        messages.append(tool_result(call.id, result))
```

Everything else in every coding agent ever shipped is quality, interface, or
distribution wrapped around those ten lines.

Three things it makes obvious that reading about agents does not:

> **The model never touches your machine.** It emits JSON saying *"I'd like to
> call `bash` with `pytest`."* Your code runs it. The agency lives in the loop.
>
> **Termination isn't your decision.** The loop ends when the model stops asking
> for tools. There is no completion detector.
>
> **Everything is resent, every turn.** Turn 10 resends turns 1–9. The model is
> stateless — the transcript is the only memory there is.

---

## The numbers

| miniagent | | grok-build | |
|---|---:|---|---:|
| Code | **309** | `xai-grok-pager` (TUI) | **414,627** |
| Annotation | 260 | `xai-grok-shell` (runtime) | 335,843 |
| Total | 569 | `xai-grok-tools` | 112,275 |
| Tests | 39 | `xai-grok-workspace` | 76,730 |

Two things hide in that table.

**Their interface is larger than their agent** — 414k vs 336k. Most of a
production coding agent is not intelligence, and not even agent design.

**~110 of our 309 code lines are JSON tool schemas** — data describing tools to
the model, not logic. All six tool implementations together are ~50 lines. The
agent's real machinery is under 200.

---

## Install

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
export OPENAI_API_KEY=...
.venv/bin/miniagent "the tests are failing, fix them"
```

Any litellm model works: `--model claude-sonnet-5`, `--model openrouter/...`

| Flag | Effect |
|---|---|
| `--auto` | Skip confirmation before `bash` |
| `--resume` | Continue the latest session in this directory |
| `--session <id>` | Resume a specific session |
| `--model <str>` | Any litellm model string |
| `--max-turns <n>` | Cap loop iterations (default 25) |

---

## What it deliberately doesn't do

No MCP. No subagents. No TUI. No streaming. No scheduling. No memory system. No
slash commands. No compaction. No sandbox.

grok-build has every one of them. **[REFERENCE.md](REFERENCE.md) says why none of
them is the spine — and that list is the finding, not the backlog.**

Sort grok's 1.3M lines by *why they exist* and they fall into two piles:

- **Bets on model weakness** — goal decomposition, verification, anchored
  editing, compaction. These exist because the model isn't good enough yet.
  **They shrink as models improve.**
- **Bets on human needs** — the TUI, settings, sessions, MCP, crash handling.
  Nothing to do with model quality. **They grow forever.**

That's the honest answer to *what do 1.3M lines buy*: a shrinking pile and a
growing one. The growing pile is the bigger one.

### One deliberate flaw

`edit_file` uses **naive string matching on purpose**. It breaks when the model
targets text it misremembers from three turns ago.

That's not an oversight — it's the exact problem xAI built **hashline** to solve:
anchored editing where every line carries a content hash, three candidate
schemes, an 887-line benchmark with no LLM in it, shipped behind a *server-side
flag*. They haven't settled it either. Naive matching is the baseline they're
still measuring against.

---

## Tests

```bash
.venv/bin/pytest    # 39 tests, zero API calls
```

Every test runs against a `FakeLLM` returning scripted tool calls. The loop's
correctness has nothing to do with the model, so it's tested without one — the
same move grok-build makes in its hashline benchmark.

---

*Reference source: [xai-org/grok-build](https://github.com/xai-org/grok-build)
@ `b189869`, Apache 2.0. Every claim in [REFERENCE.md](REFERENCE.md) points at a
real path in that tree.*
