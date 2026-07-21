from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import AuthenticationError, RateLimitError
from pydantic import BaseModel

from src.llm_client import LLMClient


class ExampleModel(BaseModel):
    value: str


class FakeMessage:
    def __init__(self, content: str | None = None, refusal: str | None = None) -> None:
        self.content = content
        self.refusal = refusal


class FakeChoice:
    def __init__(self, message: FakeMessage) -> None:
        self.message = message


class FakeResponse:
    def __init__(self, content: str | None = None) -> None:
        self.choices = [FakeChoice(FakeMessage(content=content))]
        self.usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)


class FakeCompletions:
    def __init__(self, outcomes) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        outcome = self._outcomes[self.calls - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(outcomes))


def make_rate_limit_error() -> RateLimitError:
    return RateLimitError("rate limit", response=httpx.Response(429, request=httpx.Request("POST", "https://example.com")), body=None)


def make_auth_error() -> AuthenticationError:
    return AuthenticationError("invalid API key", response=httpx.Response(401, request=httpx.Request("POST", "https://example.com")), body=None)


def test_retries_only_retryable_errors(monkeypatch):
    client = LLMClient(api_key="test")
    client.client = FakeClient([make_rate_limit_error(), FakeResponse(content='{"value": "ok"}')])

    result = client.structured(step="test", model=ExampleModel, system="sys", data="input")

    assert isinstance(result, ExampleModel)
    assert result.value == "ok"
    assert client.client.chat.completions.calls == 2


def test_non_retryable_errors_raise_immediately(monkeypatch):
    client = LLMClient(api_key="test")
    client.client = FakeClient([make_auth_error()])

    with pytest.raises(RuntimeError, match="non-retryable"):
        client.structured(step="test", model=ExampleModel, system="sys", data="input")

    assert client.client.chat.completions.calls == 1


def test_normalizes_schema_additional_properties():
    client = LLMClient(api_key="test")
    schema = {
        "title": "ExampleModel",
        "type": "object",
        "properties": {
            "value": {"type": "string"}
        }
    }

    normalized = client._normalize_schema(schema)

    assert normalized["additionalProperties"] is False
    assert normalized["properties"]["value"] == {"type": "string"}
    assert normalized["required"] == ["value"]


def test_normalizes_schema_required_for_optional_fields():
    client = LLMClient(api_key="test")
    schema = {
        "title": "ExampleModel",
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {"type": "string"}
        },
        "required": ["required_field"]
    }

    normalized = client._normalize_schema(schema)

    assert normalized["required"] == ["required_field", "optional_field"]
