from __future__ import annotations

import csv
from pathlib import Path

from src.schemas import GeneratedTestCase, TestStep


def read_checklist_cases(path: Path) -> list[tuple[str, GeneratedTestCase]]:
    """Restore Xray's multi-row checklist format to case objects and their TCIDs."""
    if not path.exists():
        return []
    cases: list[tuple[str, GeneratedTestCase]] = []
    current_tcid: str | None = None
    current: dict[str, object] | None = None
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            tcid = (row.get("TCID") or "").strip()
            if tcid:
                _append_case(cases, current_tcid, current)
                current_tcid = tcid
                current = {
                    "summary": row.get("Test Summary", ""),
                    "description": row.get("Description", ""),
                    "test_repository_path": row.get("Test Repository Path", ""),
                    "labels": _labels(row.get("Label", "")),
                    "steps": [],
                }
            if current is not None:
                _add_step(current, row)
    _append_case(cases, current_tcid, current)
    return cases


def api_labeled_cases(cases: list[tuple[str, GeneratedTestCase]]) -> list[tuple[str, GeneratedTestCase]]:
    return [(tcid, case) for tcid, case in cases if "api" in {label.lower() for label in case.labels}]


def _append_case(cases: list[tuple[str, GeneratedTestCase]], tcid: str | None, data: dict[str, object] | None) -> None:
    if tcid is None or data is None:
        return
    try:
        cases.append((tcid, GeneratedTestCase.model_validate(data)))
    except ValueError as error:
        print(f"[WARNING] Skipped malformed checklist case {tcid}: {error}")


def _add_step(case: dict[str, object], row: dict[str, str]) -> None:
    action = (row.get("Action") or "").strip()
    expected = (row.get("Expected Result") or "").strip()
    if action or expected:
        steps = case["steps"]
        assert isinstance(steps, list)
        steps.append({"action": action, "data": row.get("Data") or None, "expected_result": expected})


def _labels(value: str) -> list[str]:
    return [label.strip() for label in value.split(";") if label.strip()]
