from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.rate_limit import RateLimit


class RateLimitExceeded(Exception):
    def __init__(self, limit: int, key_type: str):
        self.limit = limit
        self.key_type = key_type
        super().__init__(f"Daily limit of {limit} reached for {key_type}")


async def _increment_and_get_count(db: AsyncSession, key: str, key_type: str) -> int:
    """
    Atomic upsert: insert a fresh row at count=1, or bump the existing
    row's count by 1 for today's bucket. Returns the count AFTER incrementing.
    """
    today = date.today()
    stmt = (
        pg_insert(RateLimit)
        .values(key=key, key_type=key_type, request_date=today, count=1)
        .on_conflict_do_update(
            index_elements=["key", "key_type", "request_date"],
            set_={"count": RateLimit.count + 1},
        )
        .returning(RateLimit.count)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def enforce_rate_limit(db: AsyncSession, *, ip: str | None, user_id: str | None) -> None:
    """
    Call BEFORE the LLM request. Raises RateLimitExceeded if the caller is
    over their daily quota; otherwise records the attempt.

    Signed-in users are limited by user_id (5/day); anonymous callers are
    limited by IP (3/day). A signed-in user is never also checked by IP.
    """
    if user_id:
        key, key_type, limit = user_id, "user", settings.user_daily_limit
    else:
        key, key_type, limit = ip or "unknown", "ip", settings.anon_daily_limit

    new_count = await _increment_and_get_count(db, key, key_type)
    if new_count > limit:
        raise RateLimitExceeded(limit=limit, key_type=key_type)


async def get_remaining_quota(db: AsyncSession, *, ip: str | None, user_id: str | None) -> dict:
    """Used by GET /rate-limit-status — read-only, does not increment."""
    today = date.today()
    if user_id:
        key, key_type, limit = user_id, "user", settings.user_daily_limit
    else:
        key, key_type, limit = ip or "unknown", "ip", settings.anon_daily_limit

    result = await db.execute(
        select(RateLimit.count).where(
            RateLimit.key == key,
            RateLimit.key_type == key_type,
            RateLimit.request_date == today,
        )
    )
    used = result.scalar_one_or_none() or 0
    return {"limit": limit, "used": used, "remaining": max(limit - used, 0)}
