"""
Webhook endpoint management — CRUD + test ping.
"""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import WebhookEndpoint, User
from schemas import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    WebhookResponse,
    WebhookCreatedResponse,
    WebhookTestResponse,
    VALID_WEBHOOK_EVENTS,
)
from middleware.auth import get_current_user, require_operator

router = APIRouter()
logger = logging.getLogger("sentinelforge.webhooks")


@router.post("/", response_model=WebhookCreatedResponse)
async def create_webhook(
    request: WebhookCreateRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Register a new webhook endpoint."""
    # Validate event types
    invalid = set(request.events) - VALID_WEBHOOK_EVENTS
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event types: {invalid}. "
            f"Valid: {sorted(VALID_WEBHOOK_EVENTS)}",
        )

    # Validate URL
    if not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="URL must start with http(s)://")

    secret = secrets.token_hex(32)
    webhook = WebhookEndpoint(
        user_id=user.id,
        url=request.url,
        events=request.events,
        secret=secret,
        description=request.description,
    )
    db.add(webhook)
    await db.flush()

    logger.info(f"Created webhook {webhook.id} for {request.url}")

    return WebhookCreatedResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events or [],
        is_active=True,
        description=webhook.description,
        failure_count=0,
        created_at=webhook.created_at,
        secret=secret,
    )


@router.get("/", response_model=list[WebhookResponse])
async def list_webhooks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all webhooks for the current user."""
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.user_id == user.id)
        .order_by(WebhookEndpoint.created_at.desc())
    )
    webhooks = result.scalars().all()
    return [
        WebhookResponse(
            id=w.id,
            url=w.url,
            events=w.events or [],
            is_active=w.is_active,
            description=w.description,
            failure_count=w.failure_count,
            last_triggered_at=w.last_triggered_at,
            created_at=w.created_at,
        )
        for w in webhooks
    ]


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific webhook."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events or [],
        is_active=webhook.is_active,
        description=webhook.description,
        failure_count=webhook.failure_count,
        last_triggered_at=webhook.last_triggered_at,
        created_at=webhook.created_at,
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if request.events is not None:
        invalid = set(request.events) - VALID_WEBHOOK_EVENTS
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid event types: {invalid}",
            )
        webhook.events = request.events

    if request.url is not None:
        if not request.url.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=422, detail="URL must start with http(s)://"
            )
        webhook.url = request.url

    if request.is_active is not None:
        webhook.is_active = request.is_active
        if request.is_active:
            webhook.failure_count = 0  # Reset on re-enable

    if request.description is not None:
        webhook.description = request.description

    await db.flush()
    logger.info(f"Updated webhook {webhook_id}")

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events or [],
        is_active=webhook.is_active,
        description=webhook.description,
        failure_count=webhook.failure_count,
        last_triggered_at=webhook.last_triggered_at,
        created_at=webhook.created_at,
    )


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    await db.flush()
    logger.info(f"Deleted webhook {webhook_id}")
    return {"detail": "Webhook deleted"}


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Send a test ping to a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.user_id == user.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    from services.webhook_service import send_test_ping

    ping_result = await send_test_ping(webhook)

    return WebhookTestResponse(
        webhook_id=webhook.id,
        status=ping_result["status"],
        response_code=ping_result.get("response_code"),
        error=ping_result.get("error"),
    )
