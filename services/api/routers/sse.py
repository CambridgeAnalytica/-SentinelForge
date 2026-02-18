"""
Server-Sent Events endpoint for real-time attack run progress.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models import AttackRun, User

router = APIRouter()
logger = logging.getLogger("sentinelforge.sse")

TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


async def _event_generator(run_id: str, db: AsyncSession):
    """Yield SSE events as the attack run progresses."""
    while True:
        result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            yield 'event: error\ndata: {"error": "Run not found"}\n\n'
            return

        data = (
            f'{{"id": "{run.id}", '
            f'"status": "{run.status}", '
            f'"progress": {run.progress}, '
            f'"started_at": "{run.started_at.isoformat() if run.started_at else ""}", '
            f'"completed_at": "{run.completed_at.isoformat() if run.completed_at else ""}"}}'
        )
        yield f"event: progress\ndata: {data}\n\n"

        if run.status in TERMINAL_STATUSES:
            yield f"event: done\ndata: {data}\n\n"
            return

        # Expire the cached instance so next select sees fresh DB state
        await db.expire_all()
        await asyncio.sleep(1)


@router.get("/runs/{run_id}/stream")
async def stream_run_progress(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream attack run progress via Server-Sent Events."""
    # Verify run exists
    result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )

    return StreamingResponse(
        _event_generator(run_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx
        },
    )
