from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models.extraction import Extraction
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.extraction import ExtractionHistoryItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[ExtractionHistoryItem])
async def list_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Extraction)
        .where(Extraction.user_id == current_user.id)
        .order_by(Extraction.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{extraction_id}", response_model=ExtractionHistoryItem)
async def get_extraction(
    extraction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Extraction).where(
            Extraction.id == extraction_id, Extraction.user_id == current_user.id
        )
    )
    extraction = result.scalar_one_or_none()
    if extraction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return extraction


@router.delete("/{extraction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_extraction(
    extraction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(Extraction).where(
            Extraction.id == extraction_id, Extraction.user_id == current_user.id
        )
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
