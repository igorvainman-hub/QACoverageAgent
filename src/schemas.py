from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DocumentSection(BaseModel):
    path: str
    title: str
    raw_content: str


class CoverageGap(BaseModel):
    section_path: str
    scenario_description: str = Field(min_length=3, max_length=500)
    gap_type: Literal["intra_feature", "cross_feature"]
    related_features: list[str] = Field(default_factory=list)
    priority: Literal["High", "Medium", "Low"]

    @model_validator(mode="after")
    def validate_cross_feature(self) -> "CoverageGap":
        if self.gap_type == "cross_feature" and not self.related_features:
            raise ValueError("cross_feature gaps must name related_features")
        return self


class CoverageMatrixResult(BaseModel):
    covered: list[str] = Field(default_factory=list)
    gaps: list[CoverageGap] = Field(default_factory=list)


class TestStep(BaseModel):
    action: str = Field(min_length=1, max_length=500)
    data: str | None = Field(default=None, max_length=500)
    expected_result: str = Field(min_length=1, max_length=500)


class GeneratedTestCase(BaseModel):
    summary: str = Field(min_length=3, max_length=500)
    test_repository_path: str = Field(min_length=1, max_length=300)
    labels: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1, max_length=500)
    steps: list[TestStep] = Field(min_length=1)


class GeneratedTestCases(BaseModel):
    test_cases: list[GeneratedTestCase] = Field(default_factory=list)
