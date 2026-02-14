"""
Webhook notification service.

Dispatches HMAC-signed event payloads to user-registered webhook endpoints
with retry logic and automatic disabling after consecutive failures.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger("sentinelforge.webhooks")


async def dispatch_webhook_event(
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Find all active webhooks subscribed to this event and dispatch."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from database import AsyncSessionLocal
    from models import WebhookEndpoint

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.is_active.is_(True),
                    WebhookEndpoint.failure_count < 10,
                )
            )
            endpoints = result.scalars().all()

            tasks = []
            for endpoint in endpoints:
                if event_type in (endpoint.events or []):
                    tasks.append(
                        _send_webhook_with_retry(endpoint, event_type, payload, db)
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            await db.commit()
    except Exception as e:
        logger.error(f"Webhook dispatch failed for {event_type}: {e}")


async def _send_webhook_with_retry(
    endpoint,
    event_type: str,
    payload: Dict[str, Any],
    db,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Send webhook with exponential backoff retry. Returns delivery result."""
    import httpx

    body = json.dumps(
        {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        },
        default=str,
    )

    # HMAC-SHA256 signature
    signature = hmac.new(
        endpoint.secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-SentinelForge-Event": event_type,
        "X-SentinelForge-Signature": f"sha256={signature}",
        "X-SentinelForge-Delivery": endpoint.id,
        "User-Agent": "SentinelForge-Webhook/1.4",
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    endpoint.url, content=body, headers=headers
                )
                if response.status_code < 300:
                    endpoint.failure_count = 0
                    endpoint.last_triggered_at = datetime.now(timezone.utc)
                    logger.info(
                        f"Webhook {endpoint.id} delivered {event_type} "
                        f"({response.status_code})"
                    )
                    return {
                        "status": "delivered",
                        "response_code": response.status_code,
                    }
                else:
                    logger.warning(
                        f"Webhook {endpoint.id} returned {response.status_code}"
                    )
        except Exception as e:
            logger.warning(
                f"Webhook {endpoint.id} attempt {attempt + 1} failed: {e}"
            )

        # Exponential backoff: 1s, 2s, 4s
        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    # All retries failed
    endpoint.failure_count += 1
    if endpoint.failure_count >= 10:
        endpoint.is_active = False
        logger.error(
            f"Webhook {endpoint.id} disabled after {endpoint.failure_count} failures"
        )

    return {"status": "failed", "error": "All retries exhausted"}


async def send_test_ping(endpoint) -> Dict[str, Any]:
    """Send a test ping to a webhook endpoint."""
    import httpx

    body = json.dumps(
        {
            "event": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "SentinelForge webhook test ping"},
        },
        default=str,
    )

    signature = hmac.new(
        endpoint.secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-SentinelForge-Event": "ping",
        "X-SentinelForge-Signature": f"sha256={signature}",
        "X-SentinelForge-Delivery": endpoint.id,
        "User-Agent": "SentinelForge-Webhook/1.4",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(endpoint.url, content=body, headers=headers)
            return {
                "status": "delivered" if response.status_code < 300 else "error",
                "response_code": response.status_code,
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
