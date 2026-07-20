from __future__ import annotations

from pathlib import Path

from llm_client import LLMClient
from schemas import GeneratedTestCase

DEFAULT_OVERVIEW = "# System Overview\n"


def load_overview(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else DEFAULT_OVERVIEW


def update_overview(client: LLMClient, existing: str, feature: str, cases: list[GeneratedTestCase], tcids: list[str]) -> str:
    rendered = "\n".join(f"{tcid}: {case.summary}" for tcid, case in zip(tcids, cases))

    instruction = f"""Update the Markdown section for feature '{feature}' in the system overview.

    If an existing section is provided, preserve any still-relevant facts from it — especially previously
    noted integrations with other features — and merge them with what the new tests reveal. Do not silently
    drop integration notes just because the current batch of new tests doesn't mention them; only remove a
    fact if the new tests explicitly contradict it.

    Write 3-5 sentences covering, in this order:
    1. What the feature does (one sentence).
    2. What is now tested — the TCID range from this batch, described by what it covers, not just the range itself.
    3. Known integrations with other features, if any — merged from prior knowledge and this batch.

    Return only the section body as plain Markdown starting with '## {feature}'."""

    # Plain text output is intentionally constrained through this tiny schema.
    from pydantic import BaseModel, Field
    class OverviewSection(BaseModel):
        markdown: str = Field(min_length=5, max_length=2000)
    result = client.structured(step="4", model=OverviewSection, system=instruction, data=f"Existing overview:\n{existing}\nNew tests:\n{rendered}")
    return _replace_section(existing, feature, result.markdown)


def _replace_section(overview: str, feature: str, section: str) -> str:
    import re
    section = section.strip()
    if not section.startswith("## "):
        section = f"## {feature}\n{section}"
    pattern = re.compile(rf"^## {re.escape(feature)}\s*$.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    if pattern.search(overview):
        return pattern.sub(section + "\n", overview).strip() + "\n"
    return overview.rstrip() + "\n\n" + section + "\n"
