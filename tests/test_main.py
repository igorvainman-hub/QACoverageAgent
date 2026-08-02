import pytest
from pathlib import Path
from types import SimpleNamespace

from src import main


def test_legacy_document_arguments_are_rejected():
    with pytest.raises(SystemExit):
        main.build_parser().parse_args(["--doc", "auth.md", "--dry-run"])


def test_generate_docs_command_is_explicitly_supported():
    args = main.build_parser().parse_args(["generate-docs", "--doc", "auth.md", "--dry-run"])

    assert args.command == "generate-docs"
    assert args.doc == "auth.md"
    assert args.dry_run


def test_process_document_marks_document_as_processed(tmp_path, monkeypatch):
    document = tmp_path / "auth.md"
    document.write_text("# Auth\n", encoding="utf-8")

    checklist = tmp_path / "checklist.csv"
    checklist.write_text("", encoding="utf-8")
    state_file = tmp_path / "state.json"
    overview_file = tmp_path / "system_overview.md"

    monkeypatch.setattr(main, "DOCS", tmp_path)
    monkeypatch.setattr(main, "CHECKLIST", checklist)
    monkeypatch.setattr(main, "STATE_DIR", tmp_path)
    monkeypatch.setattr(main, "STATE_FILE", state_file)
    monkeypatch.setattr(main, "OVERVIEW_FILE", overview_file)
    monkeypatch.setattr(main, "parse_document", lambda path: [SimpleNamespace(path="feature/auth", raw_content="body")])
    monkeypatch.setattr(main, "find_gaps", lambda *args, **kwargs: SimpleNamespace(covered=[], gaps=[]))
    monkeypatch.setattr(main, "design_tests", lambda *args, **kwargs: SimpleNamespace(test_cases=[]))
    monkeypatch.setattr(main, "validate_case", lambda case: None)
    monkeypatch.setattr(main, "append_cases", lambda *args, **kwargs: [])
    monkeypatch.setattr(main, "update_overview", lambda *args, **kwargs: "updated overview")

    state = {"processed_documents": {}}
    config = SimpleNamespace(api_key="sk-test", base_path="MyProject", tcid_prefix="QA")

    updated_overview, updated_state = main.process_document(
        document,
        client=object(),
        config=config,
        state=state,
        overview="initial overview",
        dry_run=False,
        verbose=False,
    )

    assert updated_overview == "initial overview"
    assert "auth.md" in updated_state["processed_documents"]
    assert updated_state["processed_documents"]["auth.md"]["test_case_ids_generated"] == []
