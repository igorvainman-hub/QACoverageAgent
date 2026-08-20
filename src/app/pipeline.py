from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def content_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {"processed_documents": {}}
    return json.loads(state_file.read_text(encoding="utf-8"))


def write_state(state: dict[str, Any], state_dir: Path, state_file: Path) -> None:
    state_dir.mkdir(exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_document_pipeline(
    document: Path,
    *,
    client: object,
    config: object,
    state: dict[str, Any],
    overview: str,
    dry_run: bool,
    verbose: bool,
    parse_document: Callable[[Path], list[Any]],
    find_gaps: Callable[[object, list[Any], str, str], Any],
    design_tests: Callable[[object, list[Any], str], Any],
    validate_case: Callable[[Any], str | None],
    append_cases: Callable[[Path, list[Any], str, str], list[str]],
    update_overview: Callable[[object, str, str, list[Any], list[str]], str],
    docs_root: Path,
    checklist_path: Path,
    state_dir: Path,
    state_file: Path,
    overview_file: Path,
) -> tuple[str, dict[str, Any]]:
    relative = str(document.relative_to(docs_root)).replace("\\", "/")
    digest = content_hash(document)
    if state["processed_documents"].get(relative, {}).get("content_hash") == digest:
        print(f"[SKIP] {relative} — unchanged (hash match)")
        return overview, state

    print(f"[PROCESSING] {relative}")
    sections = parse_document(document)
    matrix = find_gaps(client, sections, overview, "")
    print(f"  Sections: {len(sections)} | Covered: {len(matrix.covered)} | Gaps: {len(matrix.gaps)}")
    if verbose:
        for gap in matrix.gaps:
            print(f"  gap [{gap.gap_type}/{gap.priority}]: {gap.scenario_description}")

    generated = design_tests(client, matrix.gaps, config.base_path).test_cases if matrix.gaps else []
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

    tcids = append_cases(checklist_path, valid_cases, config.tcid_prefix, config.base_path) if valid_cases else []
    if valid_cases:
        feature = sections[0].path.split("/")[0]
        updated = update_overview(client, overview, feature, valid_cases, tcids)
        updated_lower = updated.lower()
        if len(updated) > 50000 or any(marker in updated_lower for marker in ("ignore previous", "system prompt", "you are now")):
            print("[WARNING] Suspicious system overview update rejected")
        else:
            state_dir.mkdir(exist_ok=True)
            overview_file.write_text(updated, encoding="utf-8")
            overview = updated

    if matrix.gaps and not valid_cases:
        print(f"  [WARNING] All generated cases were invalid — {relative} will be re-analyzed next run.")
        return overview, state

    state["processed_documents"][relative] = {
        "content_hash": digest,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "test_case_ids_generated": tcids,
    }
    write_state(state, state_dir, state_file)
    print(f"  Generated cases: {len(tcids)}" + (f" ({tcids[0]} .. {tcids[-1]})" if tcids else ""))
    return overview, state
