<h1>miniagent</h1>

**xAI open-sourced their coding agent. Its user interface is bigger than its
agent** — 414,627 lines of TUI against 335,843 of runtime.

So I rebuilt the spine in **378 lines** to find out what the other 1,299,622 are
actually for.

[![license](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![spine](https://img.shields.io/badge/spine-378%20lines-brightgreen)](#the-numbers)
[![ci](https://github.com/Ruthwik-Data/miniagent/actions/workflows/ci.yml/badge.svg)](https://github.com/Ruthwik-Data/miniagent/actions/workflows/ci.yml)
[![tests](https://img.shields.io/badge/tests-51%20offline-brightgreen)](#running-it)

![miniagent finding and fixing a real bug](demos/demo.gif)

The answer is **[REFERENCE.md](REFERENCE.md)** — a subsystem-by-subsystem map
from these 378 lines to [grok-build](https://github.com/xai-org/grok-build)'s 1.3
million. The code is the exhibit.

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

**The model never touches your machine** — it emits JSON requesting a call, your
code runs it. **Termination isn't your decision** — the loop ends when the model
stops asking. **Everything is resent every turn** — the model is stateless, so the
transcript is the only memory there is.

Everything in every coding agent ever shipped is quality, interface, or
distribution wrapped around those ten lines.

---

## Then I ran it, and it broke in three ways I didn't predict

**The bug I shipped on purpose refused to fail.** `edit_file` uses naive string
matching, deliberately, to rediscover the problem xAI built
[hashline](REFERENCE.md#tools-edit-and-write) to solve. Two attempts, five
sequential edits to one line, no re-reads — `gpt-4o-mini` tracked every one. It
didn't reproduce.

**`grep` found the agent's own transcript and fed it back.** It searched
`.miniagent/sessions/` — the file the running loop was writing. **142,984 tokens
against a 128,000 limit, in six turns.** Not context drift, recursion. That's what
grok's `gitignore.rs` is really for: a search tool that can see the agent's own
state is a self-amplifying context bomb.

**The model lied about being done.** Asked to add `--version` to its own CLI, it
wedged a callback between a decorator and its function, broke three tests, never
ran the code, and reported success. Nothing in a 378-line agent can catch that —
termination is `if not reply.tool_calls: return`. **"Done" is the model's
opinion.**

So I built the verifier to catch it. **It didn't work either** — three attempts,
never reached a verdict, and it made outcomes *worse*: 18 turns instead of 6.
[The full post-mortem is in REFERENCE.md](REFERENCE.md#the-loop).

The idea of a verifier is 40 lines. The *reliability* is 202 lines of prompt plus
a planner plus a sandbox — and the reliability is the entire product.

---

## What 1.3M lines buy

Sort grok's code by *why it exists* and it splits cleanly:

- **Bets on model weakness** — goal decomposition, verification, anchored editing,
  compaction. These should shrink as models improve. **Mine says they haven't
  yet.**
- **Bets on human needs** — TUI, settings, sessions, MCP, crash handling. Nothing
  to do with model quality. **They grow forever**, and they're the bigger pile.

Most of a production coding agent is not intelligence, and not even agent design.
It's product.

### The numbers

| miniagent | code | total | | grok-build | lines |
|---|---:|---:|---|---|---:|
| The spine (6 files) | **378** | 683 | | `xai-grok-pager` — the TUI | **414,627** |
| `verify.py` (failed experiment) | 63 | 126 | | `xai-grok-shell` — runtime | 335,843 |
| **All** | **441** | **809** | | `xai-grok-tools` | 112,275 |
| Tests (offline) | 51 | | | `xai-grok-workspace` | 76,730 |

~110 of the spine's 378 code lines are **JSON tool schemas** — data, not logic.
All six tool implementations together are ~50 lines.

---

## What it's for

**Reading it.** 378 lines fits in your head in one sitting, and every non-obvious
decision points at what grok does instead.

**A research bench.** `llm` is injectable, `--model` takes any litellm string.
Hold the harness fixed, swap the model, watch what breaks — that's how every
finding above was produced.

**A library.** `from miniagent.agent import run`. Tools are a plain dict; adding
one is a line.

### What it's not for

**Real work.** Use [Claude Code](https://claude.com/claude-code) or
[grok](https://x.ai/cli). They're better at all of it, because the ~1.3M lines
this repo lacks are the ones that make an agent trustworthy on a *bad* day.

Concretely, don't use it when the codebase is large (no compaction — it crashed
at 142,984 tokens), when you can't check the work yourself (it will tell you it's
done when it isn't), or when the task needs more than ~20 turns.

**That gap is the point of the repo.**

---

## Running it

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
export OPENAI_API_KEY=...
.venv/bin/miniagent "the tests are failing, fix them"
```

| Flag | Effect |
|---|---|
| `--auto` | Skip confirmation before `bash` |
| `--resume` / `--session <id>` | Continue a previous session |
| `--model <str>` | Any litellm model string |
| `--max-turns <n>` | Cap loop iterations (default 25) |
| `--verify` | Second LLM pass checks the work ([it doesn't work](REFERENCE.md#the-loop)) |

```bash
.venv/bin/pytest    # 51 tests, 1.5 seconds, no API key
```

Every test runs against a `FakeLLM` with scripted tool calls — the loop's
correctness has nothing to do with the model, so it's tested without one. Same
move grok makes in its hashline benchmark, which measures an edit format with no
LLM in it at all.

**Five of the 51 are scars** — `grep` eating its own transcript, the model passing
`cwd="~"`, the verifier trying to edit the evidence it was judging, a 200-line
traceback for a bad key, and a test that checked typer's renderer instead of my
code. The other 46 were written from the plan and passed first try.

---

*Reference source: [xai-org/grok-build](https://github.com/xai-org/grok-build)
@ `b189869`, Apache 2.0. Every claim in [REFERENCE.md](REFERENCE.md) points at a
real path in that tree.*
