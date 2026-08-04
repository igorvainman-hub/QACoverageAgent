from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.agents.api_test_generator.openapi_parser import OpenAPIEndpoint
from src.schemas import GeneratedTestCase

from .models import EffectiveThresholds


@dataclass(frozen=True)
class K6Generation:
    files: dict[Path, str]
    slug: str


def generate_k6_journey_files(
    output_dir: Path,
    journey: list[tuple[str, GeneratedTestCase, OpenAPIEndpoint]],
    *,
    base_url: str,
    thresholds: EffectiveThresholds,
    vus: int,
    duration: str,
    slug: str | None = None,
) -> K6Generation:
    """Return k6 journey files; the caller owns filesystem writes."""
    slug = slug or _journey_slug([tcid for tcid, _, _ in journey])
    journey_dir = output_dir / "journeys"
    return K6Generation(
        files={
            journey_dir / f"{slug}.js": _script(journey, base_url, thresholds, vus, duration),
            journey_dir / f"{slug}.md": _report(journey, thresholds),
        },
        slug=slug,
    )


def _script(
    journey: list[tuple[str, GeneratedTestCase, OpenAPIEndpoint]],
    base_url: str,
    thresholds: EffectiveThresholds,
    vus: int,
    duration: str,
) -> str:
    values = thresholds.values
    placeholder = "// PLACEHOLDER THRESHOLDS — replace with real SLA before running against production-like load.\n" if thresholds.is_placeholder else ""
    steps = "\n\n".join(_step(index, tcid, case, endpoint) for index, (tcid, case, endpoint) in enumerate(journey, start=1))
    return (
        "import http from 'k6/http';\n"
        "import { check, sleep } from 'k6';\n\n"
        f"{placeholder}"
        "export const options = {\n"
        "  stages: [\n"
        f"    {{ duration: '30s', target: {vus} }},\n"
        f"    {{ duration: '{_js_string(duration)}', target: {vus} }},\n"
        "    { duration: '30s', target: 0 },\n"
        "  ],\n"
        "  thresholds: {\n"
        f"    http_req_duration: ['p(95)<{values.p95}', 'p(99)<{values.p99}'],\n"
        f"    http_req_failed: ['rate<{values.error_rate}'],\n"
        "  },\n"
        "};\n\n"
        f"const BASE_URL = __ENV.BASE_URL || '{_js_string(base_url)}';\n\n"
        "export default function () {\n"
        f"{steps}\n\n"
        "  sleep(1);\n"
        "}\n"
    )


def _step(index: int, tcid: str, case: GeneratedTestCase, endpoint: OpenAPIEndpoint) -> str:
    dependency_todo = ""
    if index > 1:
        dependency_todo = (
            "  // TODO: If this step depends on data from a previous step's response,\n"
            "  // extract it here (e.g. const orderId = res1.json('id')) and use it below.\n"
        )
    body = _example_body(endpoint.request_schema)
    url = f"`${{BASE_URL}}{_path_with_todos(endpoint.path)}`"
    method = endpoint.method.lower()
    if body is None:
        call = f"http.{method}({url})"
    else:
        rendered_body = json.dumps(body, ensure_ascii=False)
        call = f"http.{method}({url}, JSON.stringify({rendered_body}), {{ headers: {{ 'Content-Type': 'application/json' }} }})"
    summary = case.summary.replace("\n", " ")
    return (
        f"{dependency_todo}"
        f"  // Step {index} — Source: {tcid} — {summary}\n"
        f"  let res{index} = {call};\n"
        f"  check(res{index}, {{ '{_js_string(tcid)}: status is 2xx': (r) => r.status >= 200 && r.status < 300 }});"
    )


def _report(journey: list[tuple[str, GeneratedTestCase, OpenAPIEndpoint]], thresholds: EffectiveThresholds) -> str:
    values = thresholds.values
    lines = ["# k6 Load Test Journey", "", "## Steps", "", "| TCID | Endpoint | Summary |", "| --- | --- | --- |"]
    for tcid, case, endpoint in journey:
        lines.append(f"| {tcid} | {endpoint.method} {endpoint.path} | {_table(case.summary)} |")
    source = ", ".join(thresholds.sources)
    lines.extend([
        "",
        "## Applied thresholds",
        "",
        f"- Source: {source}",
        f"- p95: {values.p95}ms; p99: {values.p99}ms; error rate: {values.error_rate}",
        f"- Data-dependency TODOs: {max(0, len(journey) - 1)}",
    ])
    if thresholds.is_placeholder:
        lines.append("- Warning: placeholder thresholds must be replaced with a real SLA before production-like load.")
    return "\n".join(lines) + "\n"


def _path_with_todos(path: str) -> str:
    return re.sub(r"\{([^}]+)\}", lambda match: f"TODO-{match.group(1)}", path)


def _example_body(schema: dict | None) -> object | None:
    if schema is None:
        return None
    if isinstance(schema.get("example"), (dict, list, str, int, float, bool)):
        return schema["example"]
    properties = schema.get("properties")
    if isinstance(properties, dict):
        return {name: _example_body(value) if isinstance(value, dict) else "TODO" for name, value in properties.items()}
    if schema.get("type") == "array":
        return []
    if schema.get("type") in {"integer", "number"}:
        return 0
    if schema.get("type") == "boolean":
        return False
    if schema.get("type") == "string":
        return "TODO"
    return {}


def _journey_slug(tcids: list[str]) -> str:
    joined = "-to-".join(tcids)
    return re.sub(r"[^a-z0-9]+", "-", joined.lower()).strip("-") or "journey"


def _js_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def _table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
