from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import load_runtime_config
from csv_writer import append_cases, validate_case
from document_parser import parse_document
from llm_client import LLMClient
from src.agents.coverage_matrix import checklist_summary, find_gaps
from src.agents.overview import load_overview, update_overview
from src.agents.test_designer import design_tests
from src.app.pipeline import read_state, run_document_pipeline, write_state

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATE_DIR = ROOT / ".state"
STATE_FILE = STATE_DIR / "state.json"
OVERVIEW_FILE = STATE_DIR / "system_overview.md"
CHECKLIST = ROOT / "checklist.csv"
SUPPORTED = {".md", ".txt", ".doc", ".csv"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Xray-ready tests for genuine documentation coverage gaps.")
    parser.add_argument("--doc", help="one document path relative to docs/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def files_for(args: argparse.Namespace) -> list[Path]:
    if args.doc:
        candidate = DOCS / args.doc
        if not candidate.is_file(): raise FileNotFoundError(f"Document not found under docs/: {args.doc}")
        return [candidate]
    return [path for path in DOCS.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED and not path.name.startswith("_") and path.name.lower() != "readme.md"]


def process_document(document: Path, *, client: object, config: object, state: dict, overview: str, dry_run: bool, verbose: bool) -> tuple[str, dict]:
    return run_document_pipeline(
        document,
        client=client,
        config=config,
        state=state,
        overview=overview,
        dry_run=dry_run,
        verbose=verbose,
        parse_document=parse_document,
        find_gaps=lambda client_arg, sections, overview_arg, checklist_arg: find_gaps(client_arg, sections, overview_arg, checklist_summary(CHECKLIST)),
        design_tests=design_tests,
        validate_case=validate_case,
        append_cases=append_cases,
        update_overview=update_overview,
        docs_root=DOCS,
        checklist_path=CHECKLIST,
        state_dir=STATE_DIR,
        state_file=STATE_FILE,
        overview_file=OVERVIEW_FILE,
    )


def setup_runtime(parser: argparse.ArgumentParser) -> tuple[argparse.Namespace, object, dict, str, object]:
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    try:
        config = load_runtime_config()
    except ValueError as error:
        parser.error(str(error))
    client = LLMClient(config.api_key, args.verbose)
    state = read_state(STATE_FILE)
    overview = load_overview(OVERVIEW_FILE)
    return args, config, state, overview, client


def main() -> int:
    parser = build_parser()
    args, config, state, overview, client = setup_runtime(parser)
    for document in files_for(args):
        overview, state = process_document(document, client=client, config=config, state=state, overview=overview, dry_run=args.dry_run, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())