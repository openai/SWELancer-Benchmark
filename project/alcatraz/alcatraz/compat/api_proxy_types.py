from typing import Awaitable, Callable, Iterable, Literal

from openai.types.chat import ChatCompletion  # response format
from openai.types.chat import completion_create_params
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from openai.types.chat.chat_completion_tool_choice_option_param import (
    ChatCompletionToolChoiceOptionParam,
)
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat_model import ChatModel
from pydantic import BaseModel

# A simple interface for mocking API calls using the OpenAI API proxy.
# Right now, this only supports the ChatCompletions endpoint. We can add more endpoints as needed.
# https://api.openai.com/v1/chat/completions

# We could have used the actual completions API (api/completionsapi/api/methods/create_chat_completion_method.py)
# but this adds a lot of annoying imports and complexity.


class ChatCompletionRequest(BaseModel):
    # A list of messages comprising the conversation so far.
    messages: list[ChatCompletionMessageParam]
    # ID of the model to use.
    model: str | ChatModel
    # Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far.
    frequency_penalty: float | None = None
    # Deprecated in favor of `tool_choice`. Controls which (if any) function is called by the model.
    function_call: completion_create_params.FunctionCall | None = None
    # Deprecated in favor of `tools`. A list of functions the model may generate JSON inputs for.
    functions: Iterable[completion_create_params.Function] | None = None
    # Modify the likelihood of specified tokens appearing in the completion.
    logit_bias: dict[str, int] | None = None
    # Whether to return log probabilities of the output tokens or not.
    logprobs: bool | None = None
    # The maximum number of tokens that can be generated in the chat completion.
    max_tokens: int | None = None
    # How many chat completion choices to generate for each input message.
    n: int | None = None
    # Whether to enable parallel function calling during tool use.
    parallel_tool_calls: bool = False
    # Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far.
    presence_penalty: float | None = None
    # An object specifying the format that the model must output ('text' or 'json_object')
    response_format: completion_create_params.ResponseFormat | None = None
    # This feature is in Beta. If specified, our system will make a best effort to sample deterministically.
    seed: int | None = None
    # Specifies the latency tier to use for processing the request.
    service_tier: Literal["auto", "default"] | None = None
    # Up to 4 sequences where the API will stop generating further tokens.
    stop: str | None | list[str] = None
    # If set, partial message deltas will be sent, like in ChatGPT.
    stream: Literal[False] | None = None
    # Options for streaming response. Only set this when you set `stream: true`.
    stream_options: ChatCompletionStreamOptionsParam | None = None
    # What sampling temperature to use, between 0 and 2.
    temperature: float | None = None
    # Controls which (if any) tool is called by the model.
    tool_choice: ChatCompletionToolChoiceOptionParam | None = None
    # A list of tools the model may call.
    tools: Iterable[ChatCompletionToolParam] | None = None
    # An integer between 0 and 20 specifying the number of most likely tokens to return at each token position.
    top_logprobs: int | None = None
    # An alternative to sampling with temperature, called nucleus sampling.
    top_p: float | None = None
    # A unique identifier representing your end-user, which can help OpenAI to monitor and detect abuse.
    user: str | None = None


AsyncChatCompletionFunction = Callable[[ChatCompletionRequest], Awaitable[ChatCompletion]]


class APIRequest(BaseModel):
    method: str
    path: str
    headers: dict[str, str]
    body: str
