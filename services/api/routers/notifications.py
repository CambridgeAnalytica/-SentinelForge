"""
Notification Channels router — CRUD for Slack, email, Teams, webhook channels.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth import get_current_user, require_operator
from models import NotificationChannel, ChannelType, User
from schemas import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    NotificationTestResponse,
    VALID_CHANNEL_TYPES,
)

router = APIRouter()


@router.post(
    "/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    req: NotificationChannelCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Register a new notification channel."""
    if req.channel_type not in VALID_CHANNEL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel type. Must be one of: {', '.join(VALID_CHANNEL_TYPES)}",
        )

    # Validate channel-specific config
    _validate_channel_config(req.channel_type, req.config)

    channel = NotificationChannel(
        user_id=user.id,
        channel_type=ChannelType(req.channel_type),
        name=req.name,
        config=req.config,
        events=req.events,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    return _to_response(channel)


@router.get("/channels", response_model=List[NotificationChannelResponse])
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all notification channels for the current user."""
    result = await db.execute(
        select(NotificationChannel)
        .where(NotificationChannel.user_id == user.id)
        .order_by(NotificationChannel.created_at.desc())
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(
    channel_id: str,
    req: NotificationChannelUpdate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Update a notification channel."""
    channel = await _get_channel_or_404(channel_id, user.id, db)

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    await db.flush()
    await db.refresh(channel)
    return _to_response(channel)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification channel."""
    channel = await _get_channel_or_404(channel_id, user.id, db)
    await db.delete(channel)


@router.post("/channels/{channel_id}/test", response_model=NotificationTestResponse)
async def test_channel(
    channel_id: str,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification to a channel."""
    channel = await _get_channel_or_404(channel_id, user.id, db)

    from services.notification_service import send_test_notification

    result = await send_test_notification(channel)
    return NotificationTestResponse(
        channel_id=channel.id,
        status=result.get("status", "unknown"),
        error=result.get("error"),
    )


# ── Helpers ──


def _validate_channel_config(channel_type: str, config: dict):
    """Validate required config fields for each channel type."""
    if channel_type == "slack" and "webhook_url" not in config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack channel requires 'webhook_url' in config",
        )
    if channel_type == "email" and "to" not in config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email channel requires 'to' address in config",
        )
    if channel_type == "teams" and "webhook_url" not in config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teams channel requires 'webhook_url' in config",
        )
    if channel_type == "webhook" and "url" not in config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook channel requires 'url' in config",
        )


async def _get_channel_or_404(
    channel_id: str, user_id: str, db: AsyncSession
) -> NotificationChannel:
    result = await db.execute(
        select(NotificationChannel).where(
            NotificationChannel.id == channel_id,
            NotificationChannel.user_id == user_id,
        )
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found",
        )
    return channel


def _to_response(c: NotificationChannel) -> NotificationChannelResponse:
    return NotificationChannelResponse(
        id=c.id,
        channel_type=(
            c.channel_type.value if hasattr(c.channel_type, "value") else c.channel_type
        ),
        name=c.name,
        config=c.config or {},
        events=c.events or [],
        is_active=c.is_active,
        failure_count=c.failure_count,
        last_triggered_at=c.last_triggered_at,
        created_at=c.created_at,
    )
