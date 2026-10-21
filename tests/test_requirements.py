from jira_test_agent.jira_client import JiraStory, adf_to_text
from jira_test_agent.requirements import extract_requirements


def story(description: str, acceptance_criteria: str = "") -> JiraStory:
    return JiraStory("DEMO-1", "Login story", description, acceptance_criteria, "Story", "Medium", [], "https://example.atlassian.net/browse/DEMO-1")


def test_extract_acceptance_criteria_section():
    result = extract_requirements(story("As a user I can sign in.\n\nAcceptance Criteria:\n- Valid credentials allow login.\n- Invalid credentials are rejected."))
    assert [r.requirement_id for r in result] == ["AC-1", "AC-2"]
    assert result[0].text == "Valid credentials allow login."


def test_fallback_description_requirements():
    result = extract_requirements(story("User can save a profile.\nPassword must be validated."))
    assert result
    assert result[0].requirement_id == "REQ-1"


def test_adf_to_text():
    adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello"}]}]}
    assert "Hello" in adf_to_text(adf)
