"""
User service: authentication, user management, token revocation.
"""

import hashlib
import logging
import re
import threading
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import AsyncSessionLocal
from models import User, UserRole

logger = logging.getLogger("sentinelforge.auth")
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True
)


# ---------- Token blocklist (Redis-backed with in-memory fallback) ----------

_redis_client = None
_redis_available = False


def _init_redis():
    """Initialize Redis client if REDIS_URL is configured."""
    global _redis_client, _redis_available
    if not settings.REDIS_URL:
        logger.info("REDIS_URL not set — using in-memory token blocklist")
        return
    try:
        import redis

        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected — using Redis-backed token blocklist")
    except Exception as e:
        logger.warning(
            f"Redis unavailable ({e}) — falling back to in-memory token blocklist"
        )
        _redis_client = None
        _redis_available = False


# In-memory fallback
_revoked_tokens: dict = {}  # token_hash -> expiry_timestamp
_revoked_lock = threading.Lock()

_BLOCKLIST_PREFIX = "sf:revoked:"


def _token_hash(token: str) -> str:
    """Hash token for storage (don't store raw tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(token: str) -> None:
    """Add a token to the revocation blocklist."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        exp = payload.get("exp", 0)
    except JWTError:
        exp = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

    token_key = _token_hash(token)
    ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 60)

    if _redis_available and _redis_client:
        try:
            _redis_client.setex(f"{_BLOCKLIST_PREFIX}{token_key}", ttl, "1")
            return
        except Exception as e:
            logger.warning(f"Redis write failed ({e}), falling back to in-memory")

    with _revoked_lock:
        _cleanup_expired()
        _revoked_tokens[token_key] = exp


def is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked."""
    token_key = _token_hash(token)

    if _redis_available and _redis_client:
        try:
            return _redis_client.exists(f"{_BLOCKLIST_PREFIX}{token_key}") > 0
        except Exception as e:
            logger.warning(f"Redis read failed ({e}), falling back to in-memory")

    with _revoked_lock:
        return token_key in _revoked_tokens


def _cleanup_expired():
    """Remove expired tokens from the in-memory blocklist."""
    now = datetime.now(timezone.utc).timestamp()
    expired = [h for h, exp in _revoked_tokens.items() if exp < now]
    for h in expired:
        del _revoked_tokens[h]


# ---------- Password helpers ----------

_PASSWORD_MIN_LENGTH = 12
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]).+$"
)


def validate_password_strength(password: str) -> str | None:
    """Returns an error message if the password is too weak, else None."""
    if len(password) < _PASSWORD_MIN_LENGTH:
        return f"Password must be at least {_PASSWORD_MIN_LENGTH} characters."
    if not _PASSWORD_PATTERN.match(password):
        return (
            "Password must contain at least: "
            "1 uppercase, 1 lowercase, 1 digit, and 1 special character."
        )
    return None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: int = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRATION_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, checking revocation."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Check revocation blocklist
        if is_token_revoked(token):
            logger.info("Rejected revoked token")
            return None
        return payload
    except JWTError:
        return None


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def ensure_admin_user():
    """Create default admin user if none exists."""
    if not settings.DEFAULT_ADMIN_USERNAME or not settings.DEFAULT_ADMIN_PASSWORD:
        logger.warning(
            "Admin credentials not configured — skipping admin user creation."
        )
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(
                f"Created default admin user: {settings.DEFAULT_ADMIN_USERNAME}"
            )
        else:
            logger.info("Admin user already exists")
