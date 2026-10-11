from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExtractionFields(BaseModel):
    job_title: str | None = None
    company: str | None = None
    description: str | None = None
    skills_required: list[str] | None = None
    location: str | None = None
    employment_type: str | None = None
    salary_range: str | None = None


class ExtractionResponse(ExtractionFields):
    id: UUID | None = None  # None for anonymous (never persisted) results
    saved: bool
    image_url: str | None = None
    llm_provider: str
    created_at: datetime | None = None


class ExtractionHistoryItem(ExtractionFields):
    id: UUID
    image_url: str
    llm_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class RateLimitStatus(BaseModel):
    limit: int
    used: int
    remaining: int
