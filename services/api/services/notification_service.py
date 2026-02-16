"""
Notification Service — dispatches events to multiple channel types.

Supports: webhook, Slack, email (SMTP), Microsoft Teams.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("sentinelforge.notifications")


async def dispatch_notification(
    event_type: str,
    payload: dict,
    channels: list,
) -> List[Dict[str, Any]]:
    """Dispatch a notification to all active channels subscribed to this event."""
    results = []
    for channel in channels:
        if not channel.is_active:
            continue
        events = channel.events or []
        if event_type not in events and "*" not in events:
            continue

        result = await _send_to_channel(channel, event_type, payload)
        results.append(result)

    return results


async def _send_to_channel(channel, event_type: str, payload: dict) -> Dict[str, Any]:
    """Route to the appropriate channel sender."""
    channel_type = (
        channel.channel_type.value
        if hasattr(channel.channel_type, "value")
        else channel.channel_type
    )

    sender_map = {
        "webhook": _send_webhook,
        "slack": _send_slack,
        "email": _send_email,
        "teams": _send_teams,
    }

    sender = sender_map.get(channel_type)
    if not sender:
        return {
            "channel_id": channel.id,
            "status": "error",
            "error": f"Unknown channel type: {channel_type}",
        }

    try:
        await sender(channel.config or {}, event_type, payload)
        return {"channel_id": channel.id, "status": "sent"}
    except Exception as e:
        logger.warning(f"Notification failed for channel {channel.id}: {e}")
        return {"channel_id": channel.id, "status": "error", "error": str(e)}


async def send_test_notification(channel) -> Dict[str, Any]:
    """Send a test notification to validate channel config."""
    test_payload = {
        "event": "test.notification",
        "message": "SentinelForge test notification — if you see this, the channel is configured correctly.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return await _send_to_channel(channel, "test.notification", test_payload)


# ── Channel Senders ──


async def _send_webhook(config: dict, event_type: str, payload: dict):
    """Send plain webhook POST with JSON body."""
    url = config["url"]
    headers = config.get("headers", {})
    headers.setdefault("Content-Type", "application/json")
    headers["X-SentinelForge-Event"] = event_type

    body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()


async def _send_slack(config: dict, event_type: str, payload: dict):
    """Send Slack notification via Incoming Webhook."""
    webhook_url = config["webhook_url"]
    channel = config.get("channel", "#security-alerts")

    # Format as Slack blocks for rich display
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🛡️ SentinelForge — {event_type}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": _format_payload_markdown(payload),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                }
            ],
        },
    ]

    body = {
        "channel": channel,
        "text": f"SentinelForge: {event_type}",
        "blocks": blocks,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=body)
        resp.raise_for_status()


async def _send_email(config: dict, event_type: str, payload: dict):
    """Send email notification via SMTP."""
    import smtplib
    from email.message import EmailMessage

    to = config["to"]
    subject = config.get("subject", f"SentinelForge Alert: {event_type}")

    from_email = config.get("from", "noreply@sentinelforge.io")
    smtp_host = config.get("smtp_host", "localhost")
    smtp_port = int(config.get("smtp_port", 587))
    smtp_user = config.get("smtp_user", "")
    smtp_pass = config.get("smtp_pass", "")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to
    msg.set_content(
        f"SentinelForge Alert: {event_type}\n\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )

    # HTML version
    html = f"""
    <h2>🛡️ SentinelForge Alert</h2>
    <p><strong>Event:</strong> {event_type}</p>
    <pre>{json.dumps(payload, indent=2, default=str)}</pre>
    <hr>
    <p style="color: #888; font-size: 12px;">
        Sent by SentinelForge at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
    </p>
    """
    msg.add_alternative(html, subtype="html")

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                if smtp_user:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        raise


async def _send_teams(config: dict, event_type: str, payload: dict):
    """Send Microsoft Teams notification via Incoming Webhook (Adaptive Card)."""
    webhook_url = config["webhook_url"]

    # Adaptive Card format
    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"🛡️ SentinelForge — {event_type}",
                            "weight": "bolder",
                            "size": "large",
                        },
                        {
                            "type": "TextBlock",
                            "text": _format_payload_markdown(payload),
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                            "size": "small",
                            "isSubtle": True,
                        },
                    ],
                },
            }
        ],
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=card)
        resp.raise_for_status()


def _format_payload_markdown(payload: dict) -> str:
    """Format a payload dict as readable markdown for Slack/Teams."""
    lines = []
    for key, value in payload.items():
        if isinstance(value, dict):
            value = json.dumps(value, default=str)
        lines.append(f"• **{key}**: {value}")
    return "\n".join(lines) if lines else "No data"
