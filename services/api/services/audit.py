"""
SentinelForge Audit Log Service
Writes security-relevant events to the AuditLog table.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog

logger = logging.getLogger("sentinelforge.audit")


async def log_event(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Write an audit log entry for a security-relevant action.

    Actions include:
    - auth.login, auth.login_failed, auth.logout
    - attack.launch, attack.complete, attack.failed
    - tool.execute, tool.execute_failed
    - report.generate
    - admin.user_created
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
        logger.debug(
            f"Audit: {action} by user={user_id} on {resource_type}/{resource_id}"
        )
    except Exception as e:
        # Audit logging should never crash the application
        logger.error(f"Failed to write audit log: {e}")
