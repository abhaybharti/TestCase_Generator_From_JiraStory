from __future__ import annotations

import csv
import json
from pathlib import Path
from .jira_client import JiraStory
from .models import Requirement, TestSuite
from .validation import ValidationReport


def export_json(path: Path, story: JiraStory, requirements: list[Requirement], suite: TestSuite, report: ValidationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "story": {
            "key": story.key, "summary": story.summary, "url": story.url,
            "issue_type": story.issue_type, "priority": story.priority,
        },
        "requirements": [r.model_dump() for r in requirements],
        "test_cases": [tc.model_dump() for tc in suite.test_cases],
        "general_gaps": suite.general_gaps,
        "coverage_notes": suite.coverage_notes,
        "validation": {
            "passed": report.passed,
            "errors": report.errors,
            "warnings": report.warnings,
            "uncovered_requirement_ids": report.uncovered_requirement_ids,
        },
        "review_status": "REQUIRES_HUMAN_REVIEW",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_csv(path: Path, suite: TestSuite) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "test_case_id", "title", "objective", "priority", "test_type", "preconditions",
        "steps", "test_data", "expected_result", "requirement_refs", "assumptions_or_gaps",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, tc in enumerate(suite.test_cases, start=1):
            writer.writerow({
                "test_case_id": f"TC-{index:03d}", "title": tc.title, "objective": tc.objective,
                "priority": tc.priority, "test_type": tc.test_type,
                "preconditions": " | ".join(tc.preconditions),
                "steps": "\n".join(f"{i}. {step}" for i, step in enumerate(tc.steps, start=1)),
                "test_data": " | ".join(tc.test_data), "expected_result": tc.expected_result,
                "requirement_refs": "; ".join(tc.requirement_refs),
                "assumptions_or_gaps": " | ".join(tc.assumptions_or_gaps),
            })
