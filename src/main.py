from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
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

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
STATE_DIR = ROOT / ".state"
STATE_FILE = STATE_DIR / "state.json"
OVERVIEW_FILE = STATE_DIR / "system_overview.md"
CHECKLIST = ROOT / "checklist.csv"
SUPPORTED = {".md", ".txt", ".doc", ".csv"}


def read_state() -> dict:
    if not STATE_FILE.exists(): return {"processed_documents": {}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def write_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def content_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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
    relative = str(document.relative_to(DOCS)).replace("\\", "/")
    digest = content_hash(document)
    if state["processed_documents"].get(relative, {}).get("content_hash") == digest:
        print(f"[SKIP] {relative} — unchanged (hash match)")
        return overview, state

    print(f"[PROCESSING] {relative}")
    sections = parse_document(document)
    matrix = find_gaps(client, sections, overview, checklist_summary(CHECKLIST))
    print(f"  Sections: {len(sections)} | Covered: {len(matrix.covered)} | Gaps: {len(matrix.gaps)}")
    if verbose:
        for gap in matrix.gaps:
            print(f"  gap [{gap.gap_type}/{gap.priority}]: {gap.scenario_description}")

    base_path = config.base_path
    tcid_prefix = config.tcid_prefix
    generated = design_tests(client, matrix.gaps, base_path).test_cases if matrix.gaps else []
    valid_cases, skipped = [], 0
    for case in generated:
        reason = validate_case(case)
        if reason:
            skipped += 1
            print(f"[WARNING] Skipped invalid case: {reason}")
        else:
            valid_cases.append(case)

    if dry_run:
        print(f"  [DRY RUN] Would write {len(valid_cases)} cases; skipped {skipped}.")
        return overview, state

    tcids = append_cases(CHECKLIST, valid_cases, tcid_prefix, base_path) if valid_cases else []
    if valid_cases:
        feature = sections[0].path.split("/")[0]
        updated = update_overview(client, overview, feature, valid_cases, tcids)
        updated_lower = updated.lower()
        if len(updated) > 50000 or any(marker in updated_lower for marker in ("ignore previous", "system prompt", "you are now")):
            print("[WARNING] Suspicious system overview update rejected")
        else:
            STATE_DIR.mkdir(exist_ok=True)
            OVERVIEW_FILE.write_text(updated, encoding="utf-8")
            overview = updated

    if matrix.gaps and not valid_cases:
        print(f"  [WARNING] All generated cases were invalid — {relative} will be re-analyzed next run.")
        return overview, state

    state["processed_documents"][relative] = {
        "content_hash": digest,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "test_case_ids_generated": tcids,
    }
    write_state(state)
    print(f"  Generated cases: {len(tcids)}" + (f" ({tcids[0]} .. {tcids[-1]})" if tcids else ""))
    return overview, state


def setup_runtime(parser: argparse.ArgumentParser) -> tuple[argparse.Namespace, object, dict, str, object]:
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    try:
        config = load_runtime_config()
    except ValueError as error:
        parser.error(str(error))
    client = LLMClient(config.api_key, args.verbose)
    state = read_state()
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