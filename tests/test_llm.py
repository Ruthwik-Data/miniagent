from tests.fakes import FakeLLM, FakeReply, FakeToolCall, FakeFunction


def test_fake_llm_returns_scripted_replies_in_order():
    fake = FakeLLM([
        FakeReply(tool_calls=[
            FakeToolCall(id="1", function=FakeFunction(name="bash", arguments='{"command": "ls"}'))
        ]),
        FakeReply(content="done"),
    ])

    first = fake([{"role": "user", "content": "hi"}], tools=[])
    assert first.tool_calls[0].function.name == "bash"
    assert first.content is None

    second = fake([{"role": "user", "content": "hi"}], tools=[])
    assert second.content == "done"
    assert second.tool_calls is None


def test_fake_llm_records_the_messages_it_was_sent():
    fake = FakeLLM([FakeReply(content="ok")])
    fake([{"role": "user", "content": "hi"}], tools=[])
    assert fake.calls[0] == [{"role": "user", "content": "hi"}]
