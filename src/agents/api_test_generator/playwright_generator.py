from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path

from src.schemas import GeneratedTestCase

from .models import EndpointMatch
from .openapi_parser import OpenAPIEndpoint


@dataclass(frozen=True)
class PlaywrightGeneration:
    files: dict[Path, str]
    generated_tcids: frozenset[str]


def generate_playwright_files(
    output_dir: Path,
    cases: dict[str, GeneratedTestCase],
    matches: list[EndpointMatch],
    endpoints: dict[tuple[str, str], OpenAPIEndpoint],
    security_schemes: dict[str, object] | None = None,
) -> PlaywrightGeneration:
    """Return all Playwright files; the caller owns writing them to disk."""
    matched = [match for match in matches if match.matched and match.tcid in cases and (match.method, match.path) in endpoints]
    files: dict[Path, str] = {}
    by_tag: dict[str, list[OpenAPIEndpoint]] = {}
    for match in matched:
        endpoint = endpoints[(match.method or "", match.path or "")]
        by_tag.setdefault(endpoint.tag, []).append(endpoint)

    auth_import = "../fixtures/auth" if security_schemes else "@playwright/test"
    for tag, tagged_endpoints in by_tag.items():
        client_name = _class_name(tag) + "Client"
        client_file = _slug(tag) + ".ts"
        unique_endpoints = {(_endpoint.method, _endpoint.path): _endpoint for _endpoint in tagged_endpoints}.values()
        files[output_dir / "clients" / client_file] = _client_source(client_name, unique_endpoints)
        for match in (item for item in matched if endpoints[(item.method or "", item.path or "")].tag == tag):
            endpoint = endpoints[(match.method or "", match.path or "")]
            files[output_dir / "tests" / f"{_slug(match.tcid)}.spec.ts"] = _test_source(match, cases[match.tcid], endpoint, client_name, client_file, auth_import)
    if security_schemes:
        files[output_dir / "fixtures" / "auth.ts"] = _auth_fixture(security_schemes)
    return PlaywrightGeneration(files=files, generated_tcids=frozenset(match.tcid for match in matched))


def _client_source(client_name: str, endpoints: object) -> str:
    methods = "\n\n".join(_client_method(endpoint) for endpoint in endpoints)
    return f'import {{ APIRequestContext, APIResponse }} from "@playwright/test";\n\nexport class {client_name} {{\n  constructor(private readonly request: APIRequestContext) {{}}\n\n{methods}\n}}\n'


def _client_method(endpoint: OpenAPIEndpoint) -> str:
    name = _method_name(endpoint)
    path = endpoint.path.replace("`", "\\`")
    return f'  async {name}(pathParams: Record<string, string> = {{}}, body?: unknown): Promise<APIResponse> {{\n    const path = "{path}".replace(/\\{{([^}}]+)\\}}/g, (_, key) => pathParams[key] ?? `{{${{key}}}}`);\n    return this.request.{endpoint.method.lower()}(path, body === undefined ? undefined : {{ data: body }});\n  }}'


def _test_source(match: EndpointMatch, case: GeneratedTestCase, endpoint: OpenAPIEndpoint, client_name: str, client_file: str, test_import: str) -> str:
    method = _method_name(endpoint)
    summary = case.summary.replace("\n", " ").replace("'", "\\'")
    path_params = _path_params(endpoint.path)
    request_body = _example_body(endpoint.request_schema)
    setup = []
    if path_params:
        setup.append(f"  const pathParams: Record<string, string> = {json.dumps(path_params)};")
    else:
        setup.append("  const pathParams: Record<string, string> = {};")
    if request_body is not None:
        setup.append(f"  // TODO: replace generated request data with a valid fixture for this scenario.")
        setup.append(f"  const requestBody = {json.dumps(request_body, ensure_ascii=False)};")
    call = f"client.{method}(pathParams" + (", requestBody" if request_body is not None else "") + ")"
    steps = []
    for index, step in enumerate(case.steps, start=1):
        title = _ts_string(f"{index}. {step.action}")
        data = f"    // Data: {step.data}" if step.data else "    // Data: none"
        expected = f"    // Expected result: {step.expected_result}"
        action = f"    response = await {call};" if index == 1 else "    // The API request is issued in the first checklist step."
        steps.append(f"  await test.step('{title}', async () => {{\n{data}\n{expected}\n{action}\n  }});")
    response_assertions = _response_assertions(endpoint.response_schema)
    multi_step_todo = (
        "  // TODO: This checklist case has multiple steps. Add and validate the additional API calls for the full workflow.\n"
        if len(case.steps) > 1
        else ""
    )
    return "".join(
        [
            f'import {{ test, expect }} from "{test_import}";\n',
            f'import {{ {client_name} }} from "../clients/{client_file.removesuffix(".ts")}";\n\n',
            f'// Source: {match.tcid} — {case.summary}\n',
            f"test('{summary}', async ({{ request }}) => {{\n",
            f"  const client = new {client_name}(request);\n",
            "\n".join(setup) + "\n",
            multi_step_todo,
            "  let response;\n",
            "\n".join(steps) + "\n",
            "  expect(response?.ok()).toBeTruthy();\n",
            response_assertions,
            "});\n",
        ]
    )


def _auth_fixture(security_schemes: dict[str, object]) -> str:
    names = ", ".join(f"AUTH_{_slug(name).upper()}" for name in security_schemes)
    return f'// TODO: implement authentication for OpenAPI security schemes. Required environment variables: {names}\nexport {{ test, expect }} from "@playwright/test";\n'


def _method_name(endpoint: OpenAPIEndpoint) -> str:
    return _camel(endpoint.operation_id) if endpoint.operation_id else _camel(f"{endpoint.method.lower()}_{endpoint.path}")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "default"


def _camel(value: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", value)
    first, *rest = [part for part in parts if part]
    return first[:1].lower() + first[1:] + "".join(part[:1].upper() + part[1:] for part in rest)


def _class_name(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part) or "Default"


def _path_params(path: str) -> dict[str, str]:
    return {name: f"TODO-{name}" for name in re.findall(r"\{([^}]+)\}", path)}


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


def _ts_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")


def _response_assertions(schema: dict | None) -> str:
    if not schema or not isinstance(schema.get("properties"), dict):
        return ""
    required = schema.get("required")
    names = required if isinstance(required, list) else list(schema["properties"])
    expected = {name: "expect.anything()" for name in names if isinstance(name, str)}
    if not expected:
        return ""
    rendered = ", ".join(f"{json.dumps(name)}: {value}" for name, value in expected.items())
    return f"  const responseBody = await response!.json();\n  expect(responseBody).toMatchObject({{ {rendered} }});\n"
