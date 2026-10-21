from __future__ import annotations

from dataclasses import dataclass
from .models import Requirement, TestSuite


@dataclass(frozen=True)
class ValidationReport:
    errors: list[str]
    warnings: list[str]
    uncovered_requirement_ids: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_suite(suite: TestSuite, requirements: list[Requirement]) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    known_ids = {req.requirement_id for req in requirements}
    covered_ids: set[str] = set()
    seen_titles: set[str] = set()

    for index, case in enumerate(suite.test_cases, start=1):
        title = " ".join(case.title.lower().split())
        if title in seen_titles:
            warnings.append(f"Test case {index} may duplicate another case: {case.title}")
        seen_titles.add(title)
        invalid_refs = sorted(set(case.requirement_refs) - known_ids)
        if invalid_refs:
            errors.append(f"{case.title}: unknown requirement reference(s): {', '.join(invalid_refs)}")
        covered_ids.update(set(case.requirement_refs) & known_ids)
        if len(case.steps) == 0:
            errors.append(f"{case.title}: no steps")
        if not case.expected_result.strip():
            errors.append(f"{case.title}: expected result is empty")
        if case.assumptions_or_gaps:
            warnings.append(f"{case.title}: review assumptions/gaps before execution")

    uncovered = sorted(known_ids - covered_ids)
    if uncovered:
        warnings.append("No test case references these requirements: " + ", ".join(uncovered))
    for gap in suite.general_gaps:
        warnings.append("Requirement gap: " + gap)
    return ValidationReport(errors=errors, warnings=warnings, uncovered_requirement_ids=uncovered)
