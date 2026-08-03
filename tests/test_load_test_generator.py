from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agents.api_test_generator.openapi_parser import parse_openapi
from src.agents.api_test_generator.models import EndpointMatch, EndpointMatchResult
from src.agents.load_test_generator.k6_generator import generate_k6_journey_files
from src.agents.load_test_generator.models import EffectiveThresholds, ThresholdConfig, ThresholdValues
from src.agents.load_test_generator.pipeline import LoadTestGenerationError, run_load_test_journeys_pipeline, run_load_test_pipeline
from src.agents.load_test_generator.thresholds import thresholds_for_tags
from src.schemas import GeneratedTestCase, TestStep


def _case(summary: str = "Create order") -> GeneratedTestCase:
    return GeneratedTestCase(
        summary=summary,
        description="API journey case",
        test_repository_path="orders",
        labels=["api"],
        steps=[TestStep(action="Send request", expected_result="Order is created")],
    )


def _endpoints():
    return parse_openapi(
        {
            "info": {"title": "Orders", "version": "1"},
            "paths": {
                "/orders/{orderId}": {
                    "post": {
                        "tags": ["orders"],
                        "requestBody": {"content": {"application/json": {"schema": {"type": "object", "properties": {"quantity": {"type": "integer"}}}}}},
                        "responses": {"201": {"description": "Created"}},
                    }
                },
                "/payments": {"get": {"tags": ["payments"], "responses": {"200": {"description": "OK"}}}},
            },
        }
    )


def test_k6_generator_renders_complete_javascript_with_placeholder_thresholds():
    endpoints = _endpoints()
    threshold = EffectiveThresholds(values=ThresholdValues(p95=500, p99=1000, error_rate=0.01), sources=["default placeholder"], is_placeholder=True)
    generation = generate_k6_journey_files(
        Path("automation/load"),
        [("QA-101", _case(), endpoints[("POST", "/orders/{orderId}")]), ("QA-110", _case("Read payment"), endpoints[("GET", "/payments")])],
        base_url="https://api.example.test",
        thresholds=threshold,
        vus=50,
        duration="2m",
    )
    script = generation.files[Path("automation/load/journeys/qa-101-to-qa-110.js")]

    assert "import http from 'k6/http';" in script
    assert "PLACEHOLDER THRESHOLDS" in script
    assert "TODO-orderId" in script
    assert 'JSON.stringify({"quantity": 0})' in script
    assert "QA-110: status is 2xx" in script
    assert "extract it here" in script
    assert script.count("{") == script.count("}")
    assert "Data-dependency TODOs: 1" in generation.files[Path("automation/load/journeys/qa-101-to-qa-110.md")]


def test_thresholds_fall_back_to_default_when_no_tag_matches():
    config = ThresholdConfig(
        default=ThresholdValues(p95=500, p99=1000, error_rate=0.01),
        by_tag={"payments": ThresholdValues(p95=300, p99=700, error_rate=0.005)},
    )

    effective = thresholds_for_tags(config, ["orders"])

    assert effective.values == config.default
    assert effective.sources == ["default"]


def test_thresholds_use_minimum_across_matching_tags():
    config = ThresholdConfig(
        default=ThresholdValues(p95=500, p99=1000, error_rate=0.01),
        by_tag={
            "orders": ThresholdValues(p95=400, p99=900, error_rate=0.01),
            "payments": ThresholdValues(p95=300, p99=700, error_rate=0.005),
        },
    )

    effective = thresholds_for_tags(config, ["orders", "payments"])

    assert effective.values == ThresholdValues(p95=300, p99=700, error_rate=0.005)
    assert effective.sources == ["orders", "payments"]


def test_pipeline_rejects_missing_tcid_before_matching():
    with pytest.raises(LoadTestGenerationError, match="TCID QA-404 not found"):
        run_load_test_pipeline(
            client=object(),
            checklist_path=Path("checklist.csv"),
            openapi_source="unused.json",
            journey=["QA-404"],
            thresholds_path=None,
            vus=1,
            duration="1m",
            output_dir=Path("automation/load"),
            base_path="Project",
            dry_run=True,
            read_cases=lambda _: [("QA-101", _case())],
        )


def test_batch_pipeline_continues_after_failure_and_uses_unique_slugs():
    calls: list[tuple[list[str], str]] = []
    output: list[str] = []

    def run_journey(*, journey, slug, **kwargs):
        calls.append((journey, slug))
        if journey == ["QA_1"]:
            raise LoadTestGenerationError("TCID QA_1 could not be matched")
        return 0

    status = run_load_test_journeys_pipeline(
        journeys=[["QA_1"], ["QA-1"]],
        run_journey=run_journey,
        print_result=output.append,
    )

    assert status == 1
    assert calls == [(["QA_1"], "qa-1"), (["QA-1"], "qa-1-2")]
    assert output == [
        "✗ QA_1 — TCID QA_1 could not be matched",
        "✓ QA-1",
        "Load-test journeys: 1/2 generated successfully.",
    ]


def test_batch_pipeline_labels_dry_run_summary_as_would_generate():
    output: list[str] = []

    status = run_load_test_journeys_pipeline(
        journeys=[["QA-101"]],
        run_journey=lambda **kwargs: 0,
        print_result=output.append,
        dry_run=True,
    )

    assert status == 0
    assert output[-1] == "Load-test journeys: 1/1 would generate successfully."


def test_pipeline_warns_when_openapi_has_no_server(capsys):
    endpoints = _endpoints()
    spec = {"info": {"title": "Orders", "version": "1"}, "paths": {"/payments": {"get": {"tags": ["payments"], "responses": {"200": {"description": "OK"}}}}}}
    generated: dict[str, object] = {}

    def generate_files(*args, **kwargs):
        generated.update(kwargs)
        return SimpleNamespace(files={}, slug="qa-101")

    status = run_load_test_pipeline(
        client=object(),
        checklist_path=Path("checklist.csv"),
        openapi_source="unused.json",
        journey=["QA-101"],
        thresholds_path=None,
        vus=1,
        duration="1m",
        output_dir=Path("automation/load"),
        base_path="Project",
        dry_run=True,
        read_cases=lambda _: [("QA-101", _case())],
        load_spec=lambda _: spec,
        parse_spec=lambda _: endpoints,
        match=lambda *args: EndpointMatchResult(matches=[EndpointMatch(tcid="QA-101", matched=True, method="GET", path="/payments", confidence="high", reasoning="Exact")]),
        generate_files=generate_files,
    )

    assert status == 0
    assert generated["base_url"] == "TODO-BASE-URL"
    assert "OpenAPI spec has no servers[0].url" in capsys.readouterr().out
