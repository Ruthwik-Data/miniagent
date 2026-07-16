from dataclasses import dataclass


@dataclass
class FakeFunction:
    name: str
    arguments: str  # JSON string, exactly like the real API


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction


@dataclass
class FakeReply:
    content: str | None = None
    tool_calls: list[FakeToolCall] | None = None


class FakeLLM:
    """Scripted stand-in for llm.complete. Zero API spend.

    The shapes above mirror litellm's real response object closely enough
    that agent.py cannot tell the difference: .content, .tool_calls, and
    per-call .id / .function.name / .function.arguments.

    This is grok-build's own eval insight applied here. Their hashline
    benchmark (grok_build_hashline/benchmark.rs, 887 lines) tests an edit
    format with no LLM anywhere in it, by isolating the deterministic
    substrate and measuring that. A FakeLLM is the same move: the loop's
    correctness has nothing to do with the model, so test it without one.
    """

    def __init__(self, replies: list[FakeReply]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, tools, model=None):
        self.calls.append([dict(m) for m in messages])
        return self.replies.pop(0)
