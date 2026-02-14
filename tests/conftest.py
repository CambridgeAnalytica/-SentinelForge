"""
Shared fixtures for SentinelForge integration tests.

Sets up an in-memory SQLite database, overrides FastAPI dependencies,
and provides an async HTTP client for testing API endpoints.
"""

import os

# ── Set environment BEFORE any SentinelForge imports ──
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
os.environ.setdefault("DEFAULT_ADMIN_USERNAME", "testadmin")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "TestPassword123!@#")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SENTINELFORGE_DRY_RUN", "1")

# Note: pytest.ini sets pythonpath = ". services/api" so both
# "from services.api.schemas import X" and "from schemas import X" work.

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Now safe to import SentinelForge modules (they use relative imports like `from database import Base`)
from database import Base
from models import User, UserRole


# ── Test database engine (SQLite in-memory) ──
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)
_TestSession = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Mock user for auth dependency overrides ──
_mock_admin = User(
    id="test-admin-id",
    username="testadmin",
    hashed_password="not-a-real-hash",
    role=UserRole.ADMIN,
    is_active=True,
    created_at=datetime.now(timezone.utc),
)


async def _override_get_db():
    """Yield a test database session."""
    async with _TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _override_get_current_user():
    return _mock_admin


async def _override_require_operator():
    return _mock_admin


async def _override_require_admin():
    return _mock_admin


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables once per test session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Provide a fresh database session per test."""
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(setup_database):
    """Async HTTP client wired to the FastAPI app with dependency overrides."""
    from httpx import ASGITransport, AsyncClient

    # Import app AFTER env vars are set and sys.path is configured
    from main import app
    from database import get_db
    from middleware.auth import get_current_user, require_operator, require_admin

    # Override dependencies
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[require_operator] = _override_require_operator
    app.dependency_overrides[require_admin] = _override_require_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Cleanup overrides
    app.dependency_overrides.clear()
