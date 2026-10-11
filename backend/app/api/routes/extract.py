import logging

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_optional_user
from app.db.models.extraction import Extraction
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.extraction import ExtractionResponse, RateLimitStatus
from app.services.image_optimize import optimize_image
from app.services.image_validation import InvalidImageError, validate_image
from app.services.rate_limit import RateLimitExceeded, enforce_rate_limit, get_remaining_quota
from app.services.storage_r2 import upload_image
from app.services.vision_llm import extract_job_data

logger = logging.getLogger(__name__)

router = APIRouter(tags=["extract"])


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    request: Request,
    file: UploadFile,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    user_id_str = str(current_user.id) if current_user else None

    # 1. Enforce quota BEFORE spending anything on an LLM call.
    try:
        await enforce_rate_limit(db, ip=client_ip, user_id=user_id_str)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily limit of {exc.limit} extractions reached. Try again tomorrow.",
        ) from exc

    # 2. Validate the actual file content (size + real MIME type via magic bytes).
    try:
        raw_bytes = await validate_image(file)
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    media_type = file.content_type or "image/jpeg"

    # 3. Run extraction (Claude Haiku primary, GPT-4o mini fallback inside the service).
    try:
        fields, provider, raw_response = extract_job_data(raw_bytes, media_type)
    except Exception as exc:
        logger.exception("Vision LLM extraction failed (both providers)")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't reach the extraction service. Check API keys are configured, then try again.",
        ) from exc

    # 4. Signed-in only: optimize + upload to R2 + persist. Anonymous: discard the image entirely.
    if current_user is None:
        return ExtractionResponse(**fields, saved=False, image_url=None, llm_provider=provider)

    try:
        optimized_bytes, optimized_content_type = optimize_image(raw_bytes)
        image_url = upload_image(optimized_bytes, optimized_content_type, str(current_user.id))
    except Exception as exc:
        logger.exception("Image optimize/upload to R2 failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Extraction succeeded but saving the image failed. Check storage configuration.",
        ) from exc

    extraction = Extraction(
        user_id=current_user.id,
        llm_provider=provider,
        raw_llm_response=raw_response,
        image_url=image_url,
        **fields,
    )
    db.add(extraction)
    await db.commit()
    await db.refresh(extraction)

    return ExtractionResponse(
        **fields,
        id=extraction.id,
        saved=True,
        image_url=image_url,
        llm_provider=provider,
        created_at=extraction.created_at,
    )


@router.get("/rate-limit-status", response_model=RateLimitStatus)
async def rate_limit_status(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    user_id_str = str(current_user.id) if current_user else None
    return await get_remaining_quota(db, ip=client_ip, user_id=user_id_str)
