"""
Audit log API — admin-only access to security-relevant event history.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import require_admin
from models import AuditLog, User

router = APIRouter()
logger = logging.getLogger("sentinelforge.audit_router")


@router.get("")
async def list_audit_logs(
    action: Optional[str] = Query(
        None, description="Filter by action (e.g. auth.login)"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries (admin only). Supports filtering by action, user, and resource."""
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)

    where_clause = and_(*filters) if filters else True

    # Total count
    count_q = select(func.count(AuditLog.id)).where(where_clause)
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch page
    q = (
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    logs = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/actions")
async def list_audit_actions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List distinct audit log actions for filter dropdowns."""
    result = await db.execute(
        select(AuditLog.action).distinct().order_by(AuditLog.action)
    )
    return {"actions": [row[0] for row in result.all()]}
