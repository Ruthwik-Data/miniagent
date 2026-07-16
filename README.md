<h1>miniagent</h1>

**xAI's coding agent is 1,300,000 lines of Rust. Its user interface is bigger
than its agent.**

This is the **309-line spine** underneath — a working coding agent — and a map of
what the other 1,299,691 lines are actually for.

[![license](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![python](https://img.shields.io/badge/python-3.14-blue)](pyproject.toml)
[![code](https://img.shields.io/badge/code-309%20lines-brightgreen)](#the-numbers)
[![tests](https://img.shields.io/badge/tests-41%20offline-brightgreen)](#running-it)

![miniagent finding and fixing a real bug](demos/demo.gif)

*Real run. `calc.py` had a real bug, `pytest` really failed, the agent really
fixed it. Regenerate it: [`vhs demos/demo.tape`](demos/demo.tape).*

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

Everything in every coding agent ever shipped is quality, interface, or
distribution wrapped around those ten lines.

**The model never touches your machine** — it emits JSON requesting a call, your
code runs it. **Termination isn't your decision** — the loop ends when the model
stops asking. **Everything is resent every turn** — the model is stateless, and
the transcript is the only memory there is.

---

## What broke when we ran it

Three findings. **None was the one we predicted.**

#### The bug we shipped on purpose refused to fail

`edit_file` uses naive string matching, deliberately, to rediscover the problem
xAI built [hashline](REFERENCE.md#tools-edit-and-write) to solve — anchored
editing, three candidate schemes, an 887-line benchmark, shipped behind a
server-side flag.

Two attempts. Five sequential edits to the same line, no re-reads. `gpt-4o-mini`
tracked every one. **At this scale, with this model, it did not reproduce.**
→ [`stale-edit-did-not-fire.txt`](demos/stale-edit-did-not-fire.txt)

#### The bug we didn't know about was a feedback loop

`grep` searched `.miniagent/sessions/` — the transcript *being written by the loop
that was searching*. It fed the conversation back into itself: **142,984 tokens
against a 128,000 limit, in six turns.** Not drift. Recursion.

That's what grok's `gitignore.rs` is really for. It reads like politeness about
`node_modules`. It isn't — a search tool that can see the agent's own state is a
self-amplifying context bomb.
→ [`context-window-wall.txt`](demos/context-window-wall.txt)

#### The model lied about being finished

Asked to add a `--version` flag to its own CLI, it wedged a callback between a
decorator and its function, broke three tests, **never ran the code**, and
reported:

> *"I added a `--version` flag... using Typer's callback pattern."*

Nothing in a 309-line agent can catch that. Termination is
`if not reply.tool_calls: return`. **"Done" is the model's opinion.**

That is what grok's 202-line `goal_verifier_prompt.md` exists for — and it is not
a relic for weaker models. It's for this, on a current model, on a ten-line task.
→ [`self-modification.txt`](demos/self-modification.txt)

---

## The numbers

| miniagent | |
|---|---:|
| **Code** | **309** |
| Annotation (docstrings explaining grok) | 260 |
| Tests (all offline) | 41 |

~110 of those 309 code lines are **JSON tool schemas** — data describing tools to
the model, not logic. All six tool implementations together are ~50 lines.

| grok-build | |
|---|---:|
| `xai-grok-pager` — the TUI | **414,627** |
| `xai-grok-shell` — agent runtime | 335,843 |
| `xai-grok-tools` | 112,275 |
| `xai-grok-workspace` | 76,730 |

**Their interface is larger than their agent.** Most of a production coding agent
is not intelligence, and not even agent design.

---

## What it deliberately doesn't do

No MCP. No subagents. No TUI. No streaming. No scheduling. No memory system. No
slash commands. No compaction. No sandbox. grok-build has every one.

**[REFERENCE.md](REFERENCE.md) says why none of them is the spine — that list is
the finding, not the backlog.** Sort grok's 1.3M lines by *why they exist* and
they split in two:

- **Bets on model weakness** — goal decomposition, verification, anchored editing,
  compaction. Should shrink as models improve. *They haven't yet* — see above.
- **Bets on human needs** — TUI, settings, sessions, MCP, crash handling. Nothing
  to do with model quality. **They grow forever**, and they're the bigger pile.

---

## Running it

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
export OPENAI_API_KEY=...
.venv/bin/miniagent "the tests are failing, fix them"
```

Any litellm model: `--model claude-sonnet-5`, `--model openrouter/...`

| Flag | Effect |
|---|---|
| `--auto` | Skip confirmation before `bash` |
| `--resume` | Continue the latest session here |
| `--session <id>` | Resume a specific session |
| `--model <str>` | Any litellm model string |
| `--max-turns <n>` | Cap loop iterations (default 25) |

```bash
.venv/bin/pytest    # 41 tests, zero API calls
```

Every test runs against a `FakeLLM` with scripted tool calls. The loop's
correctness has nothing to do with the model, so it's tested without one — the
same move grok-build makes in its hashline benchmark, which measures an edit
format with no LLM in it at all.

---

*Reference source: [xai-org/grok-build](https://github.com/xai-org/grok-build)
@ `b189869`, Apache 2.0. Every claim in [REFERENCE.md](REFERENCE.md) points at a
real path in that tree.*
