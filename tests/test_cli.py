from typer.testing import CliRunner

from miniagent.cli import app

runner = CliRunner()


def test_cli_help_lists_the_flags():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--auto" in result.stdout
    assert "--resume" in result.stdout


def test_cli_runs_a_prompt_and_prints_the_result(monkeypatch):
    monkeypatch.setattr("miniagent.cli.run", lambda prompt, **kw: ("all done", []))
    result = runner.invoke(app, ["fix the tests"])
    assert result.exit_code == 0
    assert "all done" in result.stdout


def test_cli_resume_loads_the_latest_session(monkeypatch, tmp_path):
    from miniagent import sessions

    prior = [{"role": "system", "content": "s"}, {"role": "user", "content": "earlier"}]
    sessions.save("s1", prior, root=tmp_path)
    monkeypatch.chdir(tmp_path)

    seen = {}

    def fake_run(prompt, **kw):
        seen["messages"] = kw.get("messages")
        return ("ok", [])

    monkeypatch.setattr("miniagent.cli.run", fake_run)
    result = runner.invoke(app, ["carry on", "--resume"])
    assert result.exit_code == 0
    assert seen["messages"][1]["content"] == "earlier"


def test_cli_prints_one_line_for_a_bad_api_key(monkeypatch):
    # Was: ~200 lines of litellm traceback to explain a one-line problem.
    class AuthenticationError(Exception):
        pass

    def boom(prompt, **kw):
        raise AuthenticationError("Incorrect API key provided: sk-proj-xxx")

    monkeypatch.setattr("miniagent.cli.run", boom)
    result = runner.invoke(app, ["do a thing"])

    assert result.exit_code == 1
    assert len(result.output.strip().splitlines()) <= 2
    assert "API key" in result.output


def test_cli_explains_the_context_window_wall(monkeypatch):
    class ContextWindowExceededError(Exception):
        pass

    def boom(prompt, **kw):
        raise ContextWindowExceededError("128000 tokens")

    monkeypatch.setattr("miniagent.cli.run", boom)
    result = runner.invoke(app, ["do a thing"])

    assert result.exit_code == 1
    assert "context window" in result.output
    assert "compaction" in result.output
