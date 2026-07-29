from pathlib import Path
from types import SimpleNamespace

from src.app.pipeline import run_document_pipeline


def test_run_document_pipeline_marks_document_as_processed(tmp_path):
    document = tmp_path / "auth.md"
    document.write_text("# Auth\n", encoding="utf-8")

    checklist = tmp_path / "checklist.csv"
    checklist.write_text("", encoding="utf-8")
    state_file = tmp_path / "state.json"
    overview_file = tmp_path / "system_overview.md"

    def fake_parse_document(path: Path):
        return [SimpleNamespace(path="feature/auth", raw_content="body")]

    def fake_find_gaps(*args, **kwargs):
        return SimpleNamespace(covered=[], gaps=[])

    def fake_design_tests(*args, **kwargs):
        return SimpleNamespace(test_cases=[])

    def fake_validate_case(case):
        return None

    def fake_append_cases(*args, **kwargs):
        return []

    def fake_update_overview(*args, **kwargs):
        return "updated overview"

    state = {"processed_documents": {}}
    config = SimpleNamespace(api_key="sk-test", base_path="MyProject", tcid_prefix="QA")

    updated_overview, updated_state = run_document_pipeline(
        document,
        client=object(),
        config=config,
        state=state,
        overview="initial overview",
        dry_run=False,
        verbose=False,
        parse_document=fake_parse_document,
        find_gaps=fake_find_gaps,
        design_tests=fake_design_tests,
        validate_case=fake_validate_case,
        append_cases=fake_append_cases,
        update_overview=fake_update_overview,
        docs_root=tmp_path,
        checklist_path=checklist,
        state_dir=tmp_path,
        state_file=state_file,
        overview_file=overview_file,
    )

    assert updated_overview == "initial overview"
    assert "auth.md" in updated_state["processed_documents"]
    assert updated_state["processed_documents"]["auth.md"]["test_case_ids_generated"] == []
