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
