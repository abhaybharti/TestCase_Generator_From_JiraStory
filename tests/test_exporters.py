import csv
import json
from jira_test_agent.exporters import export_csv, export_json
from jira_test_agent.jira_client import JiraStory
from jira_test_agent.models import Requirement, TestCase, TestSuite
from jira_test_agent.validation import validate_suite


def test_json_and_csv_export(tmp_path):
    story = JiraStory("DEMO-1", "Login", "Description", "Valid login", "Story", "Medium", [], "https://example.atlassian.net/browse/DEMO-1")
    requirements = [Requirement(requirement_id="AC-1", text="Valid login", source="custom_field")]
    suite = TestSuite(test_cases=[TestCase(
        title="Valid user can log in", objective="Verify successful login", preconditions=["User exists"],
        steps=["Open login page", "Enter valid credentials", "Select Sign in"], test_data=["valid user"],
        expected_result="User is authenticated", priority="P1", test_type="positive", requirement_refs=["AC-1"]
    )])
    report = validate_suite(suite, requirements)
    json_path, csv_path = tmp_path / "cases.json", tmp_path / "cases.csv"
    export_json(json_path, story, requirements, suite, report)
    export_csv(csv_path, suite)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["review_status"] == "REQUIRES_HUMAN_REVIEW"
    assert payload["test_cases"][0]["requirement_refs"] == ["AC-1"]
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["test_case_id"] == "TC-001"
