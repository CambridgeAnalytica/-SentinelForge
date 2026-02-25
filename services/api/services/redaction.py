"""
SentinelForge Data Redaction Layer
Scrubs sensitive data (PII, API keys, credentials) from prompts BEFORE
they are sent to external AI providers.

This module sits between the application and model adapters to ensure
no company or client data leaks to third-party APIs.
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("sentinelforge.redaction")


# ---------- Redaction patterns ----------

_REDACTION_PATTERNS: List[tuple] = [
    # API keys and tokens
    (r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]"),
    (r"api[_-]?key\s*[:=]\s*\S+", "api_key=[REDACTED]"),
    (r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", "Bearer [REDACTED_TOKEN]"),
    (r"token\s*[:=]\s*\S+", "token=[REDACTED]"),
    # Passwords and secrets
    (r"password\s*[:=]\s*\S+", "password=[REDACTED]"),
    (r"secret\s*[:=]\s*\S+", "secret=[REDACTED]"),
    # Email addresses
    (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]"),
    # IP addresses (v4)
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]"),
    # Credit card numbers (basic)
    (r"\b(?:\d{4}[\s\-]?){3}\d{4}\b", "[REDACTED_CC]"),
    # SSN
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    # Phone numbers (US format)
    (r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b", "[REDACTED_PHONE]"),
    # AWS credentials
    (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
    (
        r"aws[_\-]?secret[_\-]?access[_\-]?key\s*[:=]\s*\S+",
        "aws_secret_access_key=[REDACTED]",
    ),
    # Connection strings
    (r"(?:postgres|mysql|mongodb|redis)://\S+", "[REDACTED_CONNECTION_STRING]"),
    # Private keys
    (
        r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
        "[REDACTED_PRIVATE_KEY]",
    ),
]

# Compile patterns once for performance
_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), r) for p, r in _REDACTION_PATTERNS]


def redact_text(text: str) -> str:
    """Scrub sensitive data patterns from text.

    Returns the redacted text. Does NOT modify the original.
    """
    if not text:
        return text

    redacted = text
    for pattern, replacement in _COMPILED_PATTERNS:
        redacted = pattern.sub(replacement, redacted)

    if redacted != text:
        logger.info(
            f"Redacted {len(text) - len(redacted) + redacted.count('[REDACTED')} "
            f"sensitive patterns from text ({len(text)} chars)"
        )

    return redacted


def redact_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Redact sensitive data from a list of chat messages.

    Returns a NEW list — does not modify the original messages.
    Handles multipart content (list of text + image_url parts) for vision models.
    """
    result = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            # Multipart content (vision models): redact text parts only
            redacted_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    redacted_parts.append(
                        {**part, "text": redact_text(part.get("text", ""))}
                    )
                else:
                    redacted_parts.append(part)
            result.append({**msg, "content": redacted_parts})
        else:
            result.append({**msg, "content": redact_text(content)})
    return result


class RedactionConfig:
    """Configuration for the redaction layer."""

    def __init__(
        self,
        enabled: bool = True,
        custom_patterns: Optional[List[tuple]] = None,
        log_redactions: bool = True,
    ):
        self.enabled = enabled
        self.log_redactions = log_redactions
        self._extra_patterns = []

        if custom_patterns:
            self._extra_patterns = [
                (re.compile(p, re.IGNORECASE), r) for p, r in custom_patterns
            ]

    def redact(self, text: str) -> str:
        """Apply redaction with this config's settings."""
        if not self.enabled or not text:
            return text

        result = redact_text(text)

        # Apply custom patterns
        for pattern, replacement in self._extra_patterns:
            result = pattern.sub(replacement, result)

        return result
