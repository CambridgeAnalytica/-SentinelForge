"""
Scoring rubric CRUD — custom pass/fail thresholds per scenario.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user, require_operator
from models import ScoringRubric, User
from schemas import ScoringRubricRequest, ScoringRubricResponse

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
