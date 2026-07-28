from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RuntimeConfig:
    api_key: str
    base_path: str
    tcid_prefix: str


def load_runtime_config(env: Mapping[str, str | None] | None = None) -> RuntimeConfig:
    values = env if env is not None else os.environ
    api_key = values.get("OPENAI_API_KEY")
    base_path = values.get("QA_BASE_PATH")
    prefix = values.get("QA_TCID_PREFIX", "QA")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    if not base_path:
        raise ValueError("QA_BASE_PATH is required")
    if not prefix.replace("-", "").isalnum():
        raise ValueError("QA_TCID_PREFIX must be alphanumeric or hyphenated")

    return RuntimeConfig(api_key=api_key, base_path=base_path, tcid_prefix=prefix)
