"""
Adversarial Fine-Tuning / Backdoor Detection API endpoints.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user
from models import User
from services.backdoor_service import scan_model, list_scans, get_scan

router = APIRouter()
logger = logging.getLogger("sentinelforge.backdoor")


@router.post("/scan")
async def run_backdoor_scan(
    model_source: str,
    scan_type: str = "behavioral",
    background_tasks: BackgroundTasks = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a backdoor detection scan on a model."""
    try:
        scan = await scan_model(
            db=db,
            model_source=model_source,
            scan_type=scan_type,
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if background_tasks:
        background_tasks.add_task(
            _dispatch_webhook,
            "scan.completed",
            {
                "scan_id": scan.id,
                "scan_type": "backdoor",
                "model_source": scan.model_source,
                "risk_level": scan.risk_level,
            },
        )

    return {
        "id": scan.id,
        "model_source": scan.model_source,
        "scan_type": scan.scan_type,
        "indicators_found": scan.indicators_found,
        "risk_level": scan.risk_level,
        "results": scan.results,
        "created_at": scan.created_at.isoformat(),
    }


async def _dispatch_webhook(event_type: str, payload: dict) -> None:
    """Background task: dispatch webhook event."""
    try:
        from services.webhook_service import dispatch_webhook_event

        await dispatch_webhook_event(event_type, payload)
    except Exception as e:
        logger.error(f"Webhook dispatch error: {e}")


@router.get("/scans")
async def list_backdoor_scans(
    model: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List backdoor scans."""
    scans = await list_scans(db, model_source=model)
    return [
        {
            "id": s.id,
            "model_source": s.model_source,
            "scan_type": s.scan_type,
            "indicators_found": s.indicators_found,
            "risk_level": s.risk_level,
            "created_at": s.created_at.isoformat(),
        }
        for s in scans
    ]


@router.get("/scans/{scan_id}")
async def get_backdoor_scan(
    scan_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific backdoor scan."""
    scan = await get_scan(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "id": scan.id,
        "model_source": scan.model_source,
        "scan_type": scan.scan_type,
        "indicators_found": scan.indicators_found,
        "risk_level": scan.risk_level,
        "results": scan.results,
        "created_at": scan.created_at.isoformat(),
    }
