from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.agents.api_test_generator.checklist_reader import read_checklist_cases
from src.agents.api_test_generator.endpoint_matcher import match_endpoints
from src.agents.api_test_generator.openapi_parser import load_openapi_json, parse_openapi

from .k6_generator import generate_k6_journey_files
from .thresholds import load_threshold_config, thresholds_for_tags


class LoadTestGenerationError(ValueError):
    """A user-facing error while creating a complete k6 journey."""


def parse_journey(value: str) -> list[str]:
    journey = [tcid.strip() for tcid in value.split(",") if tcid.strip()]
    if not journey:
        raise LoadTestGenerationError("--journey must contain at least one TCID.")
    return journey


def run_load_test_pipeline(
    *,
    client: object,
    checklist_path: Path,
    openapi_source: str,
    journey: list[str],
    thresholds_path: Path | None,
    vus: int,
    duration: str,
    output_dir: Path,
    base_path: str,
    dry_run: bool,
    read_cases: Callable = read_checklist_cases,
    load_spec: Callable = load_openapi_json,
    parse_spec: Callable = parse_openapi,
    match: Callable = match_endpoints,
    load_thresholds: Callable = load_threshold_config,
    generate_files: Callable = generate_k6_journey_files,
    slug: str | None = None,
) -> int:
    """Match every requested TCID and generate a single complete k6 journey."""
    all_cases = dict(read_cases(checklist_path))
    requested_cases = []
    for tcid in dict.fromkeys(journey):
        case = all_cases.get(tcid)
        if case is None:
            raise LoadTestGenerationError(f"TCID {tcid} not found in checklist.csv.")
        if "api" not in {label.lower() for label in case.labels}:
            raise LoadTestGenerationError(f"TCID {tcid} is not labeled 'api' in checklist.csv.")
        requested_cases.append((tcid, case))

    spec = load_spec(openapi_source)
    endpoints = parse_spec(spec)
    result = match(client, requested_cases, endpoints, base_path)
    matches = {item.tcid: item for item in result.matches if item.matched and (item.method, item.path) in endpoints}
    for tcid in journey:
        if tcid not in matches:
            raise LoadTestGenerationError(f"TCID {tcid} could not be matched to an API endpoint; no partial journey was generated.")

    ordered_journey = [
        (tcid, all_cases[tcid], endpoints[(matches[tcid].method or "", matches[tcid].path or "")])
        for tcid in journey
    ]
    config = load_thresholds(thresholds_path)
    effective = thresholds_for_tags(config, [endpoint.tag for _, _, endpoint in ordered_journey])
    base_url = _openapi_base_url(spec)
    if base_url == "TODO-BASE-URL":
        print("[WARNING] OpenAPI spec has no servers[0].url; generated k6 script uses TODO-BASE-URL. Set BASE_URL before running k6.")
    generation = generate_files(
        output_dir,
        ordered_journey,
        base_url=base_url,
        thresholds=effective,
        vus=vus,
        duration=duration,
        slug=slug,
    )
    if dry_run:
        print(f"[DRY RUN] Would write {len(generation.files)} k6 journey files to {output_dir / 'journeys'}.")
        return 0
    for path, content in generation.files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Generated k6 journey: {output_dir / 'journeys' / f'{generation.slug}.js'}")
    return 0


def run_load_test_journeys_pipeline(
    *,
    journeys: list[list[str] | str],
    run_journey: Callable = run_load_test_pipeline,
    print_result: Callable[[str], None] = print,
    **kwargs: object,
) -> int:
    """Run journeys independently and report every success or failure."""
    used_slugs: set[str] = set()
    results: list[tuple[str, str | None]] = []
    for raw_journey in journeys:
        display = raw_journey if isinstance(raw_journey, str) else ",".join(raw_journey)
        try:
            journey = parse_journey(raw_journey) if isinstance(raw_journey, str) else raw_journey
            slug = _unique_slug(journey, used_slugs)
            run_journey(journey=journey, slug=slug, **kwargs)
        except Exception as error:
            message = str(error)
            results.append((display, message))
            print_result(f"✗ {display} — {message}")
        else:
            results.append((display, None))
            print_result(f"✓ {display}")

    succeeded = sum(error is None for _, error in results)
    action = "would generate" if kwargs.get("dry_run") else "generated"
    print_result(f"Load-test journeys: {succeeded}/{len(journeys)} {action} successfully.")
    return 0 if succeeded == len(journeys) else 1


def _unique_slug(journey: list[str], used: set[str]) -> str:
    base = "-to-".join(journey).lower()
    base = "".join(character if character.isalnum() else "-" for character in base).strip("-") or "journey"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _openapi_base_url(spec: dict) -> str:
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict) and isinstance(first.get("url"), str) and first["url"]:
            return first["url"]
    return "TODO-BASE-URL"
