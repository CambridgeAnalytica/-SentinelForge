"""
Scoring rubric CRUD + scoring calibration pipeline.
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, AsyncSessionLocal
from middleware.auth import get_current_user, require_operator, require_admin
from models import ScoringRubric, CalibrationRun, RunStatus, User
from schemas import (
    ScoringRubricRequest,
    ScoringRubricResponse,
    CalibrationRequest,
    CalibrationResponse,
    CalibrationDetail,
)

router = APIRouter()
logger = logging.getLogger("sentinelforge.scoring")


@router.get("/rubrics", response_model=list[ScoringRubricResponse])
async def list_rubrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all scoring rubrics."""
    result = await db.execute(
        select(ScoringRubric).order_by(ScoringRubric.created_at.desc())
    )
    rubrics = result.scalars().all()
    return [
        ScoringRubricResponse(
            id=r.id,
            name=r.name,
            rules=r.rules or {},
            is_default=r.is_default,
            created_at=r.created_at,
        )
        for r in rubrics
    ]


@router.post("/rubrics", response_model=ScoringRubricResponse, status_code=201)
async def create_rubric(
    request: ScoringRubricRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom scoring rubric."""
    # If marking as default, unset existing defaults
    if request.is_default:
        result = await db.execute(
            select(ScoringRubric).where(ScoringRubric.is_default.is_(True))
        )
        for existing in result.scalars().all():
            existing.is_default = False

    rubric = ScoringRubric(
        name=request.name,
        rules=request.rules,
        is_default=request.is_default,
        user_id=user.id,
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)

    logger.info(f"Rubric '{rubric.name}' created by {user.username}")
    return ScoringRubricResponse(
        id=rubric.id,
        name=rubric.name,
        rules=rubric.rules or {},
        is_default=rubric.is_default,
        created_at=rubric.created_at,
    )


@router.put("/rubrics/{rubric_id}", response_model=ScoringRubricResponse)
async def update_rubric(
    rubric_id: str,
    request: ScoringRubricRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a scoring rubric."""
    result = await db.execute(
        select(ScoringRubric).where(ScoringRubric.id == rubric_id)
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    # If marking as default, unset existing defaults
    if request.is_default and not rubric.is_default:
        others = await db.execute(
            select(ScoringRubric).where(
                ScoringRubric.is_default.is_(True),
                ScoringRubric.id != rubric_id,
            )
        )
        for existing in others.scalars().all():
            existing.is_default = False

    rubric.name = request.name
    rubric.rules = request.rules
    rubric.is_default = request.is_default
    await db.commit()

    return ScoringRubricResponse(
        id=rubric.id,
        name=rubric.name,
        rules=rubric.rules or {},
        is_default=rubric.is_default,
        created_at=rubric.created_at,
    )


@router.delete("/rubrics/{rubric_id}", status_code=204)
async def delete_rubric(
    rubric_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Delete a scoring rubric."""
    result = await db.execute(
        select(ScoringRubric).where(ScoringRubric.id == rubric_id)
    )
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")

    await db.delete(rubric)
    await db.commit()
    logger.info(f"Rubric '{rubric.name}' deleted by {user.username}")


# ── Scoring Calibration ──────────────────────────────────────────────


@router.post("/calibrate", response_model=CalibrationResponse, status_code=201)
async def start_calibration(
    request: CalibrationRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch a scoring calibration run against a target model."""
    cal = CalibrationRun(
        target_model=request.target_model,
        status=RunStatus.QUEUED,
        config=request.config,
        user_id=user.id,
    )
    db.add(cal)
    await db.commit()
    await db.refresh(cal)

    logger.info(
        f"Calibration '{cal.id}' queued for {request.target_model} by {user.username}"
    )

    # Launch in background (non-blocking)
    asyncio.create_task(
        _run_calibration_async(cal.id, request.target_model, request.config)
    )

    return CalibrationResponse(
        id=cal.id,
        target_model=cal.target_model,
        status=cal.status.value,
        progress=cal.progress,
        created_at=cal.created_at,
    )


@router.get("/calibrations", response_model=list[CalibrationResponse])
async def list_calibrations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all calibration runs."""
    result = await db.execute(
        select(CalibrationRun).order_by(CalibrationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        CalibrationResponse(
            id=r.id,
            target_model=r.target_model,
            status=r.status.value if hasattr(r.status, "value") else r.status,
            progress=r.progress or 0.0,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/calibrations/{cal_id}", response_model=CalibrationDetail)
async def get_calibration(
    cal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed calibration results including ROC curve."""
    result = await db.execute(select(CalibrationRun).where(CalibrationRun.id == cal_id))
    cal = result.scalar_one_or_none()
    if not cal:
        raise HTTPException(status_code=404, detail="Calibration run not found")

    results = cal.results or {}
    return CalibrationDetail(
        id=cal.id,
        target_model=cal.target_model,
        status=cal.status.value if hasattr(cal.status, "value") else cal.status,
        progress=cal.progress or 0.0,
        created_at=cal.created_at,
        metrics=results.get("metrics", {}).get("recommended_threshold", {}),
        confusion_matrix=results.get("confusion_matrix", {}),
        roc_curve=results.get("roc_curve", []),
        recommended_threshold=cal.recommended_threshold,
        per_indicator_stats=results.get("per_indicator_stats", []),
        completed_at=cal.completed_at,
    )


@router.post("/calibrations/{cal_id}/apply", status_code=200)
async def apply_calibration(
    cal_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Apply a calibration's recommended threshold as the default scoring rubric (admin only)."""
    result = await db.execute(select(CalibrationRun).where(CalibrationRun.id == cal_id))
    cal = result.scalar_one_or_none()
    if not cal:
        raise HTTPException(status_code=404, detail="Calibration run not found")
    if not cal.recommended_threshold:
        raise HTTPException(
            status_code=400, detail="Calibration has no recommended threshold"
        )

    # Find or create default rubric
    rub_result = await db.execute(
        select(ScoringRubric).where(ScoringRubric.is_default.is_(True))
    )
    default_rubric = rub_result.scalar_one_or_none()

    if default_rubric:
        rules = default_rubric.rules or {}
        rules["default_threshold"] = cal.recommended_threshold
        default_rubric.rules = rules
    else:
        default_rubric = ScoringRubric(
            name="Auto-Calibrated",
            rules={"default_threshold": cal.recommended_threshold},
            is_default=True,
            user_id=user.id,
        )
        db.add(default_rubric)

    await db.commit()
    logger.info(
        f"Applied calibration threshold {cal.recommended_threshold} by {user.username}"
    )
    return {
        "message": f"Default threshold updated to {cal.recommended_threshold}",
        "rubric_id": default_rubric.id,
    }


async def _run_calibration_async(cal_id: str, target_model: str, config: dict):
    """Background task: run calibration and update DB."""
    async with AsyncSessionLocal() as db:
        try:
            # Set running
            result = await db.execute(
                select(CalibrationRun).where(CalibrationRun.id == cal_id)
            )
            cal = result.scalar_one_or_none()
            if not cal:
                return
            cal.status = RunStatus.RUNNING
            await db.commit()

            # Progress callback
            async def on_prompt_done(progress: float):
                result2 = await db.execute(
                    select(CalibrationRun).where(CalibrationRun.id == cal_id)
                )
                c = result2.scalar_one_or_none()
                if c:
                    c.progress = progress
                    await db.commit()

            from services.calibration_service import run_calibration

            results = await run_calibration(target_model, config, on_prompt_done)

            # Update with results
            result3 = await db.execute(
                select(CalibrationRun).where(CalibrationRun.id == cal_id)
            )
            cal = result3.scalar_one_or_none()
            if cal:
                cal.status = RunStatus.COMPLETED
                cal.progress = 1.0
                cal.results = results
                cal.recommended_threshold = results.get("recommended_threshold")
                cal.completed_at = datetime.now(timezone.utc)
                await db.commit()

            logger.info(
                f"Calibration '{cal_id}' completed — threshold={results.get('recommended_threshold')}"
            )

        except Exception as e:
            logger.error(f"Calibration '{cal_id}' failed: {e}")
            try:
                result4 = await db.execute(
                    select(CalibrationRun).where(CalibrationRun.id == cal_id)
                )
                cal = result4.scalar_one_or_none()
                if cal:
                    cal.status = RunStatus.FAILED
                    cal.results = {"error": str(e)}
                    cal.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass
