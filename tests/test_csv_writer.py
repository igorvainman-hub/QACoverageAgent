import csv
from pathlib import Path

from src.csv_writer import append_cases
from src.schemas import GeneratedTestCase, TestStep


def test_append_cases_writes_rows_and_normalizes_paths(tmp_path: Path):
    path = tmp_path / "checklist.csv"
    case = GeneratedTestCase(
        summary="Login works",
        description="Verify login flow",
        test_repository_path="feature/auth",
        labels=["auth"],
        steps=[TestStep(action="Open page", data="", expected_result="Logged in")],
    )

    tcids = append_cases(path, [case], "QA", "MyProject")

    assert tcids == ["QA-001"]
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["TCID"] == "QA-001"
    assert rows[0]["Test Repository Path"] == "MyProject/feature/auth"
