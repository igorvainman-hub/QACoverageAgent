from __future__ import annotations

import csv
from pathlib import Path

from src.llm_client import LLMClient
from src.schemas import CoverageMatrixResult, DocumentSection
from .prompts import COVERAGE_ANALYSIS_PROMPT


def checklist_summary(path: Path) -> str:
    if not path.exists():
        return "(No existing test cases.)"
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = csv.DictReader(source)
        return "\n".join(f"{r.get('TCID','')} | {r.get('Test Summary','')} | {r.get('Test Repository Path','')}" for r in rows if r.get("TCID")) or "(No existing test cases.)"


def find_gaps(client: LLMClient, sections: list[DocumentSection], overview: str, checklist: str) -> CoverageMatrixResult:
    section_data = "\n\n".join(
        f"<document_content>\nSECTION: {s.path}\n{s.raw_content}\n</document_content>"
        for s in sections
    )
    context = (
        f"SYSTEM OVERVIEW (data):\n<document_content>\n{overview}\n</document_content>\n"
        f"EXISTING TEST SUMMARIES (data):\n<document_content>\n{checklist}\n</document_content>"
    )
    system = COVERAGE_ANALYSIS_PROMPT
    return client.structured(step="2b", model=CoverageMatrixResult, system=system, data=section_data, context=context)
