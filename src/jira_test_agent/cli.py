from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAIError

from .exporters import export_csv, export_json
from .generator import TestCaseGenerator
from .jira_client import JiraClient, JiraError
from .requirements import extract_requirements
from .validation import validate_suite

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate manual test cases from a Jira Cloud story.")
    parser.add_argument("issue_key", help="Jira issue key, e.g. DEMO-123")
    parser.add_argument("--format", choices=("json", "csv", "both"), default="both", help="Output format (default: both)")
    parser.add_argument("--output-dir", default="outputs", help="Directory for generated files")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and fetch story only; do not call OpenAI")
    return parser


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    key = args.issue_key.strip()
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*-\d+", key, re.IGNORECASE):
        print("ERROR: Issue key must look like PROJ-123", file=sys.stderr)
        raise SystemExit(2)

    base_url = os.getenv("JIRA_BASE_URL", "")
    jira_email = os.getenv("JIRA_EMAIL", "")
    jira_token = os.getenv("JIRA_API_TOKEN", "")
    if not all((base_url, jira_email, jira_token)):
        print("ERROR: Set JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env", file=sys.stderr)
        raise SystemExit(2)

    try:
        jira = JiraClient(
            base_url, jira_email, jira_token,
            timeout=int(os.getenv("HTTP_TIMEOUT_SECONDS", "20")),
        )
        story = jira.get_story(key, os.getenv("JIRA_ACCEPTANCE_CRITERIA_FIELD", ""))
        requirements = extract_requirements(story)
        if not story.summary:
            raise JiraError("The Jira issue has no summary; refusing to generate test cases.")
        if not requirements:
            raise JiraError("No usable requirements found. Add acceptance criteria or meaningful story description.")
        print(f"Fetched {story.key}: {story.summary}")
        print(f"Extracted {len(requirements)} candidate requirement(s).")
        if args.dry_run:
            print("Dry run successful. OpenAI was not called and no files were written.")
            return

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing from .env")
        generator = TestCaseGenerator(api_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        suite = generator.generate(story, requirements)
        report = validate_suite(suite, requirements)

        safe_key = re.sub(r"[^A-Za-z0-9_-]", "_", story.key)
        output_dir = Path(args.output_dir)
        if args.format in ("json", "both"):
            json_path = output_dir / f"{safe_key}_test_cases.json"
            export_json(json_path, story, requirements, suite, report)
            print(f"Wrote {json_path}")
        if args.format in ("csv", "both"):
            csv_path = output_dir / f"{safe_key}_test_cases.csv"
            export_csv(csv_path, suite)
            print(f"Wrote {csv_path}")

        print(f"Generated {len(suite.test_cases)} test case(s). Validation errors: {len(report.errors)}; warnings: {len(report.warnings)}.")
        print("REVIEW REQUIRED: generated cases are drafts and must be checked by a QE before use.")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
        if report.errors:
            print("ERRORS:")
            for error in report.errors:
                print(f" - {error}")
            raise SystemExit(3)
    except (JiraError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except OpenAIError as exc:
        logger.error("OpenAI request failed (%s). Check API availability, model access, and billing.", type(exc).__name__)
        raise SystemExit(4) from exc
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc


if __name__ == "__main__":
    main()
