from miniagent.safety import confirm, RISKY
from miniagent.tools import bash


def _never_called(_prompt):
    raise AssertionError("should not have prompted")


def test_confirm_allows_safe_tools_without_asking():
    assert confirm("read_file", {"path": "x"}, input_fn=_never_called) is True


def test_confirm_asks_before_bash_and_respects_yes():
    assert confirm("bash", {"command": "ls"}, input_fn=lambda _: "y") is True


def test_confirm_denies_by_default_on_anything_else():
    assert confirm("bash", {"command": "rm -rf /"}, input_fn=lambda _: "") is False
    assert confirm("bash", {"command": "rm -rf /"}, input_fn=lambda _: "n") is False


def test_auto_bypasses_the_gate_without_asking():
    assert confirm("bash", {"command": "ls"}, auto=True, input_fn=_never_called) is True


def test_bash_is_the_only_risky_tool():
    assert RISKY == {"bash"}


def test_bash_returns_exit_code_and_output(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    out = bash("ls", cwd=str(tmp_path))
    assert out.startswith("exit 0")
    assert "a.txt" in out


def test_bash_returns_stderr_and_nonzero_exit_as_a_string(tmp_path):
    out = bash("exit 3", cwd=str(tmp_path))
    assert out.startswith("exit 3")
