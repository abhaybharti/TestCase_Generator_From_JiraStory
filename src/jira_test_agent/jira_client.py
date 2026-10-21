from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$", re.IGNORECASE)


class JiraError(RuntimeError):
    """Safe, user-facing Jira integration error."""


@dataclass(frozen=True)
class JiraStory:
    key: str
    summary: str
    description: str
    acceptance_criteria: str
    issue_type: str
    priority: str
    labels: list[str]
    url: str


def adf_to_text(value: object) -> str:
    """Convert Jira Cloud Atlassian Document Format JSON into readable plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := adf_to_text(item)))
    if isinstance(value, dict):
        node_type = value.get("type")
        if node_type == "text":
            return str(value.get("text", ""))
        content = value.get("content", [])
        children = adf_to_text(content)
        if node_type in {"paragraph", "heading", "listItem", "blockquote", "codeBlock"}:
            return children + ("\n" if children else "")
        if node_type in {"hardBreak"}:
            return "\n"
        return children
    return ""


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 20):
        parsed = urlparse(base_url.strip().rstrip("/"))
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("JIRA_BASE_URL must be an HTTPS URL without embedded credentials")
        if not email.strip() or not api_token.strip():
            raise ValueError("Jira email and API token are required")
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json", "User-Agent": "jira-story-test-agent/0.1"})
        retry = Retry(
            total=3, connect=3, read=2, status=3,
            backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}), respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)

    def get_story(self, issue_key: str, acceptance_criteria_field: str = "") -> JiraStory:
        if not ISSUE_KEY_RE.fullmatch(issue_key.strip()):
            raise ValueError("Issue key must look like PROJ-123")
        fields = ["summary", "description", "issuetype", "priority", "labels"]
        if acceptance_criteria_field.strip():
            if not re.fullmatch(r"customfield_\d+", acceptance_criteria_field.strip()):
                raise ValueError("Acceptance criteria field must be a Jira customfield_NNNNN key")
            fields.append(acceptance_criteria_field.strip())
        url = f"{self.base_url}/rest/api/3/issue/{issue_key.strip()}"
        try:
            response = self.session.get(url, params={"fields": ",".join(fields)}, timeout=self.timeout)
            if response.status_code == 401:
                raise JiraError("Jira authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN.")
            if response.status_code == 403:
                raise JiraError("Jira denied access. Check the account's project and issue permissions.")
            if response.status_code == 404:
                raise JiraError(f"Jira issue {issue_key} was not found or is not visible to this account.")
            response.raise_for_status()
            payload = response.json()
        except JiraError:
            raise
        except requests.RequestException as exc:
            logger.warning("Jira request failed (%s)", type(exc).__name__)
            raise JiraError("Could not retrieve the Jira issue. Check connectivity and Jira configuration.") from exc
        except ValueError as exc:
            raise JiraError("Jira returned an invalid JSON response.") from exc

        issue_fields = payload.get("fields") or {}
        custom_ac = adf_to_text(issue_fields.get(acceptance_criteria_field)) if acceptance_criteria_field else ""
        return JiraStory(
            key=payload.get("key", issue_key.strip()),
            summary=str(issue_fields.get("summary") or "").strip(),
            description=adf_to_text(issue_fields.get("description")),
            acceptance_criteria=custom_ac,
            issue_type=str((issue_fields.get("issuetype") or {}).get("name") or "Unknown"),
            priority=str((issue_fields.get("priority") or {}).get("name") or "Unspecified"),
            labels=list(issue_fields.get("labels") or []),
            url=f"{self.base_url}/browse/{payload.get('key', issue_key.strip())}",
        )
