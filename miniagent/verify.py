"""The verifier: a second LLM pass that checks the agent's homework.

Why this exists: the agent lies about being finished.

Asked to add a --version flag to its own CLI, gpt-4o-mini wedged a callback
between a decorator and its function, broke three tests, never ran the code,
and reported "I added a --version flag... using Typer's callback pattern."
(demos/self-modification.txt). Nothing in agent.py could catch that, because
the loop's whole termination rule is `if not reply.tool_calls: return`.
Done is the model's opinion.

grok-build's answer is a 202-line goal_verifier_prompt.md plus a planner, a
strategist, and a summarizer — four LLM roles around one task. This is that
idea at 1/5th the size, testing whether the shape works.

Three design decisions carry the whole thing, and the third was learned the
hard way:

1. **The verifier gets tools.** A judge that only reads the claim is a rubber
   stamp. This one runs the code.
2. **The verifier does NOT get the agent's transcript.** It sees the task and
   the claim, never the reasoning that produced them. A judge that reads the
   defendant's diary inherits the defendant's mistakes — if the agent
   convinced itself the edit was fine, its transcript is the most persuasive
   document arguing exactly that.
3. **The verifier's tools are READ-ONLY.** The first version handed it the
   full toolset, and it immediately tried to `edit_file` — a judge fixing the
   evidence it was sent to inspect. A verifier that can write cannot produce
   a trustworthy verdict about the state it just changed.

Note the hole we keep on purpose: `bash` stays, because running the code is
the only real check, and `bash` can obviously write (`sed -i`, `>`). The
read-only property here is a *strong default*, not a sandbox. Enforcing it
properly needs what grok has: xai-grok-sandbox. That is the honest boundary
between a 40-line verifier and a 202-line prompt with a sandbox under it.

Opt-in via --verify, so the un-verified failure stays reproducible as a
baseline. See REFERENCE.md.
"""
from miniagent.tools import SCHEMAS

# A judge may look, search, and run. It may not edit the evidence.
READ_ONLY_TOOLS = {"read_file", "list_dir", "grep", "bash"}
VERIFIER_SCHEMAS = [s for s in SCHEMAS if s["function"]["name"] in READ_ONLY_TOOLS]

VERIFIER_PROMPT = """You are verifying whether a coding agent actually completed its task.

You are given the task it was set and the report it produced. The report is a
claim, not evidence. Agents routinely report success on work that does not
compile, does not run, or does not do what was asked.

Use the tools to check the real state of the repository. Read the files that were
supposedly changed. Run the code. Verify the claim against reality.

How to run things:
- Python and pytest live in a virtualenv. Use `.venv/bin/python` and
  `.venv/bin/pytest`, not bare `python`/`pytest` — bare names are not on PATH
  and will return exit 127.
- If a command fails with 127, the binary is not where you looked. Find it
  (`list_dir` on `.venv/bin`) rather than retrying the same command.
- Importing the changed module is often the fastest real check:
  `.venv/bin/python -c "import the_module"` catches syntax errors immediately.

You cannot edit files. You have read_file, list_dir, grep, and bash. Your job is
to judge, not to fix.

Be efficient. You have a limited number of turns. Check the specific claim, not
the whole repository.

Then reply with exactly one of:

DONE: <one sentence naming what you actually ran or read>
NOT DONE: <what is concretely wrong, and the next step to fix it>

Any reply that does not begin with DONE: or NOT DONE: is treated as NOT DONE.
If you did not verify anything with the tools, you cannot say DONE."""


def verify(
    task: str,
    report: str,
    llm,
    model: str | None = None,
    auto: bool = True,
    input_fn=input,
    max_turns: int = 10,
) -> str | None:
    """Check whether `task` was really done. Returns None if verified, else why not.

    Runs its own small loop with a fresh context: system prompt, the task, the
    claim. Nothing else.
    """
    from miniagent.agent import _reply_to_message, dispatch  # late: avoids a cycle

    messages = [
        {"role": "system", "content": VERIFIER_PROMPT},
        {
            "role": "user",
            "content": (
                f"<task>\n{task}\n</task>\n\n"
                f"<agent_report>\n{report}\n</agent_report>\n\n"
                "Check the repository. Do not trust the report."
            ),
        },
    ]

    for _ in range(max_turns):
        kwargs = {"model": model} if model else {}
        reply = llm(messages, tools=VERIFIER_SCHEMAS, **kwargs)
        messages.append(_reply_to_message(reply))

        if not reply.tool_calls:
            verdict = (reply.content or "").strip()
            if verdict.upper().startswith("DONE"):
                return None
            # NOT DONE, or anything ambiguous. Ambiguity is not approval.
            return verdict or "verifier returned an empty verdict"

        for call in reply.tool_calls:
            result = dispatch(call, auto=auto, input_fn=input_fn)
            print(f"    verify: {call.function.name} → {result.splitlines()[0][:60] if result else ''}")
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    return f"verifier used all {max_turns} turns without reaching a verdict"
