from __future__ import annotations

import csv
import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.config import load_runtime_config
from src.llm_client import LLMClient
from src.main import (
    OVERVIEW_FILE,
    STATE_DIR,
    files_for,
    process_document,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CHECKLIST = ROOT / "checklist.csv"
STATE_FILE = ROOT / ".state" / "state.json"


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {"processed_documents": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"processed_documents": {}}


def read_checklist() -> list[dict[str, str]]:
    if not CHECKLIST.exists():
        return []
    with CHECKLIST.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def document_paths() -> list[Path]:
    if not DOCS.exists():
        return []
    return sorted(
        path
        for path in DOCS.rglob("*")
        if path.is_file()
        and path.name.lower() not in {"readme.md", ".gitkeep"}
        and not path.name.startswith("_")
    )


def save_uploaded_files(uploaded_files: list[object]) -> list[str]:
    DOCS.mkdir(exist_ok=True)
    saved_files = []
    for uploaded_file in uploaded_files:
        filename = Path(uploaded_file.name).name
        if not filename or Path(filename).suffix.lower() not in {".md", ".txt", ".doc", ".csv"}:
            continue
        destination = DOCS / filename
        destination.write_bytes(uploaded_file.getvalue())
        saved_files.append(filename)
    return saved_files


def run_generation(selected_document: str | None, dry_run: bool) -> int:
    load_dotenv(ROOT / ".env")
    config = load_runtime_config()
    client = LLMClient(config.api_key, verbose=False)
    state = read_state()
    overview = ""
    if OVERVIEW_FILE.exists():
        overview = OVERVIEW_FILE.read_text(encoding="utf-8")

    class GenerationArgs:
        doc = selected_document

    documents = files_for(GenerationArgs())
    generated_count = 0
    for document in documents:
        before = len(read_checklist())
        overview, state = process_document(
            document,
            client=client,
            config=config,
            state=state,
            overview=overview,
            dry_run=dry_run,
            verbose=False,
        )
        generated_count += max(0, len(read_checklist()) - before)
    return generated_count


def main() -> None:
    st.set_page_config(page_title="QA Coverage", page_icon="✅", layout="wide")
    st.title("QA Coverage")
    st.caption("Project status and test inventory")

    state = read_state()
    processed = state.get("processed_documents", {})
    documents = document_paths()
    checklist = read_checklist()

    st.sidebar.header("File management")
    uploaded_files = st.sidebar.file_uploader(
        "Upload documents",
        type=["md", "txt", "doc", "csv"],
        accept_multiple_files=True,
    )
    if uploaded_files and st.sidebar.button("Save uploaded files"):
        saved_files = save_uploaded_files(uploaded_files)
        if saved_files:
            st.sidebar.success(f"Saved: {', '.join(saved_files)}")
            st.rerun()
        st.sidebar.warning("No supported files were selected.")

    if CHECKLIST.exists():
        st.sidebar.download_button(
            "Download checklist.csv",
            data=CHECKLIST.read_bytes(),
            file_name="checklist.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.sidebar.info("checklist.csv is not available yet.")

    st.sidebar.header("Test generation")
    document_options = ["All documents"] + [
        path.relative_to(DOCS).as_posix() for path in documents
    ]
    selected_option = st.sidebar.selectbox("Document", document_options)
    dry_run = st.sidebar.checkbox("Dry run", value=False)
    if st.sidebar.button("Generate tests", type="primary", use_container_width=True):
        selected_document = None if selected_option == "All documents" else selected_option
        try:
            with st.spinner("Generating test cases..."):
                generated_count = run_generation(selected_document, dry_run)
            mode = "would be generated" if dry_run else "generated"
            st.sidebar.success(f"{generated_count} test cases {mode}.")
            if not dry_run:
                st.rerun()
        except (ValueError, FileNotFoundError, RuntimeError) as error:
            st.sidebar.error(str(error))

    generated_ids = [
        test_id
        for item in processed.values()
        for test_id in item.get("test_case_ids_generated", [])
    ]

    metric_columns = st.columns(4)
    metric_columns[0].metric("Documents", len(documents))
    metric_columns[1].metric("Processed", len(processed))
    metric_columns[2].metric("Test cases", len([row for row in checklist if row.get("TCID")]))
    metric_columns[3].metric("Generated", len(generated_ids))

    st.subheader("Documents")
    if documents:
        document_rows = []
        for path in documents:
            relative = path.relative_to(DOCS).as_posix()
            document_rows.append(
                {
                    "Document": relative,
                    "Status": "Processed" if relative in processed else "Pending",
                }
            )
        st.dataframe(document_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No documents found in docs/.")

    st.subheader("Test inventory")
    if checklist:
        visible_columns = ["TCID", "Test Summary", "Test Repository Path", "Labels"]
        available_columns = [column for column in visible_columns if column in checklist[0]]
        st.dataframe(
            [{column: row.get(column, "") for column in available_columns} for row in checklist],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No checklist.csv found or it contains no test cases.")

    with st.expander("Processing state"):
        st.json(processed)


if __name__ == "__main__":
    main()