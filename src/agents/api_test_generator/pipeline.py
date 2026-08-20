from __future__ import annotations

from pathlib import Path
from typing import Callable

from .checklist_reader import api_labeled_cases, read_checklist_cases
from .coverage_report import render_coverage_report
from .endpoint_matcher import match_endpoints
from .openapi_parser import load_openapi_json, parse_openapi
from .playwright_generator import generate_playwright_files


def run_api_test_pipeline(
    *,
    client: object,
    checklist_path: Path,
    openapi_source: str,
    output_dir: Path,
    base_path: str,
    dry_run: bool,
    read_cases: Callable = read_checklist_cases,
    load_spec: Callable = load_openapi_json,
    parse_spec: Callable = parse_openapi,
    match: Callable = match_endpoints,
    generate_files: Callable = generate_playwright_files,
    render_report: Callable = render_coverage_report,
) -> int:
    cases = api_labeled_cases(read_cases(checklist_path))
    if not cases:
        print("No test cases labeled 'api' found in checklist.csv — nothing to generate")
        return 0
    spec = load_spec(openapi_source)
    endpoints = parse_spec(spec)
    result = match(client, cases, endpoints, base_path)
    case_by_tcid = dict(cases)
    schemes = spec.get("components", {}).get("securitySchemes", {}) if isinstance(spec.get("components"), dict) else {}
    schemes = schemes if isinstance(schemes, dict) else {}
    generation = generate_files(output_dir, case_by_tcid, result.matches, endpoints, schemes)
    files = generation.files
    files[output_dir / "coverage-report.md"] = render_report(cases, result.matches)
    if dry_run:
        print(f"[DRY RUN] Would write {len(files)} API automation files to {output_dir}.")
        return 0
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    generated = len(generation.generated_tcids)
    print(f"Generated API tests: {generated}/{len(cases)}. Coverage report: {output_dir / 'coverage-report.md'}")
    return 0
