"""
Authentication endpoints with rate limiting and token revocation.
"""

import time
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import LoginRequest, TokenResponse, UserInfo
from services.user_service import authenticate_user, create_access_token, revoke_token
from middleware.auth import get_current_user
from models import User

router = APIRouter()
logger = logging.getLogger("sentinelforge.auth")

# ---------- Rate limiting ----------
_MAX_LOGIN_ATTEMPTS = 5
_RATE_WINDOW_SECONDS = 60
_login_attempts: dict = defaultdict(list)  # IP -> [timestamp, ...]


def _check_rate_limit(client_ip: str) -> None:
    """Raise 429 if client exceeds login attempt rate limit."""
    now = time.time()
    cutoff = now - _RATE_WINDOW_SECONDS

    # Prune old entries
    _login_attempts[client_ip] = [
        ts for ts in _login_attempts[client_ip] if ts > cutoff
    ]

    if len(_login_attempts[client_ip]) >= _MAX_LOGIN_ATTEMPTS:
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {_RATE_WINDOW_SECONDS} seconds.",
        )

    _login_attempts[client_ip].append(now)


# ---------- Endpoints ----------


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    raw_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate and return JWT token (rate-limited)."""
    client_ip = raw_request.client.host if raw_request.client else "unknown"
    _check_rate_limit(client_ip)

    user = await authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token({"sub": user.id, "role": user.role.value})
    return TokenResponse(
        access_token=token,
        expires_in=1800,  # 30 minutes
    )


@router.get("/status", response_model=UserInfo)
async def auth_status(user: User = Depends(get_current_user)):
    """Get current auth status."""
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout(
    raw_request: Request,
    user: User = Depends(get_current_user),
):
    """Logout — revokes the current token server-side."""
    auth_header = raw_request.headers.get("authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if token:
        revoke_token(token)
        logger.info(f"Token revoked for user {user.username}")
    return {"message": "Successfully logged out, token revoked"}
