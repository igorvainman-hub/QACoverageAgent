from __future__ import annotations

from src.schemas import GeneratedTestCase

from .models import EndpointMatch


def render_coverage_report(cases: list[tuple[str, GeneratedTestCase]], matches: list[EndpointMatch]) -> str:
    by_tcid = {match.tcid: match for match in matches}
    lines = ["# API Test Coverage Report", "", "| TCID | Summary | Matched Endpoint | Confidence | Status |", "| --- | --- | --- | --- | --- |"]
    unmapped: list[tuple[str, EndpointMatch | None]] = []
    generated = 0
    for tcid, case in cases:
        match = by_tcid.get(tcid)
        is_matched = bool(match and match.matched)
        if is_matched:
            generated += 1
        else:
            unmapped.append((tcid, match))
        endpoint = f"{match.method} {match.path}" if is_matched else "—"
        confidence = match.confidence if match else "low"
        status = "generated" if is_matched else "unmapped"
        lines.append(f"| {tcid} | {_table(case.summary)} | {endpoint} | {confidence} | {status} |")
    percent = (generated / len(cases) * 100) if cases else 0
    lines.extend(["", f"## Coverage: {generated}/{len(cases)} ({percent:.0f}%)"])
    if unmapped:
        lines.extend(["", "## Unmapped cases"])
        for tcid, match in unmapped:
            reason = match.reasoning if match else "The LLM did not return a match for this case."
            lines.append(f"- **{tcid}**: {reason}")
    return "\n".join(lines) + "\n"


def _table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
