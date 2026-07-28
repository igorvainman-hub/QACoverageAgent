from __future__ import annotations

import copy
import time
from typing import TypeVar

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from src.agents.prompts import INJECTION_RULE

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self, api_key: str, verbose: bool = False) -> None:
        self.client = OpenAI(api_key=api_key)
        self.verbose = verbose

    def structured(self, *, step: str, model: type[T], system: str, data: str, context: str = "") -> T:
        """Call Structured Outputs and retry only transient API failures with backoff."""
        schema = self._normalize_schema(model.model_json_schema())
        messages = [
            {"role": "system", "content": f"{INJECTION_RULE}\n\n{system}"},
            {"role": "user", "content": f"{context}\n<document_content>\n{data}\n</document_content>"},
        ]
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": {"name": model.__name__, "strict": True, "schema": schema}},
                )
            except (RateLimitError, APIConnectionError, APITimeoutError) as error:
                last_error = error
                if self.verbose:
                    print(f"[LLM] step={step} attempt={attempt + 1} failed (retryable): {error}")
                if attempt == 2:
                    break
                time.sleep(2**attempt)
                continue
            except Exception as error:
                raise RuntimeError(f"LLM call failed at step {step} (non-retryable): {error}") from error

            message = response.choices[0].message
            if getattr(message, "refusal", None):
                raise RuntimeError(f"OpenAI refused request at step {step}: {message.refusal}")
            content = getattr(message, "content", None)
            if not content:
                raise RuntimeError(f"OpenAI returned an empty structured response at step {step}")

            if self.verbose:
                usage = response.usage
                print(f"[LLM] step={step} attempt={attempt + 1} tokens_in={getattr(usage, 'prompt_tokens', '?')} tokens_out={getattr(usage, 'completion_tokens', '?')}")

            try:
                return model.model_validate_json(content)
            except ValidationError as error:
                raise RuntimeError(f"LLM response failed schema validation at step {step}: {error}") from error

        raise RuntimeError(f"LLM call failed at step {step} after 3 attempts: {last_error}")

    def _normalize_schema(self, schema: dict) -> dict:
        schema = copy.deepcopy(schema)
        if schema.get("type") == "object":
            if "additionalProperties" not in schema:
                schema["additionalProperties"] = False
            if "properties" in schema:
                schema["required"] = list(schema["properties"].keys())
        for key, value in list(schema.items()):
            if isinstance(value, dict):
                schema[key] = self._normalize_schema(value)
            elif isinstance(value, list):
                schema[key] = [self._normalize_schema(item) if isinstance(item, dict) else item for item in value]
        return schema
