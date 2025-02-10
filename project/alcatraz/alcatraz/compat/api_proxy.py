import asyncio
import functools
import json
import logging
import time
import uuid
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Any, Self, cast

import structlog.stdlib
import tenacity
from openai import AsyncOpenAI
from openai._types import NOT_GIVEN
from openai.types.chat import ChatCompletion  # response format
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel

from alcatraz.clusters.local import BaseAlcatrazCluster
from alcatraz.compat.api_proxy_types import (
    APIRequest,
    AsyncChatCompletionFunction,
    ChatCompletionRequest,
)

logger = structlog.stdlib.get_logger(component=__name__)


# A mock completion function that samples a few tokens, just for testing.
async def MockAsyncChatCompletionFunction(
    request: ChatCompletionRequest, content: str = "This is a dummy response from a fake agent!"
) -> ChatCompletion:
    await asyncio.sleep(0.2)
    return ChatCompletion(
        id=f"chatcmpl-{uuid.uuid4()}",
        object="chat.completion",
        created=int(time.time()),
        model=request.model,
        system_fingerprint="fp_44709d6fcb",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=content,
                ),
                finish_reason="stop",
            ),
        ],
        usage=CompletionUsage(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
        ),
    )


@functools.cache
def _openai_client() -> AsyncOpenAI:
    return AsyncOpenAI()


# A proxy using the production OpenAI API.
async def OpenAIAsyncChatCompletionFunction(request: ChatCompletionRequest) -> ChatCompletion:
    return await _openai_client().chat.completions.create(
        model=request.model,
        messages=request.messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stop=request.stop,
        n=request.n,
        user=request.user or NOT_GIVEN,
        parallel_tool_calls=request.parallel_tool_calls or NOT_GIVEN,
        tool_choice=request.tool_choice or NOT_GIVEN,
        tools=request.tools or NOT_GIVEN,
        response_format=request.response_format or NOT_GIVEN,
        seed=request.seed,
        service_tier=request.service_tier,
        top_logprobs=request.top_logprobs,
        presence_penalty=request.presence_penalty,
    )


class _APIProxyResponse(BaseModel):
    # Use a quick pydantic model here to provide static + runtime type validation

    status_code: int
    headers: dict[str, str]
    body: str

    @staticmethod
    def make(status_code: int, body: dict[str, Any]) -> "_APIProxyResponse":
        text = json.dumps(body)
        return _APIProxyResponse(
            status_code=status_code,
            headers={
                "Content-Type": "application/json",
                # content length is defined as the BYTE SEQUENCE length, not the character length. Very important.
                # Note that aiohttp on the api_proxy server side defaults to utf-8, matching this configuration:
                # https://docs.aiohttp.org/en/stable/web_reference.html
                # If you use Unicode length instead of bytes length here, the OpenAI client will raise a JSONDecodeError
                # because the content length will be wrong.
                "Content-Length": str(len(text.encode("utf-8"))),
            },
            body=text,
        )


class _RequestHandler:
    """
    Handles the JSON -> AsyncChatCompletionFn -> JSON translation. Essentially, it calls an
    AsyncChatCompletionFunction with a JSON request and returns a JSON response.
    """

    def __init__(self, chat_completion_function: AsyncChatCompletionFunction):
        self.chat_completion_function = chat_completion_function

    # Retry completions in case of failure. Do not crash
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=tenacity.before_sleep_log(
            cast(logging.Logger, logger), logging.WARNING, exc_info=True
        ),
        retry=tenacity.retry_if_exception_type(BaseException),
    )
    async def _chat_completion_retry(self, chat_request: ChatCompletionRequest) -> ChatCompletion:
        return await self.chat_completion_function(chat_request)

    async def __call__(self, request_str: str) -> str:
        # deserialize the request
        api_request = APIRequest.model_validate_json(request_str)

        # Only chat completions is supported.
        error_str = ""
        if api_request.path != "/v1/chat/completions":
            error_str += f"Unsupported path {api_request.path}"
        if api_request.method != "POST":
            error_str += f"Unsupported method {api_request.method}"
        if error_str:
            logger.warning("API proxy received an invalid request:\n" + request_str)
            return _APIProxyResponse.make(
                status_code=400,
                body={"error": error_str},
            ).model_dump_json()

        assert api_request.path == "/v1/chat/completions", f"Unsupported path {api_request.path}"
        assert api_request.method == "POST", f"Unsupported method {api_request.method}"
        chat_request = ChatCompletionRequest.model_validate(json.loads(api_request.body))
        try:
            body = await self._chat_completion_retry(chat_request)
        except Exception as e:
            raise RuntimeError(
                "ChatCompletion function failed to process request:\n\n"
                + api_request.model_dump_json()
            ) from e

        return _APIProxyResponse.make(
            status_code=200,
            body=body.model_dump(),
        ).model_dump_json()


