"""Shared data shapes, used across pipeline stages regardless of which provider produced them."""
from typing import Literal

from pydantic import BaseModel

ClaimType = Literal["fact", "prediction", "opinion"]
VerdictLabel = Literal[
    "Verified", "Likely True", "Insufficient Evidence", "Outdated",
    "Misleading", "Disputed", "Likely False",
]
TemporalStatus = Literal["Current", "Historical", "Outdated", "Potentially Misleading"]


class Article(BaseModel):
    title: str
    date: str | None
    text: str


class Claim(BaseModel):
    claim: str
    type: ClaimType
    event_date: str | None = None


class Verdict(BaseModel):
    claim: str
    verdict: VerdictLabel
    temporal_status: TemporalStatus
    confidence: float
    explanation: str
    sources: list[str]
