import json

from miniagent.verify import verify
from tests.fakes import FakeFunction, FakeLLM, FakeReply, FakeToolCall


def _call(id, name, **args):
    return FakeToolCall(id=id, function=FakeFunction(name=name, arguments=json.dumps(args)))


def test_verify_returns_none_when_the_verdict_is_done():
    fake = FakeLLM([FakeReply(content="DONE: the flag works and tests pass")])
    assert verify("add a flag", "I added the flag", llm=fake) is None


def test_verify_returns_the_complaint_when_not_done():
    fake = FakeLLM([FakeReply(content="NOT DONE: three tests fail, main is undecorated")])
    result = verify("add a flag", "I added the flag", llm=fake)
    assert result is not None
    assert "three tests fail" in result


def test_verify_checks_the_repo_with_tools_before_ruling(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello\n")
    fake = FakeLLM([
        FakeReply(tool_calls=[_call("v1", "read_file", path=str(f))]),
        FakeReply(content="DONE: verified against the file"),
    ])

    assert verify("write hello", "wrote it", llm=fake) is None
    # It read the file before ruling — the verdict is grounded, not echoed.
    assert any(m.get("role") == "tool" for m in fake.calls[1])


def test_verify_does_not_see_the_agents_transcript():
    # The verifier gets the task and the claim, never the reasoning that
    # produced them. A judge that reads the defendant's diary is not a judge.
    fake = FakeLLM([FakeReply(content="DONE: fine")])
    verify("the task", "the report", llm=fake)
    sent = json.dumps(fake.calls[0])
    assert "the task" in sent
    assert "the report" in sent
    assert "SYSTEM_PROMPT_OF_THE_AGENT" not in sent


def test_verify_treats_an_ambiguous_verdict_as_not_done():
    fake = FakeLLM([FakeReply(content="looks fine to me probably")])
    result = verify("add a flag", "added", llm=fake)
    assert result is not None


def test_verify_gives_up_rather_than_looping_forever():
    fake = FakeLLM([
        FakeReply(tool_calls=[_call(f"v{i}", "list_dir", path=".")]) for i in range(5)
    ])
    result = verify("x", "y", llm=fake, max_turns=3)
    assert "verdict" in result.lower()


def test_verifier_cannot_edit_the_evidence():
    # The first version had the full toolset and immediately tried edit_file —
    # a judge fixing the evidence it was sent to inspect.
    from miniagent.verify import VERIFIER_SCHEMAS

    names = {s["function"]["name"] for s in VERIFIER_SCHEMAS}
    assert "edit_file" not in names
    assert "write" not in names
    assert {"read_file", "grep", "list_dir"} <= names
