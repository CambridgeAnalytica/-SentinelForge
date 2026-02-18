"""
SentinelForge RBAC Enforcement Tests

Verifies that VIEWER and OPERATOR roles are properly restricted
from actions that require higher privilege levels. Uses real auth
dependency enforcement instead of mocking all roles to ADMIN.
"""

import os

# ── Set environment BEFORE any SentinelForge imports ──
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long!!")
os.environ.setdefault("DEFAULT_ADMIN_USERNAME", "testadmin")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "TestPassword123!@#")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SENTINELFORGE_DRY_RUN", "1")

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database import Base
from models import User, UserRole

# ── Test database ──
_rbac_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_RBACSession = async_sessionmaker(
    _rbac_engine, class_=AsyncSession, expire_on_commit=False
)

# ── Mock users for each role ──
_mock_viewer = User(
    id="test-viewer-id",
    username="testviewer",
    hashed_password="not-a-real-hash",
    role=UserRole.VIEWER,
    is_active=True,
    created_at=datetime.now(timezone.utc),
)

_mock_operator = User(
    id="test-operator-id",
    username="testoperator",
    hashed_password="not-a-real-hash",
    role=UserRole.OPERATOR,
    is_active=True,
    created_at=datetime.now(timezone.utc),
)

_mock_admin = User(
    id="test-admin-id",
    username="testadmin",
    hashed_password="not-a-real-hash",
    role=UserRole.ADMIN,
    is_active=True,
    created_at=datetime.now(timezone.utc),
)


async def _override_get_db():
    async with _RBACSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(scope="session")
async def rbac_setup_database():
    async with _rbac_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _rbac_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _rbac_engine.dispose()


def _make_client(user: User):
    """Create a fixture-factory that returns a client with real RBAC enforcement.

    Only `get_current_user` is overridden — `require_operator` and
    `require_admin` use the real implementations which check user.role.
    """

    @pytest_asyncio.fixture
    async def _client(rbac_setup_database):
        from main import app
        from database import get_db
        from middleware.auth import get_current_user

        # Only override get_current_user — let require_operator / require_admin
        # perform real role checks against the user object we inject.
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = lambda: user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()

    return _client


client_viewer = _make_client(_mock_viewer)
client_operator = _make_client(_mock_operator)
client_admin = _make_client(_mock_admin)


# ═══════════════════════════════════════════════════════════
# VIEWER RESTRICTIONS — should be denied write operations
# ═══════════════════════════════════════════════════════════


class TestViewerRestrictions:
    """VIEWER should get 403 on all write/mutation endpoints that require operator+."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_launch_attack(self, client_viewer):
        resp = await client_viewer.post(
            "/attacks/run",
            json={
                "scenario_id": "prompt_injection",
                "target_model": "gpt-4",
                "config": {},
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_webhook(self, client_viewer):
        resp = await client_viewer.post(
            "/webhooks/",
            json={
                "url": "https://example.com/hook",
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_schedule(self, client_viewer):
        resp = await client_viewer.post(
            "/schedules",
            json={
                "name": "daily-scan",
                "cron_expression": "0 2 * * *",
                "scenario_id": "prompt_injection",
                "target_model": "gpt-4",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_notification_channel(self, client_viewer):
        resp = await client_viewer.post(
            "/notifications/channels",
            json={
                "channel_type": "slack",
                "name": "test-slack",
                "config": {"webhook_url": "https://hooks.slack.com/test"},
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════
# VIEWER READ ACCESS — should be allowed on GET endpoints
# ═══════════════════════════════════════════════════════════


class TestViewerReadAccess:
    """VIEWER should be able to read resources (GET requests)."""

    @pytest.mark.asyncio
    async def test_viewer_can_list_attack_runs(self, client_viewer):
        resp = await client_viewer.get("/attacks/runs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_tools(self, client_viewer):
        resp = await client_viewer.get("/tools/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_reports(self, client_viewer):
        resp = await client_viewer.get("/reports/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_drift_baselines(self, client_viewer):
        resp = await client_viewer.get("/drift/baselines")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_webhooks(self, client_viewer):
        resp = await client_viewer.get("/webhooks/")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_schedules(self, client_viewer):
        resp = await client_viewer.get("/schedules")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_api_keys(self, client_viewer):
        resp = await client_viewer.get("/api-keys")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_compliance_frameworks(self, client_viewer):
        resp = await client_viewer.get("/compliance/frameworks")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════
# OPERATOR RESTRICTIONS — should be denied admin-only actions
# ═══════════════════════════════════════════════════════════


class TestOperatorRestrictions:
    """OPERATOR should be rejected by the require_admin dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_rejects_operator(self):
        """require_admin raises 403 for OPERATOR role."""
        from middleware.auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=_mock_operator)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_admin_rejects_viewer(self):
        """require_admin raises 403 for VIEWER role."""
        from middleware.auth import require_admin

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(user=_mock_viewer)
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════
# OPERATOR WRITE ACCESS — should be allowed on operator endpoints
# ═══════════════════════════════════════════════════════════


class TestOperatorWriteAccess:
    """OPERATOR should be able to perform write operations on non-admin endpoints."""

    @pytest.mark.asyncio
    async def test_operator_can_launch_attack(self, client_operator):
        resp = await client_operator.post(
            "/attacks/run",
            json={
                "scenario_id": "prompt_injection",
                "target_model": "gpt-4",
                "config": {},
            },
        )
        # Not 403 = operator passed RBAC; 200/202 = accepted, 404 = scenario not found in test env
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_operator_can_create_webhook(self, client_operator):
        resp = await client_operator.post(
            "/webhooks/",
            json={
                "url": "https://example.com/hook",
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_operator_can_create_schedule(self, client_operator):
        resp = await client_operator.post(
            "/schedules",
            json={
                "name": "daily-scan",
                "cron_expression": "0 2 * * *",
                "scenario_id": "prompt_injection",
                "target_model": "gpt-4",
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_operator_can_create_notification_channel(self, client_operator):
        resp = await client_operator.post(
            "/notifications/channels",
            json={
                "channel_type": "slack",
                "name": "test-slack",
                "config": {"webhook_url": "https://hooks.slack.com/test"},
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 201
