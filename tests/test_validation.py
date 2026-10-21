from jira_test_agent.models import Requirement, TestCase, TestSuite
from jira_test_agent.validation import validate_suite


def test_unknown_requirement_reference_is_error():
    requirements = [Requirement(requirement_id="AC-1", text="Can login", source="acceptance_criteria")]
    suite = TestSuite(test_cases=[TestCase(
        title="Login works correctly", objective="Verify login works", steps=["Submit credentials"],
        expected_result="User is logged in", priority="P1", test_type="positive", requirement_refs=["AC-99"]
    )])
    report = validate_suite(suite, requirements)
    assert not report.passed
    assert "AC-99" in report.errors[0]
    assert report.uncovered_requirement_ids == ["AC-1"]


def test_duplicate_titles_are_warning():
    req = [Requirement(requirement_id="AC-1", text="Can login", source="acceptance_criteria")]
    case = TestCase(title="Login works correctly", objective="Verify login works", steps=["Submit credentials"], expected_result="User is logged in", priority="P1", test_type="positive", requirement_refs=["AC-1"])
    suite = TestSuite(test_cases=[case, case])
    report = validate_suite(suite, req)
    assert report.passed
    assert any("duplicate" in warning for warning in report.warnings)
