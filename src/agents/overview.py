from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from src.llm_client import LLMClient
from src.schemas import GeneratedTestCase
from .prompts import INJECTION_RULE, OVERVIEW_PROMPT

DEFAULT_OVERVIEW = "# System Overview\n"


def load_overview(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else DEFAULT_OVERVIEW


def update_overview(client: LLMClient, existing: str, feature: str, cases: list[GeneratedTestCase], tcids: list[str]) -> str:
    rendered = "\n".join(f"{tcid}: {case.summary}" for tcid, case in zip(tcids, cases))
    instruction = f"{INJECTION_RULE}\n\n{OVERVIEW_PROMPT.format(feature=feature)}"

    class OverviewSection(BaseModel):
        markdown: str = Field(min_length=5, max_length=2000)

    result = client.structured(step="4", model=OverviewSection, system=instruction, data=f"Existing overview:\n{existing}\nNew tests:\n{rendered}")
    return _replace_section(existing, feature, result.markdown)


def _replace_section(overview: str, feature: str, section: str) -> str:
    section = section.strip()
    if not section.startswith("## "):
        section = f"## {feature}\n{section}"
    pattern = re.compile(rf"^## {re.escape(feature)}\s*$.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(overview):
        return pattern.sub(section + "\n", overview).strip() + "\n"
    return overview.rstrip() + "\n\n" + section + "\n"