class AlcatrazAPIProxy:
    """
    Runs on the driver and wraps an Alcatraz cluster to provide an API proxy for OpenAI API calls.
    """

    def __init__(
        self,
        cluster: BaseAlcatrazCluster,
        proxy_fn: AsyncChatCompletionFunction,
        api_proxy_container_id: int = 1,
    ):
        self.cluster = cluster
        self.proxy_fn = proxy_fn
        self.api_proxy_container_id = api_proxy_container_id
        self.exit_stack = AsyncExitStack()
        self._should_stop = False

    @functools.cached_property
    def _request_handler(self) -> _RequestHandler:
        return _RequestHandler(self.proxy_fn)

    async def __aenter__(self) -> Self:
        await self.exit_stack.__aenter__()
        await self._setup()
        return self

    async def _setup(self) -> None:
        container_names = await self.cluster.fetch_container_names()
        assert (
            len(container_names) > self.api_proxy_container_id
        ), "Invalid container ID for API proxy. Make sure you are running an API proxy (alcatrazswarmcontainers.azurecr.io/alcatraz_api_proxy:latest) as a side container"

        api_proxy_hostname = container_names[self.api_proxy_container_id]
        assert api_proxy_hostname

        # Override api.openai.com in /etc/hosts
        command = (
            "getent hosts "
            + api_proxy_hostname
            + " | awk 'NR==1{print $1}' | xargs -I{} sh -c 'echo \"{} api.openai.com\" >> /etc/hosts'"
        )

        result = await self.cluster.send_shell_command(command)
        assert result["exit_code"] == 0, "error: " + result["result"].decode("utf-8")

        # trust the certificate
        # WARN this is specific to Debian/Ubuntu images!
        result = await self.cluster.send_shell_command("cat /etc/os-release")
        os_info = result["result"].decode("utf-8")

        if "ID=debian" in os_info or "ID=ubuntu" in os_info:
            logger.info("System is Debian/Ubuntu based.")
        else:
            raise RuntimeError(
                "System is not Debian/Ubuntu based. This setup is specific to Debian/Ubuntu images."
            )

        logger.info("Trusting the certificate...")
        certificate = await self.cluster.download(
            "/root/cert.pem", container_id=self.api_proxy_container_id
        )

        # Check if update-ca-certificates is available
        result = await self.cluster.send_shell_command("command -v update-ca-certificates")
        if result["exit_code"] != 0:
            logger.info("update-ca-certificates command not found. Attempting to install it...")
            # Update package list and install ca-certificates
            result = await self.cluster.send_shell_command(
                "apt-get update && apt-get install -y ca-certificates"
            )
            assert result["exit_code"] == 0, "Failed to install ca-certificates: " + result[
                "result"
            ].decode("utf-8")
        else:
            logger.info("update-ca-certificates command is available.")

        await self.cluster.upload(
            certificate,
            "/usr/local/share/ca-certificates/api_proxy.crt",
        )
        result = await self.cluster.send_shell_command("update-ca-certificates")
        assert result["exit_code"] == 0, "error: " + result["result"].decode("utf-8")

        # TODO we also need to update the `certifi` certificates used by the OpenAI Python client,
        # which differ from the system certificates.

        # This can be done using something like
        # import certifi
        # print(certifi.where())  # This will output the path to the cacert.pem file used by certifi.
        # !cat /usr/local/share/ca-certificates/api_proxy.crt >> {certify.where()}

        # For now I'm doing this in the respective agent script, but this is not ideal. Need to fix
        # this for the Jupyter kernel but haven't tested it yet.

        # Start the background task
        task = asyncio.create_task(self._poll_and_write_response())

        def stop_polling_task() -> None:
            self._should_stop = True
            task.cancel()

        self.exit_stack.callback(stop_polling_task)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.exit_stack.__aexit__(exc_type, exc_value, exc_tb)

    @tenacity.retry(
        wait=tenacity.wait_random_exponential(multiplier=1, min=2, max=30),
        retry=tenacity.retry_if_exception_type(Exception),
        retry_error_callback=lambda retry_state: (
            retry_state.outcome.result()
            if isinstance(retry_state.outcome.exception(), asyncio.CancelledError)
            else None
        ),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING, exc_info=True),
    )
    async def _process_request(self, request: str) -> None:
        request_data = (
            await self.cluster.download(request, container_id=self.api_proxy_container_id)
        ).decode("utf-8")
        logger.debug(f"Processing request: {request_data}")
        response = await self._request_handler(request_data)
        logger.debug(f"Generated response: {response}")
        partial_response_path = request.replace("/root/request", "/root/response").replace(
            ".json", ".json.tmp"
        )
        response_path = request.replace("/root/request", "/root/response")

        # Uploading isn't atomic, so we do an upload -> atomic rename on the remote side. This prevents
        # partially uploaded files from being picked up by the API proxy client, which happens a small
        # percentage of the time.
        await self.cluster.upload(
            response.encode("utf-8"),
            partial_response_path,
            container_id=self.api_proxy_container_id,
            chown=False,
        )
        logger.info("Uploaded partial response to %s", partial_response_path)
        # mv is atomic if the source and destination are on the same filesystem
        await self.cluster.send_shell_command(
            f"mv {partial_response_path} {response_path}",
            container_id=self.api_proxy_container_id,
        )
        logger.info("Completed response at %s", response_path)
        logger.info("Response at %s: %s", response_path, response)

    @tenacity.retry(
        # Exponential backoff to avoid overloading if it crash loops
        wait=tenacity.wait_random_exponential(multiplier=1, min=2, max=30),
        retry=tenacity.retry_if_not_exception_type(
            # This usually means the Alcatraz container has crashed (no more heartbeat). On all other exceptions
            # we prefer to restart
            AssertionError
        ),
        before_sleep=tenacity.before_sleep_log(
            cast(logging.Logger, logger), logging.WARNING, exc_info=True
        ),
    )
    async def _poll_and_write_response(self) -> None:
        """
        A function that polls for new requests and writes responses to container 0 on a cluster,
        given an API proxy running on container `container_id`.

        This function retries indefinitely in case of errors, and is intended to be used as a background task.
        When the API proxy exits, it will automatically stop.
        """

        logger.info("Starting Alcatraz API proxy request loop")
        started_requests: set[str] = set()
        idx = 0

        try:
            async with asyncio.TaskGroup() as processing_tasks:
                while not self._should_stop:
                    # Cat logs for debugging every N seconds
                    if idx % 100 == 0:
                        try:
                            logger.info("Container logs:")
                            logs = await self.cluster.fetch_container_logs(
                                container_id=self.api_proxy_container_id, tail=200
                            )
                            for line in logs.decode("utf-8", errors="ignore").split("\n"):
                                logger.info(line)
                        except Exception:
                            logger.error("Failed to fetch container logs. Will try again in 100s.")

                    # Poll for requests
                    result = await self.cluster.send_shell_command(
                        "find /root/request -maxdepth 1 -type f -name '*.json'",
                        container_id=self.api_proxy_container_id,
                    )
                    output = result["result"].decode("utf-8")
                    if result["exit_code"] != 0:
                        raise RuntimeError("Failed to list requests: " + output)

                    if output:
                        # Get the list of request files
                        requests = [fname.strip() for fname in output.split("\n") if fname.strip()]

                        # Filter out requests that are already being processed
                        new_requests = [req for req in requests if req not in started_requests]

                        if len(new_requests) > 0:
                            logger.info(
                                f"Found {len(new_requests)} new OpenAI API call(s) to proxy."
                            )

                        for request in new_requests:
                            logger.info(f"Found new request: {request}")
                            started_requests.add(request)
                            processing_tasks.create_task(
                                self._process_request(request), name=request
                            )

                    # Sleep for a short duration before polling again
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.error("Polling task was cancelled, retrying...")
            await self._poll_and_write_response()

    @classmethod
    async def check_curl_api(cls, cluster: BaseAlcatrazCluster) -> None:
        result = await cluster.send_shell_command("command -v curl")
        if result["exit_code"] != 0:
            logger.info("curl command not found. Attempting to install it...")
            result = await cluster.send_shell_command("apt-get update && apt-get install -y curl")
            assert result["exit_code"] == 0, "Failed to install curl: " + result["result"].decode(
                "utf-8"
            )
        else:
            logger.info("curl command is available.")

        command = """curl -sS https://api.openai.com/v1/chat/completions \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer dummy" \
            -d '{
                "model": "gpt-4o",
                "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": "Hello!"
                }
                ]
            }'
            """.strip()

        result = await cluster.send_shell_command(command)
        assert result["exit_code"] == 0, "error with curl OpenAI API: " + result["result"].decode(
            "utf-8"
        )
