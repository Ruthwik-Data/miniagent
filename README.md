# miniagent

The spine of a coding agent: **309 lines of Python** that read, edit, and run
code in your repo — annotated against
[xai-org/grok-build](https://github.com/xai-org/grok-build), xAI's production
coding agent, which does the same job in **~1,300,000 lines of Rust**.

The question this repo answers: **what do the other 1,299,691 lines buy?**

That answer is **[REFERENCE.md](REFERENCE.md)**. The code is the exhibit.

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

That's it. Everything else in every coding agent ever shipped is quality,
interface, or distribution wrapped around this.

Three things that loop makes obvious, and reading about agents does not:

1. **The model never touches your machine.** It emits JSON saying *"I'd like to
   call `bash` with `pytest`."* Your code runs it. The agency lives in the loop,
   not the model.
2. **Termination isn't your decision.** The loop ends when the model stops asking
   for tools. There's no completion detector, no "done" signal.
3. **Everything is resent, every turn.** Turn 10 resends turns 1–9. The model is
   stateless — the transcript is the only memory there is, which is why
   `sessions.py` is `json.dump(messages)` and why the context limit is the
   binding constraint on how long an agent can work.

## The numbers

| | Lines |
|---|---|
| **Code** | **309** |
| Annotation (docstrings explaining grok) | 260 |
| Total | 569 |
| Tests | 37, all offline |

Of the 309 code lines, ~110 are **JSON tool schemas** — data describing tools to
the model, not logic. All six tool implementations together are ~50 lines. The
agent's actual machinery is under 200 lines.

For comparison, from grok-build:

| Crate | Lines |
|---|---|
| `xai-grok-pager` (the TUI) | **414,627** |
| `xai-grok-shell` (agent runtime) | 335,843 |
| `xai-grok-tools` | 112,275 |
| `xai-grok-workspace` | 76,730 |

**Their interface is larger than their agent.** That's the first finding, and
it's the one that reframes everything else.

## Install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
export OPENAI_API_KEY=...
.venv/bin/miniagent "the tests are failing, fix them"
```

Any litellm model string works: `--model claude-sonnet-5`, `--model
openrouter/...`.

## Flags

| Flag | Effect |
|---|---|
| `--auto` | Skip confirmation before `bash` |
| `--resume` | Continue the latest session in this directory |
| `--session <id>` | Resume a specific session |
| `--model <str>` | Any litellm model string |
| `--max-turns <n>` | Cap loop iterations (default 25) |

## What it deliberately doesn't do

No MCP. No subagents. No TUI. No streaming. No scheduling. No memory system. No
slash commands. No compaction. No sandbox. grok-build has all of them.

[REFERENCE.md](REFERENCE.md) says why each one isn't the spine. **That list is
the finding, not the backlog** — and it sorts into two piles: features that bet
on *model weakness* (which shrink as models improve) and features that serve
*human needs* (which grow forever).

`edit_file` uses **naive string matching on purpose**. It breaks when the model
targets text it misremembers — which is exactly the problem xAI built hashline to
solve, and which they're still measuring behind a server-side flag.

## Tests

```bash
.venv/bin/pytest    # 37 tests, zero API calls
```

Every test runs against a `FakeLLM` with scripted tool calls. The loop's
correctness has nothing to do with the model, so it's tested without one — the
same move grok-build makes in its hashline benchmark, which measures an edit
format with no LLM in it at all.

## License

Apache 2.0, mirroring grok-build.
