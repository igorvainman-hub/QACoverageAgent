from __future__ import annotations

import json

from src.llm_client import LLMClient
from src.schemas import CoverageGap, GeneratedTestCases
from .prompts import INJECTION_RULE, TEST_DESIGN_PROMPT


def design_tests(client: LLMClient, gaps: list[CoverageGap], base_path: str) -> GeneratedTestCases:
    instruction = f"{INJECTION_RULE}\n\n{TEST_DESIGN_PROMPT}\n\nTest Repository Paths are rooted under {base_path}."
    return client.structured(
        step="3",
        model=GeneratedTestCases,
        system=instruction,
        data=json.dumps([g.model_dump() for g in gaps], ensure_ascii=False),
    )
