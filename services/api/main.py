"""
SentinelForge API Service
Enterprise-Grade AI Security Testing & Red Teaming Platform
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import engine, Base
from routers import health, auth, tools, attacks, reports, probes, playbooks, drift, backdoor, supply_chain
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

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")

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
    version="1.0.0",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
