"""typer entrypoint.

grok-build's equivalent surface is xai-grok-pager: 414,627 lines of TUI —
larger than its own 335,843-line agent runtime. One settings modal is 12,471
lines, thirty times this entire repository.

Interface is where production agent code actually goes. Ours is 60 lines,
and that gap is the most surprising number in REFERENCE.md.

One prompt per invocation, not a REPL. Deliberate: an in-process REPL would
hold the transcript in memory and hide the fact that the model is stateless.
Going through disk every time makes the transcript-as-only-memory fact
unavoidable. grok runs a persistent TUI *and* a `-p` headless mode; we take
the headless half.
"""
import typer

from miniagent import sessions
from miniagent.agent import run
from miniagent.llm import DEFAULT_MODEL

app = typer.Typer(add_completion=False, help="The spine of a coding agent.")


@app.command()
def main(
    prompt: str = typer.Argument(..., help="What you want the agent to do."),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation before bash."),
    resume: bool = typer.Option(False, "--resume", help="Continue the latest session."),
    session: str = typer.Option(None, "--session", help="Resume a specific session id."),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="litellm model string."),
    max_turns: int = typer.Option(25, "--max-turns", help="Cap on loop iterations."),
):
    messages = None
    session_id = session

    if session or resume:
        session_id = session or sessions.latest()
        if session_id is None:
            typer.echo("no session to resume; starting a new one")
        else:
            messages = sessions.load(session_id)
            typer.echo(f"resumed {session_id} ({len(messages)} messages)")

    if session_id is None:
        session_id = sessions.new_id()

    text, _ = run(
        prompt,
        messages=messages,
        auto=auto,
        max_turns=max_turns,
        model=model,
        session_id=session_id,
    )
    typer.echo(f"\n{text}")
