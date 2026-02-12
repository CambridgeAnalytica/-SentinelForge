"""
Model Drift Detection API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models import User
from schemas import DriftBaselineRequest, DriftCompareRequest
from services.drift_service import (
    create_baseline,
    compare_to_baseline,
    list_baselines,
    get_drift_history,
)

router = APIRouter()
logger = logging.getLogger("sentinelforge.drift")


@router.post("/baseline")
async def create_drift_baseline(
    request: DriftBaselineRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a safety baseline for a model."""
    baseline = await create_baseline(
        db=db,
        model_name=request.model,
        test_suite=request.test_suite,
        user_id=user.id,
        provider=request.provider,
    )
    return {
        "id": baseline.id,
        "model": baseline.model_name,
        "test_suite": baseline.test_suite,
        "scores": baseline.scores,
        "prompt_count": baseline.prompt_count,
        "created_at": baseline.created_at.isoformat(),
    }


@router.post("/compare")
async def compare_drift(
    request: DriftCompareRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare current model behavior against a stored baseline."""
    try:
        result = await compare_to_baseline(
            db=db,
            model_name=request.model,
            baseline_id=request.baseline_id,
            user_id=user.id,
            provider=request.provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": result.id,
        "baseline_id": result.baseline_id,
        "model": result.model_name,
        "scores": result.scores,
        "deltas": result.deltas,
        "drift_detected": result.drift_detected,
        "summary": result.summary,
        "created_at": result.created_at.isoformat(),
    }


@router.get("/baselines")
async def get_baselines(
    model: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all baselines."""
    baselines = await list_baselines(db, model_name=model)
    return [
        {
            "id": b.id,
            "model": b.model_name,
            "test_suite": b.test_suite,
            "prompt_count": b.prompt_count,
            "created_at": b.created_at.isoformat(),
        }
        for b in baselines
    ]


@router.get("/history/{baseline_id}")
async def drift_history(
    baseline_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get drift comparison history for a baseline."""
    results = await get_drift_history(db, baseline_id)
    return [
        {
            "id": r.id,
            "model": r.model_name,
            "drift_detected": r.drift_detected,
            "summary": r.summary,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]
