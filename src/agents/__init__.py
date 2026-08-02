from .prompts import COVERAGE_ANALYSIS_PROMPT, INJECTION_RULE, OVERVIEW_PROMPT, TEST_DESIGN_PROMPT

__all__ = [
    "COVERAGE_ANALYSIS_PROMPT",
    "DEFAULT_OVERVIEW",
    "INJECTION_RULE",
    "OVERVIEW_PROMPT",
    "TEST_DESIGN_PROMPT",
    "checklist_summary",
    "design_tests",
    "find_gaps",
    "load_overview",
    "update_overview",
]


def __getattr__(name: str):
    if name in {"checklist_summary", "find_gaps"}:
        from .coverage_matrix import checklist_summary, find_gaps

        return {"checklist_summary": checklist_summary, "find_gaps": find_gaps}[name]
    if name in {"DEFAULT_OVERVIEW", "load_overview", "update_overview"}:
        from .overview import DEFAULT_OVERVIEW, load_overview, update_overview

        return {
            "DEFAULT_OVERVIEW": DEFAULT_OVERVIEW,
            "load_overview": load_overview,
            "update_overview": update_overview,
        }[name]
    if name == "design_tests":
        from .test_designer import design_tests

        return design_tests
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
