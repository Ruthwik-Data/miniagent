"""The loop. This is what a coding agent IS.

Send the transcript and the tool schemas. The model replies either with text
(it's done) or with tool calls (it wants something run). Execute them, append
the results, resend everything, repeat.

That's it. That's the mechanism. grok-build wraps this same cycle in ~1.3M
lines: xai-grok-shell (335,843) is the runtime, xai-grok-pager (414,627) is
the TUI. The loop itself is about ten lines. Everything else is quality,
interface, and distribution.

Three things this file makes obvious that nothing else does:

  1. The model never touches your machine. It emits JSON requesting a call.
     dispatch() runs it. The agency lives in the loop, not the model.
  2. Termination is not a decision you make. The loop ends when the model
     stops asking for tools. There is no completion detector, no "done"
     signal, no goal check.
  3. Everything is resent every turn. Turn 10 resends turns 1-9. The model
     is stateless; the transcript is the only memory there is.
"""
import json

from miniagent import sessions
from miniagent.llm import complete
from miniagent.safety import confirm
from miniagent.tools import SCHEMAS, TOOLS

SYSTEM_PROMPT = """You are a coding agent working in the user's repository.

Use the tools to read, search, and edit files, and to run commands. Prefer
the dedicated file tools over bash for reading and editing.

Weigh each action by how easily it can be undone and how far its effects
reach. Local, reversible work such as editing files and running tests is
fine to do freely. Be careful with anything destructive or hard to reverse.

When the task is complete, reply with a short plain-text summary and no
tool calls. That is how you signal you are done."""


def _reply_to_message(reply) -> dict:
    """Convert an LLM reply into a transcript message.

    Works for both litellm's real response and tests/fakes.FakeReply, which
    is why the whole loop is testable with zero API spend.
    """
    message = {"role": "assistant", "content": reply.content}
    if reply.tool_calls:
        message["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments},
            }
            for c in reply.tool_calls
        ]
    return message


def dispatch(call, auto: bool = False, input_fn=input) -> str:
    """Execute one tool call. Always returns a string, never raises.

    This is the thing people get wrong first: treating the LLM as a caller
    that must be protected from errors, when it is a participant that reads
    them and adapts. A missing file is not a crash — it is a message.

    edit_file returning "no match found for that string" IS the retry
    mechanism. There is no retry code in this repo, because the model reads
    the failure and tries different text. Every `return f"error: ..."` below
    is a sentence addressed to the model.
    """
    name = call.function.name
    try:
        args = json.loads(call.function.arguments)
    except json.JSONDecodeError as e:
        return f"error: could not parse arguments as JSON: {e}"

    fn = TOOLS.get(name)
    if fn is None:
        return f"error: unknown tool {name}"

    if not confirm(name, args, auto=auto, input_fn=input_fn):
        return "user denied this action"

    try:
        return fn(**args)
    except Exception as e:
        return f"error: {type(e).__name__}: {e}"


def run(
    prompt: str,
    messages: list[dict] | None = None,
    auto: bool = False,
    max_turns: int = 25,
    llm=complete,
    model: str | None = None,
    session_id: str | None = None,
    root=None,
    input_fn=input,
    verify: bool = False,
    max_verifications: int = 2,
) -> tuple[str, list[dict]]:
    """Run the agent until the model stops asking for tools.

    max_turns caps runaway iteration and spend. It is a real production
    concern, not a toy guard: without it, a model that keeps requesting
    tools bills you until you notice. grok's equivalent surface is effort
    levels and background task limits.

    verify=True adds a second LLM pass that checks the work before accepting
    "done" — see verify.py. Opt-in, because the un-verified failure is a
    baseline worth keeping reproducible.
    """
    from miniagent.verify import verify as run_verifier  # late: avoids a cycle

    messages = messages or [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": prompt})
    verifications = 0

    for _turn in range(max_turns):
        kwargs = {"model": model} if model else {}
        reply = llm(messages, tools=SCHEMAS, **kwargs)
        messages.append(_reply_to_message(reply))

        # No tool calls means the model *considers* the task finished.
        if not reply.tool_calls:
            if verify and verifications < max_verifications:
                verifications += 1
                print("  — verifying —")
                complaint = run_verifier(
                    task=prompt,
                    report=reply.content or "",
                    llm=llm,
                    model=model,
                    auto=auto,
                    input_fn=input_fn,
                )
                if complaint is not None:
                    print(f"  ✗ {complaint.splitlines()[0][:90]}")
                    # Hand the verdict back as a user turn and keep going.
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "A verifier checked your work against the actual "
                                f"repository and rejected it:\n\n{complaint}\n\n"
                                "Fix it, then confirm by running the relevant "
                                "checks yourself."
                            ),
                        }
                    )
                    if session_id:
                        sessions.save(session_id, messages, root=root)
                    continue
                print("  ✓ verified")

            if session_id:
                sessions.save(session_id, messages, root=root)
            return reply.content, messages

        for call in reply.tool_calls:
            result = dispatch(call, auto=auto, input_fn=input_fn)
            preview = result.splitlines()[0][:80] if result else ""
            print(f"  {call.function.name} → {preview}")
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

        # Save after every turn so a crash or Ctrl-C loses at most one.
        if session_id:
            sessions.save(session_id, messages, root=root)

    return f"stopped after {max_turns} turns without finishing", messages
