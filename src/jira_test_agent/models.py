from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_id: str = Field(description="Stable source ID such as AC-1 or REQ-1")
    text: str = Field(min_length=1, description="Requirement text copied from the Jira story")
    source: Literal["acceptance_criteria", "description", "custom_field"]


class TestCase(BaseModel):
    __test__ = False  # Prevent pytest from treating this Pydantic schema as a test class.
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=5, max_length=180)
    objective: str = Field(min_length=5)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1, description="Ordered, executable manual steps")
    test_data: list[str] = Field(default_factory=list)
    expected_result: str = Field(min_length=5)
    priority: Literal["P0", "P1", "P2", "P3"]
    test_type: Literal[
        "positive", "negative", "boundary", "validation", "authorization",
        "error_handling", "usability", "compatibility", "other"
    ]
    requirement_refs: list[str] = Field(min_length=1, description="IDs from provided requirement list")
    assumptions_or_gaps: list[str] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def no_blank_steps(cls, value: list[str]) -> list[str]:
        if any(not step.strip() for step in value):
            raise ValueError("Test steps must not be blank")
        return value


class TestSuite(BaseModel):
    __test__ = False  # Prevent pytest from treating this Pydantic schema as a test class.
    model_config = ConfigDict(extra="forbid")
    test_cases: list[TestCase] = Field(min_length=1, max_length=60)
    general_gaps: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)
