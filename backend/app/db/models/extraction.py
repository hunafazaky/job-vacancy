import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Extraction(Base):
    """
    Only ever created for signed-in users. Anonymous extractions are returned
    to the client and never written here (see services/rate_limit.py and
    api/routes/extract.py).
    """

    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    job_title: Mapped[str | None] = mapped_column(String, nullable=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    skills_required: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String, nullable=True)

    llm_provider: Mapped[str] = mapped_column(String, nullable=False)  # 'claude-haiku' | 'gpt-4o-mini'
    raw_llm_response: Mapped[dict] = mapped_column(JSONB, nullable=False)

    image_url: Mapped[str] = mapped_column(String, nullable=False)  # Cloudflare R2 URL

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="extractions")  # noqa: F821
