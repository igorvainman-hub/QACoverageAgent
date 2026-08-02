from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.agents.api_test_generator.checklist_reader import api_labeled_cases, read_checklist_cases
from src.agents.api_test_generator.endpoint_matcher import validate_matches
from src.agents.api_test_generator.models import EndpointMatch, EndpointMatchResult
from src.agents.api_test_generator.openapi_parser import OpenAPIParseError, load_openapi_json, parse_openapi
from src.agents.api_test_generator.playwright_generator import generate_playwright_files
from src.schemas import GeneratedTestCase, TestStep

HEADERS = ["TCID", "Test Summary", "Description", "Test Type", "Test Repository Path", "Label", "Action", "Data", "Expected Result"]


def test_reader_groups_multi_row_case_and_filters_api_label(tmp_path):
    checklist = tmp_path / "checklist.csv"
    rows = [
        {
            "TCID": "QA-001", "Test Summary": "Create order via API", "Description": "API order creation", "Test Type": "Manual",
            "Test Repository Path": "Project/orders", "Label": "Smoke;API", "Action": "Send request", "Data": "payload", "Expected Result": "Created",
        },
        {
            "TCID": "", "Test Summary": "", "Description": "", "Test Type": "", "Test Repository Path": "", "Label": "",
            "Action": "Read response", "Data": "", "Expected Result": "Order ID returned",
        },
    ]
    with checklist.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    cases = api_labeled_cases(read_checklist_cases(checklist))

    assert len(cases) == 1
    assert cases[0][0] == "QA-001"
    assert [step.action for step in cases[0][1].steps] == ["Send request", "Read response"]
    assert cases[0][1].labels == ["Smoke", "API"]


def test_parse_openapi_rejects_missing_required_structure():
    with pytest.raises(OpenAPIParseError, match="'info' and 'paths'"):
        parse_openapi({"openapi": "3.0.0"})


def test_parse_openapi_extracts_json_schemas():
    endpoints = parse_openapi(
        {
            "info": {"title": "Orders", "version": "1"},
            "paths": {
                "/orders": {
                    "post": {
                        "operationId": "createOrder", "tags": ["orders"],
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                        "responses": {"201": {"content": {"application/json": {"schema": {"type": "object"}}}}},
                    }
                }
            },
        }
    )
    endpoint = endpoints[("POST", "/orders")]
    assert endpoint.operation_id == "createOrder"
    assert endpoint.request_schema == {"type": "object"}
    assert endpoint.response_schema == {"type": "object"}


def test_hallucinated_endpoint_is_downgraded_to_unmapped(capsys):
    endpoints = parse_openapi({"info": {"title": "Orders", "version": "1"}, "paths": {"/orders": {"get": {"responses": {"200": {"description": "OK"}}}}}})
    result = EndpointMatchResult(matches=[EndpointMatch(tcid="QA-001", matched=True, method="POST", path="/invented", operation_id="nope", confidence="high", reasoning="Looks plausible")])

    validated = validate_matches(result, endpoints)

    match = validated.matches[0]
    assert not match.matched
    assert match.confidence == "low"
    assert match.path is None
    assert "hallucinated endpoint for QA-001" in capsys.readouterr().out


def test_remote_openapi_rejects_private_address(monkeypatch):
    monkeypatch.setattr("src.agents.api_test_generator.openapi_parser.socket.getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("169.254.169.254", 80))])

    with pytest.raises(OpenAPIParseError, match="private"):
        load_openapi_json("http://metadata.example/openapi.json")


def test_generator_uses_case_steps_path_parameters_and_request_body():
    endpoints = parse_openapi(
        {
            "info": {"title": "Orders", "version": "1"},
            "paths": {
                "/orders/{orderId}": {
                    "post": {
                        "operationId": "createOrder",
                        "tags": ["orders"],
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"quantity": {"type": "integer"}}}}}},
                        "responses": {
                            "201": {
                                "description": "Created",
                                "content": {"application/json": {"schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}}},
                            }
                        },
                    }
                }
            },
        }
    )
    case = GeneratedTestCase(summary="Create order by API", description="An order can be created", test_repository_path="orders", labels=["api"], steps=[TestStep(action="Create order", data="quantity=1", expected_result="Order is created"), TestStep(action="Read response", expected_result="Order ID is returned")])
    match = EndpointMatch(tcid="QA-001", matched=True, method="POST", path="/orders/{orderId}", operation_id="createOrder", confidence="high", reasoning="Exact match")

    output_dir = Path("automation/api")
    generation = generate_playwright_files(output_dir, {"QA-001": case}, [match], endpoints)
    test_source = generation.files[output_dir / "tests" / "qa-001.spec.ts"]
    client_source = generation.files[output_dir / "clients" / "orders.ts"]

    assert "await test.step('1. Create order'" in test_source
    assert "Expected result: Order ID is returned" in test_source
    assert "TODO: This checklist case has multiple steps" in test_source
    assert 'const pathParams: Record<string, string> = {"orderId": "TODO-orderId"};' in test_source
    assert "const requestBody = {\"quantity\": 0};" in test_source
    assert "client.createOrder(pathParams, requestBody)" in test_source
    assert "expect(responseBody).toMatchObject({ \"id\": expect.anything() });" in test_source
    assert "body?: unknown" in client_source
    assert generation.generated_tcids == frozenset({"QA-001"})
