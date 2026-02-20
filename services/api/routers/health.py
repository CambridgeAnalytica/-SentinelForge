"""
Health check endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from database import AsyncSessionLocal
from schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {}

    # Check database
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    overall = (
        "healthy" if all(v == "healthy" for v in services.values()) else "degraded"
    )

    # Read version from the FastAPI app instance
    try:
        from main import app as _app

        version = _app.version
    except Exception:
        version = "unknown"

    return HealthResponse(
        status=overall,
        version=version,
        services=services,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/ready")
async def readiness():
    """Readiness probe for Kubernetes."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}


@router.get("/live")
async def liveness():
    """Liveness probe for Kubernetes."""
    return {"alive": True}
