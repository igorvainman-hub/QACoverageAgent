from __future__ import annotations

import json

from llm_client import LLMClient
from schemas import CoverageGap, GeneratedTestCases


def design_tests(client: LLMClient, gaps: list[CoverageGap], base_path: str) -> GeneratedTestCases:
    instruction = f"""
    Design manual 1..N test cases that close the given coverage gaps.

    For each gap, choose test design techniques based on its nature:
    - Boundary/numeric conditions → Equivalence Partitioning + Boundary Value Analysis.
    - Multiple conditions determining an outcome → Decision Table.
    - User-facing multi-step flows → Use Case based design.
    - Ambiguous or underspecified areas → Error Guessing.
    Combine techniques when the gap warrants it (e.g. a boundary condition inside a multi-step flow).

    Steps must be atomic: one action, one expected result per step.
    Bad: "Enter invalid card and submit form, verify error shown and order unchanged."
    Good: split into two steps — one action/expected pair for the error message, another for order state.

    Preconditions must be explicit, never implied (e.g. state exact starting status, user role, data setup).

    Gaps with priority High or Medium MUST include at least one negative or edge case test — this is not optional.
    Gaps with priority Low may be covered with a single happy-path test if that fully closes the gap.

    For gap_type "cross_feature", the test must exercise the interaction itself (e.g. state transition in one
    feature triggered by an event in another), not just the two features independently. Place such tests under
    a Test Repository Path that reflects the integration point (e.g. "{base_path}/Payment/OrderIntegration"),
    not just the primary feature's path.

    Test Repository Paths are rooted under {base_path}.
    Labels must be drawn from this fixed set where applicable: regression, negative, edge, integration, smoke.
    Do not invent new label categories.

    Return no duplicate tests within this batch."""
    return client.structured(step="3", model=GeneratedTestCases, system=instruction, data=json.dumps([g.model_dump() for g in gaps], ensure_ascii=False))



