from __future__ import annotations

import re
from .jira_client import JiraStory
from .models import Requirement

AC_HEADER_RE = re.compile(r"(?:^|\s)(?:acceptance criteria|acceptance criterion|acceptance requirements|\bACs?\b)\s*:?\s*$", re.I)
BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+?)\s*$")


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]


def extract_requirements(story: JiraStory) -> list[Requirement]:
    """Extract candidate requirements deterministically; IDs are local traceability anchors."""
    requirements: list[Requirement] = []
    seen: set[str] = set()

    if story.acceptance_criteria.strip():
        candidates = _clean_lines(story.acceptance_criteria)
        for line in candidates:
            match = BULLET_RE.match(line)
            text = match.group(1) if match else line
            if text and text.lower() not in seen:
                requirements.append(Requirement(requirement_id=f"AC-{len(requirements)+1}", text=text, source="custom_field"))
                seen.add(text.lower())

    description_lines = _clean_lines(story.description)
    in_ac_section = False
    ac_lines: list[str] = []
    other_lines: list[str] = []
    for line in description_lines:
        if AC_HEADER_RE.search(line.strip("# :")):
            in_ac_section = True
            continue
        if in_ac_section and re.match(r"^#{1,6}\s+", line):
            in_ac_section = False
        if in_ac_section:
            match = BULLET_RE.match(line)
            candidate = match.group(1) if match else line
            if candidate.strip():
                ac_lines.append(candidate.strip())
        else:
            if not re.match(r"^#{1,6}\s+", line):
                other_lines.append(line)

    for text in ac_lines:
        if text.lower() not in seen:
            requirements.append(Requirement(requirement_id=f"AC-{len(requirements)+1}", text=text, source="acceptance_criteria"))
            seen.add(text.lower())

    # If no explicit AC section/custom field exists, use description lines as traceable requirements.
    if not requirements:
        candidates = []
        for line in other_lines:
            match = BULLET_RE.match(line)
            candidates.append(match.group(1) if match else line)
        for text in candidates:
            text = text.strip()
            if len(text) >= 8 and text.lower() not in seen:
                requirements.append(Requirement(requirement_id=f"REQ-{len(requirements)+1}", text=text, source="description"))
                seen.add(text.lower())

    return requirements
