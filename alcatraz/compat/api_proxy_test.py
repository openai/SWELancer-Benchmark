import json
from functools import partial

import pytest

from alcatraz.clusters.swarm import SwarmCluster
from alcatraz.compat.api_proxy import (
    AlcatrazAPIProxy,
    MockAsyncChatCompletionFunction,
    _RequestHandler,
)
from alcatraz.compat.api_proxy_types import ChatCompletionRequest
from alcatraz.utils.images import ALCATRAZ_API_PROXY_IMAGE


def test_deserialize() -> None:
    # Test deserializing a bunch of real requests
    test_prompt = json.dumps(
        {
            "messages": [
                {
                    "role": "system",
                    "content": '\nYou are a helpful assistant that retreive API calls and bug locations from a text into json format.\nThe text will consist of two parts:\n1. do we need more context?\n2. where are bug locations?\nExtract API calls from question 1 (leave empty if not exist) and bug locations from question 2 (leave empty if not exist).\n\nThe API calls include:\nsearch_method_in_class(method_name: str, class_name: str)\nsearch_method_in_file(method_name: str, file_path: str)\nsearch_method(method_name: str)\nsearch_class_in_file(self, class_name, file_name: str)\nsearch_class(class_name: str)\nsearch_code_in_file(code_str: str, file_path: str)\nsearch_code(code_str: str)\n\nProvide your answer in JSON structure like this, you should ignore the argument placeholders in api calls.\nFor example, search_code(code_str="str") should be search_code("str")\nsearch_method_in_file("method_name", "path.to.file") should be search_method_in_file("method_name", "path/to/file")\n\n{\n    "API_calls": ["api_call_1(args)", "api_call_2(args)", ...],\n    "bug_locations":[{"file": "path/to/file", "class": "class_name", "method": "method_name"}, {"file": "path/to/file", "class": "class_name", "method": "method_name"} ... ]\n}\n\nNOTE: a bug location should at least has a "class" or "method".\n',
                },
                {"role": "user", "content": 'search_class("VotingClassifier")'},
            ],
            "model": "gpt-4-0125-preview",
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "tools": None,
            "top_p": 1,
        }
    )

    request = ChatCompletionRequest.model_validate_json(test_prompt)
    print(request)


@pytest.mark.asyncio
async def test_mock_request() -> None:
    # Test a mock request to the OpenAI API
    request = json.dumps(
        {
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": {
                "Host": "api.openai.com",
                "User-Agent": "curl/8.5.0",
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Authorization": "Bearer dummy",
                "Content-Length": "213",
            },
            "body": json.dumps(
                {
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello!"},
                    ],
                }
            ),
        }
    )

    print(request)

    api_proxy = _RequestHandler(MockAsyncChatCompletionFunction)
    response = await api_proxy(request)
    print(response)


# Non-ASCII chars used to create issues (11/5/2024)
_TEST_COMPLETION_CONTENT = "DFJKSLDFHSLKDJFSDLKJFद् + ध् + र् + य = द्ध्र्यद् + ध् + र् + य = द्ध्र्यद् + ध् + र् + य = द्ध्र्यद् + ध् + र् + य = द्ध्र्यद् + ध् + र् + य = द्ध्र्य"


@pytest.mark.asyncio
@pytest.mark.swarm
async def test_simple_api_proxy() -> None:
    # Test starting the API proxy
    async with (
        SwarmCluster(
            image=ALCATRAZ_API_PROXY_IMAGE,
            side_images=[ALCATRAZ_API_PROXY_IMAGE],
        ) as cluster,
        AlcatrazAPIProxy(
            cluster, partial(MockAsyncChatCompletionFunction, content=_TEST_COMPLETION_CONTENT)
        ),
    ):
        res = await cluster.send_shell_command("pip install openai")
        assert res["exit_code"] == 0, res

        # Copy the Alcatraz API certificate to Python (used by the openai python library)
        res = await cluster.send_shell_command(
            "cat /usr/local/share/ca-certificates/api_proxy.crt >> /usr/local/lib/python3.9/site-packages/certifi/cacert.pem"
        )
        assert res["exit_code"] == 0, res
        # Test a real request
        res = await cluster.send_shell_command(
            """OPENAI_API_KEY=dummy openai api chat.completions.create --max-tokens 100 -m gpt-4o -g user 'say hi'"""
        )
        assert res["exit_code"] == 0, res
        assert _TEST_COMPLETION_CONTENT in res["result"].decode().strip()

        print("smoketest passed")
