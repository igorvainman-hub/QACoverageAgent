from __future__ import annotations

import csv
import re
from pathlib import Path

from schemas import GeneratedTestCase

HEADERS = ["TCID", "Test Summary", "Description", "Test Type", "Test Repository Path", "Label", "Action", "Data", "Expected Result"]
SAFE_PATH = re.compile(r"^[A-Za-z0-9_/-]+$")
INJECTION = re.compile(r"ignore previous|system prompt|you are now", re.IGNORECASE)


def validate_case(case: GeneratedTestCase) -> str | None:
    if not SAFE_PATH.fullmatch(case.test_repository_path):
        return "invalid Test Repository Path"
    text_fields = [case.summary, case.description, *(x.action for x in case.steps), *(x.expected_result for x in case.steps)]
    if any(len(field) > 500 for field in text_fields):
        return "field exceeds 500 characters"
    if any(INJECTION.search(field) for field in text_fields):
        return "suspicious prompt-injection marker"
    return None


def next_tcid(path: Path, prefix: str) -> int:
    highest = 0
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                match = re.fullmatch(rf"{re.escape(prefix)}-(\d+)", row.get("TCID", ""))
                if match: highest = max(highest, int(match.group(1)))
    return highest + 1


def _normalize_repo_path(path_value: str, base_path: str) -> str:
    repo_path = path_value.strip("/")
    base_prefix = base_path.strip("/")
    if not repo_path.startswith(base_prefix):
        repo_path = f"{base_prefix}/{repo_path}"
    return repo_path


def _row_for_case(case: GeneratedTestCase, repo_path: str, tcid: str, step_index: int, step) -> dict[str, str]:
    return {
        "TCID": tcid if step_index == 0 else "",
        "Test Summary": case.summary if step_index == 0 else "",
        "Description": case.description if step_index == 0 else "",
        "Test Type": "Manual" if step_index == 0 else "",
        "Test Repository Path": repo_path if step_index == 0 else "",
        "Label": ";".join(case.labels) if step_index == 0 else "",
        "Action": step.action,
        "Data": step.data or "",
        "Expected Result": step.expected_result,
    }


def append_cases(path: Path, cases: list[GeneratedTestCase], prefix: str, base_path: str) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = next_tcid(path, prefix)
    new_file = not path.exists() or path.stat().st_size == 0
    tcids: list[str] = []
    skipped = 0
    rows_to_write: list[dict[str, str]] = []

    tcid_counter = start
    for case in cases:
        repo_path = _normalize_repo_path(case.test_repository_path, base_path)
        case.test_repository_path = repo_path

        error = validate_case(case)
        if error:
            print(f"[WARNING] Пропущен невалидный кейс '{case.summary[:60]}...': {error}")
            skipped += 1
            continue

        tcid = f"{prefix}-{tcid_counter:03d}"
        tcid_counter += 1
        tcids.append(tcid)
        rows_to_write.extend(_row_for_case(case, repo_path, tcid, index, step) for index, step in enumerate(case.steps))

    with path.open("a", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=HEADERS, quoting=csv.QUOTE_MINIMAL)
        if new_file:
            writer.writeheader()
        writer.writerows(rows_to_write)

    if skipped:
        print(f"[WARNING] Всего пропущено невалидных кейсов: {skipped}")
    return tcids
