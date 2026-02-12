"""
Synthetic Adversarial Data Generator API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models import User
from schemas import SyntheticGenRequest, SyntheticGenResponse
from services.synthetic_service import generate_dataset, list_datasets, get_dataset

router = APIRouter()
logger = logging.getLogger("sentinelforge.synthetic")


@router.post("/generate", response_model=SyntheticGenResponse)
async def generate_synthetic_data(
    request: SyntheticGenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a synthetic adversarial prompt dataset."""
    logger.info(
        f"Synthetic generation: {request.count} prompts, "
        f"mutations={request.mutations}, by {user.username}"
    )
    dataset = await generate_dataset(
        db=db,
        seed_prompts=request.seed_prompts,
        mutations=request.mutations,
        count=request.count,
        user_id=user.id,
    )
    samples = dataset.results.get("samples", [])[:10] if dataset.results else []
    return SyntheticGenResponse(
        id=dataset.id,
        status=dataset.status.value,
        total_generated=dataset.total_generated,
        mutations_applied=dataset.mutations_applied or [],
        samples=samples,
        created_at=dataset.created_at,
    )


@router.get("/datasets")
async def list_synthetic_datasets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List generated synthetic datasets."""
    datasets = await list_datasets(db)
    return [
        {
            "id": d.id,
            "seed_count": d.seed_count,
            "total_generated": d.total_generated,
            "mutations_applied": d.mutations_applied,
            "status": d.status.value,
            "created_at": d.created_at.isoformat(),
        }
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}", response_model=SyntheticGenResponse)
async def get_synthetic_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific synthetic dataset."""
    dataset = await get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    samples = dataset.results.get("samples", [])[:10] if dataset.results else []
    return SyntheticGenResponse(
        id=dataset.id,
        status=dataset.status.value,
        total_generated=dataset.total_generated,
        mutations_applied=dataset.mutations_applied or [],
        samples=samples,
        created_at=dataset.created_at,
    )
