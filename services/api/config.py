"""
SentinelForge Configuration
Reads from environment variables / .env file.
"""

import sys
import logging
from typing import List
from pydantic_settings import BaseSettings

logger = logging.getLogger("sentinelforge.config")

# Known weak values that must not be used in production
_WEAK_JWT_SECRETS = {
    "dev-secret-change-in-production",
    "change-me",
    "secret",
    "dev-secret",
    "",
}
_WEAK_PASSWORDS = {"admin", "password", "123456", "changeme", ""}


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://sentinelforge_user:sentinelforge_password@localhost:5432/sentinelforge"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://sentinelforge_user:sentinelforge_password@localhost:5432/sentinelforge"
    )

    # Object Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "sentinelforge-artifacts"

    # Authentication — NO DEFAULTS for secrets; must be set via env
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30
    DEFAULT_ADMIN_USERNAME: str = ""
    DEFAULT_ADMIN_PASSWORD: str = ""

    # LLM Provider Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    DATABRICKS_HOST: str = ""
    DATABRICKS_TOKEN: str = ""
    HUGGINGFACE_API_TOKEN: str = ""

    # Redis (token blocklist, caching)
    REDIS_URL: str = ""  # e.g. redis://localhost:6379/0; empty = in-memory fallback

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    LOG_LEVEL: str = "info"
    METRICS_ENABLED: bool = True

    # Worker
    WORKER_CONCURRENCY: int = 10
    WORKER_TIMEOUT_SECONDS: int = 3600

    # Budget
    DEFAULT_TOKEN_LIMIT: int = 100000
    DEFAULT_COST_LIMIT_USD: float = 50.0

    # Tools
    TOOLS_REGISTRY_PATH: str = "tools/registry.yaml"

    # Feature Flags
    ENABLE_AGENT_TESTING: bool = True
    ENABLE_MULTI_TURN: bool = True
    ENABLE_SYNTHETIC_DATA: bool = True
    ENABLE_DRIFT_MONITORING: bool = True
    ENABLE_BACKDOOR_DETECTION: bool = True
    ENABLE_SUPPLY_CHAIN_SCAN: bool = True

    # General
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = []

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def validate_settings_security():
    """Validate security-critical settings at startup. Fails hard if misconfigured."""
    errors = []

    # JWT secret must be set and strong
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY in _WEAK_JWT_SECRETS:
        errors.append(
            "JWT_SECRET_KEY is missing or weak. Set a random 256-bit key via env var."
        )
    elif len(settings.JWT_SECRET_KEY) < 32:
        errors.append(
            f"JWT_SECRET_KEY is too short ({len(settings.JWT_SECRET_KEY)} chars). "
            "Use at least 32 characters."
        )

    # Admin credentials must be explicitly configured
    if not settings.DEFAULT_ADMIN_USERNAME:
        errors.append("DEFAULT_ADMIN_USERNAME must be set via env var.")
    if (
        not settings.DEFAULT_ADMIN_PASSWORD
        or settings.DEFAULT_ADMIN_PASSWORD in _WEAK_PASSWORDS
    ):
        errors.append(
            "DEFAULT_ADMIN_PASSWORD is missing or weak. "
            "Set a strong password (12+ chars, mixed case, numbers, symbols)."
        )
    elif len(settings.DEFAULT_ADMIN_PASSWORD) < 12:
        errors.append(
            f"DEFAULT_ADMIN_PASSWORD is too short ({len(settings.DEFAULT_ADMIN_PASSWORD)} chars). "
            "Use at least 12 characters."
        )

    # CORS must not be wildcard in production
    if not settings.DEBUG and "*" in settings.CORS_ORIGINS:
        errors.append(
            "CORS_ORIGINS contains '*' which is not allowed outside DEBUG mode. "
            "Set explicit origins like 'https://yourdomain.com'."
        )

    if errors:
        for e in errors:
            logger.critical(f"SECURITY CONFIG ERROR: {e}")
        if not settings.DEBUG:
            logger.critical("Aborting startup due to security misconfigurations.")
            sys.exit(1)
        else:
            logger.warning(
                "Running in DEBUG mode — security warnings above are non-fatal, "
                "but MUST be fixed before production."
            )
