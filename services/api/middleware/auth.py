"""
Authentication dependency for FastAPI routes.
Supports both JWT Bearer tokens and API key (X-API-Key header) authentication.
"""

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole, ApiKey
from services.user_service import decode_token

security = HTTPBearer(auto_error=False)  # Don't auto-error so we can try API key


async def _authenticate_api_key(api_key_raw: str, db: AsyncSession) -> User:
    """Authenticate via API key: hash, lookup, validate, return user."""
    key_hash = hashlib.sha256(api_key_raw.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check expiry
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Update last used
    api_key.last_used_at = datetime.now(timezone.utc)

    # Load user
    user_result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate API key or JWT and return current user.

    Priority:
    1. X-API-Key header → API key auth
    2. Authorization: Bearer <token> → JWT auth
    """
    # 1. Try API key header
    api_key_raw = request.headers.get("X-API-Key")
    if api_key_raw:
        return await _authenticate_api_key(api_key_raw, db)

    # 2. Try JWT Bearer (header or ?token= query param)
    token_str = credentials.credentials if credentials else None

    # Fallback: check query param for browser-based access (report downloads, SSE)
    if not token_str:
        token_str = request.query_params.get("token")

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication (provide Bearer token, X-API-Key, or ?token= query param)",
        )

    payload = decode_token(token_str)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return user


async def require_operator(user: User = Depends(get_current_user)) -> User:
    """Require analyst, operator, or admin role (can run tests, schedule, generate reports)."""
    if user.role not in (UserRole.ADMIN, UserRole.OPERATOR, UserRole.ANALYST):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst or admin role required",
        )
    return user
