"""
Scheduled Scans router — CRUD for recurring cron-based scans.
"""

from datetime import datetime, timezone
from typing import List

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user, require_operator
from models import Schedule, User
from schemas import ScheduleCreateRequest, ScheduleUpdateRequest, ScheduleResponse

router = APIRouter()


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    req: ScheduleCreateRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scheduled scan."""
    # Validate cron expression
    try:
        croniter(req.cron_expression)
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {e}",
        )

    # Compute next run time
    now = datetime.now(timezone.utc)
    next_run = croniter(req.cron_expression, now).get_next(datetime)

    schedule = Schedule(
        name=req.name,
        cron_expression=req.cron_expression,
        scenario_id=req.scenario_id,
        target_model=req.target_model,
        config=req.config,
        compare_drift=req.compare_drift,
        baseline_id=req.baseline_id,
        next_run_at=next_run,
        user_id=user.id,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)

    return _to_response(schedule)


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all scheduled scans for the current user."""
    result = await db.execute(
        select(Schedule)
        .where(Schedule.user_id == user.id)
        .order_by(Schedule.created_at.desc())
    )
    return [_to_response(s) for s in result.scalars().all()]


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific schedule."""
    schedule = await _get_schedule_or_404(schedule_id, user.id, db)
    return _to_response(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    req: ScheduleUpdateRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule."""
    schedule = await _get_schedule_or_404(schedule_id, user.id, db)

    update_data = req.model_dump(exclude_unset=True)

    # Validate cron if changing
    if "cron_expression" in update_data:
        try:
            croniter(update_data["cron_expression"])
        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {e}",
            )
        # Recompute next run
        now = datetime.now(timezone.utc)
        schedule.next_run_at = croniter(update_data["cron_expression"], now).get_next(
            datetime
        )

    for field, value in update_data.items():
        setattr(schedule, field, value)

    schedule.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(schedule)
    return _to_response(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule."""
    schedule = await _get_schedule_or_404(schedule_id, user.id, db)
    await db.delete(schedule)


@router.post("/{schedule_id}/trigger", response_model=dict)
async def trigger_schedule(
    schedule_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a scheduled scan immediately."""
    from models import AttackRun

    schedule = await _get_schedule_or_404(schedule_id, user.id, db)

    run = AttackRun(
        scenario_id=schedule.scenario_id,
        target_model=schedule.target_model,
        config=schedule.config,
        user_id=user.id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    schedule.last_run_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "message": "Schedule triggered",
        "run_id": run.id,
        "schedule_id": schedule.id,
    }


# ── Helpers ──


async def _get_schedule_or_404(
    schedule_id: str, user_id: str, db: AsyncSession
) -> Schedule:
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )
    return schedule


def _to_response(s: Schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=s.id,
        name=s.name,
        cron_expression=s.cron_expression,
        scenario_id=s.scenario_id,
        target_model=s.target_model,
        config=s.config or {},
        is_active=s.is_active,
        compare_drift=s.compare_drift,
        baseline_id=s.baseline_id,
        last_run_at=s.last_run_at,
        next_run_at=s.next_run_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )
