"""
User service: authentication, user management, token revocation.
"""

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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True)

# ---------- Token blocklist (in-memory; use Redis in production) ----------
_revoked_tokens: dict = {}  # token_hash -> expiry_timestamp
_revoked_lock = threading.Lock()


def _token_hash(token: str) -> str:
    """Hash token for storage (don't store raw tokens)."""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(token: str) -> None:
    """Add a token to the revocation blocklist."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        exp = payload.get("exp", 0)
    except JWTError:
        exp = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

    with _revoked_lock:
        _cleanup_expired()
        _revoked_tokens[_token_hash(token)] = exp


def is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked."""
    with _revoked_lock:
        return _token_hash(token) in _revoked_tokens


def _cleanup_expired():
    """Remove expired tokens from the blocklist."""
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
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, checking revocation."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # Check revocation blocklist
        if is_token_revoked(token):
            logger.info("Rejected revoked token")
            return None
        return payload
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def ensure_admin_user():
    """Create default admin user if none exists."""
    if not settings.DEFAULT_ADMIN_USERNAME or not settings.DEFAULT_ADMIN_PASSWORD:
        logger.warning("Admin credentials not configured — skipping admin user creation.")
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
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
            logger.info(f"Created default admin user: {settings.DEFAULT_ADMIN_USERNAME}")
        else:
            logger.info("Admin user already exists")

