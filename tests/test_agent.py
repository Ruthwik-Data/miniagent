import json

from miniagent.agent import dispatch, run
from tests.fakes import FakeFunction, FakeLLM, FakeReply, FakeToolCall


def _call(id, name, **args):
    return FakeToolCall(id=id, function=FakeFunction(name=name, arguments=json.dumps(args)))


def test_run_returns_text_when_the_model_asks_for_no_tools():
    fake = FakeLLM([FakeReply(content="nothing to do")])
    text, messages = run("hi", llm=fake)
    assert text == "nothing to do"
    assert messages[-1]["role"] == "assistant"


def test_run_executes_a_tool_then_sends_the_result_back(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello\n")
    fake = FakeLLM([
        FakeReply(tool_calls=[_call("c1", "read_file", path=str(f))]),
        FakeReply(content="the file says hello"),
    ])

    text, messages = run("read it", llm=fake)

    assert text == "the file says hello"
    tool_msgs = [m for m in messages if m["role"] == "tool"]
    assert tool_msgs[0]["tool_call_id"] == "c1"
    assert tool_msgs[0]["content"] == "1\thello"
    # The whole transcript is resent every turn: turn 2 saw turn 1's result.
    assert any(m.get("role") == "tool" for m in fake.calls[1])


def test_run_stops_at_max_turns():
    fake = FakeLLM([
        FakeReply(tool_calls=[_call(f"c{i}", "list_dir", path=".")]) for i in range(5)
    ])
    text, _ = run("loop forever", llm=fake, max_turns=3)
    assert "3 turns" in text


def test_dispatch_returns_tool_errors_as_strings_never_raises():
    result = dispatch(_call("c1", "read_file", path="/nonexistent/nope.txt"))
    assert "error" in result.lower()


def test_dispatch_reports_unknown_tools_to_the_model():
    result = dispatch(_call("c1", "no_such_tool"))
    assert "unknown tool" in result


def test_dispatch_reports_unparseable_arguments_to_the_model():
    bad = FakeToolCall(id="c1", function=FakeFunction(name="read_file", arguments="{not json"))
    result = dispatch(bad)
    assert "error" in result.lower()


def test_dispatch_returns_denial_as_a_tool_result():
    result = dispatch(_call("c1", "bash", command="ls"), input_fn=lambda _: "n")
    assert "denied" in result


def test_run_persists_the_session_when_given_an_id(tmp_path):
    from miniagent import sessions

    fake = FakeLLM([FakeReply(content="done")])
    run("hi", llm=fake, session_id="s1", root=tmp_path)
    assert sessions.load("s1", root=tmp_path)[-1]["content"] == "done"
