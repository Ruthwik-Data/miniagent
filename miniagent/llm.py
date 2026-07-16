"""litellm wrapper.

grok-build's equivalent is spread across xai-grok-sampler, xai-grok-models,
and xai-grok-sampling-types — conversation.rs alone is 9,481 lines. Ours is
one function, because provider abstraction is litellm's job, not an agent
concept. Swapping models is a string.
"""
import litellm

# litellm prints its own "Give Feedback / Get Help" banner and debug chatter on
# every error. The user's problem is a bad API key; the framework's issue
# tracker is not the answer to it.
litellm.suppress_debug_info = True

DEFAULT_MODEL = "gpt-4o-mini"


def complete(messages: list[dict], tools: list[dict], model: str = DEFAULT_MODEL):
    """Send the whole transcript plus tool schemas. Return the reply message.

    The model is stateless. Every call resends everything — system prompt,
    every message, every tool call, every result. There is no server-side
    conversation to append to. This function is the only place the agent
    touches the network.

    Returns an object with .content (str | None) and .tool_calls
    (list | None). Tool calls carry .id and .function.{name, arguments},
    where arguments is a JSON *string*.
    """
    resp = litellm.completion(
        model=model,
        messages=messages,
        tools=tools,
        temperature=0,
    )
    return resp.choices[0].message
