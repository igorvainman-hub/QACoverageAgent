from __future__ import annotations

from pydantic import BaseModel, Field


class ThresholdValues(BaseModel):
    p95: int = Field(gt=0)
    p99: int = Field(gt=0)
    error_rate: float = Field(ge=0, le=1)


class ThresholdConfig(BaseModel):
    default: ThresholdValues
    by_tag: dict[str, ThresholdValues] = Field(default_factory=dict)


class EffectiveThresholds(BaseModel):
    values: ThresholdValues
    sources: list[str] = Field(default_factory=list)
    is_placeholder: bool = False
