from __future__ import annotations

import argparse
import sys
from functools import partial
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
from src.agents.api_test_generator.checklist_reader import api_labeled_cases, read_checklist_cases
from src.agents.api_test_generator.openapi_parser import OpenAPIParseError
from src.agents.api_test_generator.pipeline import run_api_test_pipeline
from src.app.pipeline import read_state, run_document_pipeline

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATE_DIR = ROOT / ".state"
STATE_FILE = STATE_DIR / "state.json"
OVERVIEW_FILE = STATE_DIR / "system_overview.md"
CHECKLIST = ROOT / "checklist.csv"
SUPPORTED = {".md", ".txt", ".doc", ".csv"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Xray-ready tests for genuine documentation coverage gaps.")
    subparsers = parser.add_subparsers(dest="command")
    docs_parser = subparsers.add_parser("generate-docs", help="generate manual Xray test cases from documentation")
    docs_parser.add_argument("--doc", help="one document path relative to docs/")
    docs_parser.add_argument("--dry-run", action="store_true")
    docs_parser.add_argument("--verbose", action="store_true")
    tests_parser = subparsers.add_parser("generate-tests", help="generate Playwright API tests from API-labeled checklist cases")
    tests_parser.add_argument(
        "--openapi",
        required=False,
        help="local JSON spec or URL (usually GET /v3/api-docs or /swagger.json)",
    )
    tests_parser.add_argument("--output-dir", default="automation/api", help="output directory relative to project root")
    tests_parser.add_argument("--dry-run", action="store_true")
    tests_parser.add_argument("--verbose", action="store_true")
    return parser


def files_for(args: argparse.Namespace) -> list[Path]:
    if args.doc:
        candidate = DOCS / args.doc
        if not candidate.is_file():
            raise FileNotFoundError(f"Document not found under docs/: {args.doc}")
        return [candidate]

    return [
        path
        for path in DOCS.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED
        and not path.name.startswith("_")
        and path.name.lower() != "readme.md"
    ]


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
        find_gaps=partial(find_gaps, checklist=checklist_summary(CHECKLIST)),
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


def setup_runtime(parser: argparse.ArgumentParser, args: argparse.Namespace) -> tuple[object, object]:
    load_dotenv(ROOT / ".env")
    try:
        config = load_runtime_config()
    except ValueError as error:
        parser.error(str(error))
    client = LLMClient(config.api_key, args.verbose)
    return config, client


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "generate-tests" and not args.openapi:
        parser.error("--openapi is required; obtain the spec from GET /v3/api-docs or /swagger.json.")
    if args.command == "generate-tests" and not api_labeled_cases(read_checklist_cases(CHECKLIST)):
        print("No test cases labeled 'api' found in checklist.csv — nothing to generate")
        return 0
    config, client = setup_runtime(parser, args)
    if args.command == "generate-tests":
        try:
            output_dir = ROOT / args.output_dir
            return run_api_test_pipeline(
                client=client,
                checklist_path=CHECKLIST,
                openapi_source=args.openapi,
                output_dir=output_dir,
                base_path=config.base_path,
                dry_run=args.dry_run,
            )
        except OpenAPIParseError as error:
            parser.error(str(error))
    state = read_state(STATE_FILE)
    overview = load_overview(OVERVIEW_FILE)
    for document in files_for(args):
        overview, state = process_document(document, client=client, config=config, state=state, overview=overview, dry_run=args.dry_run, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
