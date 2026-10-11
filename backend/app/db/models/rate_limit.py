import uuid
from datetime import date as date_type

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RateLimit(Base):
    """
    One row per (key, key_type, request_date). `key` is a client IP for
    anonymous requests or a user_id string for signed-in requests.
    Checked-and-incremented atomically before any LLM call is made.
    """

    __tablename__ = "rate_limits"
    __table_args__ = (
        UniqueConstraint("key", "key_type", "request_date", name="uq_rate_limit_bucket"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    key_type: Mapped[str] = mapped_column(String, nullable=False)  # 'ip' | 'user'
    request_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
