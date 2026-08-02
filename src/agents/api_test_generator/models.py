from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EndpointMatch(BaseModel):
    tcid: str
    matched: bool
    method: str | None = None
    path: str | None = None
    operation_id: str | None = None
    confidence: Literal["high", "low"]
    reasoning: str = Field(min_length=1, max_length=300)


class EndpointMatchResult(BaseModel):
    matches: list[EndpointMatch] = Field(default_factory=list)
