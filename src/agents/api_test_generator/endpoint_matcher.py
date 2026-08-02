from __future__ import annotations

import json

from src.agents.prompts import ENDPOINT_MATCH_PROMPT
from src.llm_client import LLMClient
from src.schemas import GeneratedTestCase

from .models import EndpointMatch, EndpointMatchResult
from .openapi_parser import OpenAPIEndpoint


def match_endpoints(
    client: LLMClient,
    cases: list[tuple[str, GeneratedTestCase]],
    endpoints: dict[tuple[str, str], OpenAPIEndpoint],
    base_path: str,
) -> EndpointMatchResult:
    """Match all cases in one structured LLM request."""
    data = [
        {"tcid": tcid, "summary": case.summary, "description": case.description, "steps": [step.model_dump() for step in case.steps]}
        for tcid, case in cases
    ]
    catalogue = [
        {"method": endpoint.method, "path": endpoint.path, "operation_id": endpoint.operation_id, "summary": endpoint.summary}
        for endpoint in endpoints.values()
    ]
    instruction = f"{ENDPOINT_MATCH_PROMPT}\n\nAPI base path context: {base_path}."
    result = client.structured(
        step="api-endpoint-match",
        model=EndpointMatchResult,
        system=instruction,
        data=json.dumps(data, ensure_ascii=False),
        context=f"OpenAPI endpoint catalogue (data):\n{json.dumps(catalogue, ensure_ascii=False)}",
    )
    return validate_matches(result, endpoints)


def validate_matches(
    result: EndpointMatchResult,
    endpoints: dict[tuple[str, str], OpenAPIEndpoint],
) -> EndpointMatchResult:
    """Downgrade hallucinated endpoint references without rejecting the entire batch."""
    validated: list[EndpointMatch] = []
    for match in result.matches:
        key = ((match.method or "").upper(), match.path or "")
        if match.matched and key not in endpoints:
            print(f"[WARNING] LLM hallucinated endpoint for {match.tcid}, treated as unmapped")
            validated.append(match.model_copy(update={"matched": False, "method": None, "path": None, "operation_id": None, "confidence": "low"}))
        else:
            validated.append(match)
    return EndpointMatchResult(matches=validated)
