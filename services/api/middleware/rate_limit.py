"""
Rate limiting middleware using SlowAPI.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _key_func(request: Request) -> str:
    """Rate limit key: use API key / JWT subject / IP address."""
    # Try X-API-Key header first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:12]}"

    # Try JWT from Authorization header
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        # Use first 20 chars of token as key (not the full token)
        return f"jwt:{auth[7:27]}"

    # Fall back to IP
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_key_func, default_limits=["100/minute"])
