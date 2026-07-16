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


def _fail(message: str) -> None:
    """Print one line and exit. No traceback.

    A bad API key used to dump ~200 lines of litellm internals to explain a
    one-line problem. Nobody should ever see that — which is precisely why
    grok-build has an xai-crash-handler crate. It reads like enterprise
    boilerplate from the outside; it is there because the dependency stack
    under any production agent produces exactly this.
    """
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(1)


@app.command()
def main(
    prompt: str = typer.Argument(..., help="What you want the agent to do."),
    auto: bool = typer.Option(False, "--auto", help="Skip confirmation before bash."),
    resume: bool = typer.Option(False, "--resume", help="Continue the latest session."),
    session: str = typer.Option(None, "--session", help="Resume a specific session id."),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="litellm model string."),
    max_turns: int = typer.Option(25, "--max-turns", help="Cap on loop iterations."),
    verify: bool = typer.Option(False, "--verify", help="Check the work with a second LLM pass before accepting done."),
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

    try:
        text, _ = run(
            prompt,
            messages=messages,
            auto=auto,
            max_turns=max_turns,
            model=model,
            session_id=session_id,
            verify=verify,
        )
    except KeyboardInterrupt:
        # The session was saved after the last completed turn. Say so — the
        # whole point of sessions is that Ctrl-C costs you one turn, not all.
        typer.echo(f"\ninterrupted. resume with: miniagent '<prompt>' --session {session_id}")
        raise typer.Exit(130) from None
    except Exception as e:
        name = type(e).__name__
        if "AuthenticationError" in name:
            _fail("the model provider rejected your API key. Check OPENAI_API_KEY.")
        elif "ContextWindow" in name:
            _fail(
                "the transcript outgrew the model's context window. Start a new "
                "session, or narrow the task. (This repo has no compaction — see "
                "REFERENCE.md.)"
            )
        elif "RateLimit" in name:
            _fail("the model provider rate-limited this request. Wait and retry.")
        elif "NotFoundError" in name or "BadRequestError" in name:
            _fail(f"the provider rejected the request: {e}")
        else:
            _fail(f"{name}: {e}")

    typer.echo(f"\n{text}")
