"""
SentinelForge API Service
Enterprise-Grade AI Security Testing & Red Teaming Platform
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine, Base
from routers import (
    health,
    auth,
    tools,
    attacks,
    reports,
    probes,
    playbooks,
    drift,
    backdoor,
    supply_chain,
    agent,
    synthetic,
    webhooks,
)
from routers import schedules, api_keys, notifications, compliance
from routers import audit as audit_router
from routers import sse as sse_router
from middleware.logging_middleware import RequestLoggingMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("sentinelforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("🚀 SentinelForge API starting up...")

    # Validate security configuration FIRST — abort before accepting traffic
    from config import validate_settings_security

    validate_settings_security()
    logger.info("✅ Security configuration validated")

    # ── OpenTelemetry ──
    try:
        from telemetry import setup_telemetry
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        setup_telemetry(settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✅ OpenTelemetry instrumentation active")
    except Exception as e:
        logger.warning(f"OpenTelemetry init skipped: {e}")

    # ── Rate Limiting ──
    try:
        if getattr(settings, "RATE_LIMIT_ENABLED", True):
            from middleware.rate_limit import limiter
            from slowapi import _rate_limit_exceeded_handler
            from slowapi.errors import RateLimitExceeded

            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            logger.info("✅ Rate limiting enabled")
    except Exception as e:
        logger.warning(f"Rate limiting init skipped: {e}")

    # Database tables: use Alembic migrations in production, auto-create in dev
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables auto-created (DEBUG mode)")
    else:
        logger.info("✅ Database ready (run 'alembic upgrade head' for migrations)")

    # Initialize Redis for token blocklist (graceful fallback to in-memory)
    from services.user_service import _init_redis

    _init_redis()

    # Initialize default admin user
    from services.user_service import ensure_admin_user

    await ensure_admin_user()
    logger.info("✅ Default admin user verified")

    yield

    # Shutdown
    logger.info("🛑 SentinelForge API shutting down...")
    await engine.dispose()


app = FastAPI(
    title="SentinelForge",
    description="Enterprise-Grade AI Security Testing & Red Teaming Platform",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Register routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(tools.router, prefix="/tools", tags=["Tools"])
app.include_router(attacks.router, prefix="/attacks", tags=["Attacks"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(probes.router, prefix="/probes", tags=["Probes"])
app.include_router(playbooks.router, prefix="/playbooks", tags=["Playbooks"])
app.include_router(drift.router, prefix="/drift", tags=["Drift Detection"])
app.include_router(backdoor.router, prefix="/backdoor", tags=["Backdoor Detection"])
app.include_router(supply_chain.router, prefix="/supply-chain", tags=["Supply Chain"])
app.include_router(agent.router, prefix="/agent", tags=["Agent Testing"])
app.include_router(synthetic.router, prefix="/synthetic", tags=["Synthetic Data"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(schedules.router, prefix="/schedules", tags=["Scheduled Scans"])
app.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])
app.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)
app.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
app.include_router(audit_router.router, prefix="/audit", tags=["Audit Log"])
app.include_router(sse_router.router, prefix="/attacks", tags=["SSE"])


# ── Prometheus metrics endpoint ──
@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Expose Prometheus metrics."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
