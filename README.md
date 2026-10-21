# Jira Story-to-Test-Case AI Agent

A Python CLI that reads a Jira Cloud issue, extracts candidate requirements, asks an OpenAI model for structured manual test cases, validates requirement traceability, and exports JSON and/or CSV. It never writes back to Jira. All generated cases are marked as requiring human review.

## Architecture

1. **Jira adapter** reads summary, description, issue type, priority, labels, and optionally a configured acceptance-criteria custom field using Jira Cloud REST API v3.
2. **Requirement extraction** creates local IDs (`AC-1`, `AC-2`, or fallback `REQ-1`) so tests can point to source text. These are traceability anchors, not Jira-native IDs.
3. **LLM generation** uses OpenAI's Responses API structured parsing with a Pydantic schema.
4. **Deterministic validation** catches unknown requirement references, missing coverage, and duplicate titles. This is not a guarantee that a test is semantically correct.
5. **Export** writes JSON and CSV drafts. No Jira test-management write API is called.

## Requirements

- Python 3.11+
- Jira Cloud account with permission to view the target issue
- Atlassian API token for basic-auth personal scripts (or replace the adapter with OAuth 2.0 for a shared/production integration)
- OpenAI API key and model access; API usage may incur charges

## Windows PowerShell setup

```powershell
cd jira-test-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

If PowerShell blocks activation, use `\.venv\Scripts\python.exe` directly or follow your organization's execution-policy guidance; do not weaken system policy just for this project.

## Configure secrets

Edit `.env` locally. Do not commit it or paste its values into tickets or chat. `.gitignore` excludes it.

- `OPENAI_API_KEY`: create an API key in your OpenAI platform account.
- `JIRA_BASE_URL`: e.g. `https://company.atlassian.net` (HTTPS required).
- `JIRA_EMAIL`: Atlassian account email for the token.
- `JIRA_API_TOKEN`: create an Atlassian API token with the least privileges needed to read issues.
- `JIRA_ACCEPTANCE_CRITERIA_FIELD`: optional Jira custom field key such as `customfield_10016`. Leave blank if acceptance criteria live in the description.
- `OPENAI_MODEL`: default `gpt-4o-mini`; set a model available to your account that supports structured outputs.

For production deployments, use a secret manager, rotate tokens, use a dedicated least-privilege Jira service account, and prefer OAuth 2.0 (3LO) or an app integration over long-lived user tokens where appropriate. Never log credentials or full authorization headers.

## Run

Fetch story and inspect requirement extraction without calling OpenAI or writing files:

```powershell
jira-test-agent DEMO-123 --dry-run
```

Generate both formats:

```powershell
jira-test-agent DEMO-123 --format both
```

Only JSON or CSV:

```powershell
jira-test-agent DEMO-123 --format json --output-dir outputs
jira-test-agent DEMO-123 --format csv --output-dir outputs
```

Example output filenames: `outputs/DEMO-123_test_cases.json` and `outputs/DEMO-123_test_cases.csv`.

## Tests

```powershell
pytest
```

Tests use local sample data and do not call Jira or OpenAI. For a quality gate in CI, also run:

```powershell
ruff check src tests
pytest --cov=jira_test_agent --cov-report=term-missing
```

## What the validator checks

- Every reference in a generated case must match a requirement ID extracted from the story.
- Which requirements have no linked test case.
- Duplicate normalized test titles (warning only).
- Assumptions and requirement gaps (warnings for review).

**Important:** a schema-valid response can still contain incorrect assumptions or weak scenarios. Human review and a representative evaluation dataset are mandatory before relying on output in delivery workflows.

## Known limitations / next hardening steps

- Requirement extraction is intentionally simple. Stories with tables, complex ADF layouts, unusual headings, or acceptance criteria in comments need a project-specific parser.
- The optional custom-field value may use ADF or plain text; both are handled, but confirm the correct field key for your Jira instance.
- The first version reads one issue and exports drafts only. It does not create Jira/Xray/Zephyr test records.
- No semantic duplicate detector, prompt-injection classifier, audit database, web service, SSO, or per-project policy layer is included yet.
- Before enterprise rollout: add offline evaluation cases and scoring, token/cost budgets, telemetry with PII redaction, dependency pinning/SBOM, CI security scanning, access controls, and OAuth/secret-manager integration.
