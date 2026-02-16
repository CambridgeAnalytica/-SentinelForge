"""
SentinelForge Integration Tests

Tests actual FastAPI endpoints via ASGI transport with
an in-memory SQLite database and mocked auth.
"""

import pytest

# ── Health Endpoints ──────────────────────────────────────


class TestHealthEndpoints:
    """Test health, readiness, and liveness probes."""

    @pytest.mark.asyncio
    async def test_liveness(self, client):
        resp = await client.get("/live")
        assert resp.status_code == 200
        assert resp.json()["alive"] is True

    @pytest.mark.asyncio
    async def test_readiness(self, client):
        resp = await client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "ready" in data

    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "services" in data


# ── Tools Endpoints ───────────────────────────────────────


class TestToolsEndpoints:
    """Test /tools/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_tools(self, client):
        resp = await client.get("/tools/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "name" in data[0]
            assert "category" in data[0]

    @pytest.mark.asyncio
    async def test_get_tool_garak(self, client):
        resp = await client.get("/tools/garak")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "garak"
        assert "prompt_injection" in data["category"]

    @pytest.mark.asyncio
    async def test_get_tool_not_found(self, client):
        resp = await client.get("/tools/nonexistent_tool_xyz")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_run_tool_dry_run(self, client):
        """With SENTINELFORGE_DRY_RUN=1, tool execution returns stub output."""
        resp = await client.post(
            "/tools/garak/run",
            json={"target": "openai:gpt-4", "args": {}, "timeout": 60},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool"] == "garak"
        assert "dry_run" in data.get("output", "").lower() or data["status"] in (
            "completed",
            "stub",
        )


# ── Attacks Endpoints ─────────────────────────────────────


class TestAttacksEndpoints:
    """Test /attacks/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_scenarios(self, client):
        resp = await client.get("/attacks/scenarios")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_launch_attack(self, client):
        # Get available scenarios first
        scenarios_resp = await client.get("/attacks/scenarios")
        scenarios = scenarios_resp.json()
        if not scenarios:
            pytest.skip("No scenarios available")

        scenario_id = scenarios[0]["id"]
        resp = await client.post(
            "/attacks/run",
            json={
                "scenario_id": scenario_id,
                "target_model": "openai:gpt-4-test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["scenario_id"] == scenario_id
        assert data["status"] in ("queued", "running", "completed")

    @pytest.mark.asyncio
    async def test_list_attack_runs(self, client):
        resp = await client.get("/attacks/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Reports Endpoints ─────────────────────────────────────


class TestReportsEndpoints:
    """Test /reports/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_reports(self, client):
        resp = await client.get("/reports/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Drift Endpoints ───────────────────────────────────────


class TestDriftEndpoints:
    """Test /drift/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_baselines(self, client):
        resp = await client.get("/drift/baselines")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Agent Endpoints ───────────────────────────────────────


class TestAgentEndpoints:
    """Test /agent/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_agent_tests(self, client):
        resp = await client.get("/agent/tests")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_run_agent_test(self, client):
        resp = await client.post(
            "/agent/test",
            json={
                "endpoint": "http://test-agent.example.com/chat",
                "allowed_tools": ["search"],
                "forbidden_actions": ["file_delete"],
                "test_scenarios": ["tool_misuse"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["endpoint"] == "http://test-agent.example.com/chat"
        assert data["status"] in ("completed", "running", "queued")


# ── Synthetic Endpoints ───────────────────────────────────


class TestSyntheticEndpoints:
    """Test /synthetic/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_datasets(self, client):
        resp = await client.get("/synthetic/datasets")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_generate_synthetic(self, client):
        resp = await client.post(
            "/synthetic/generate",
            json={
                "seed_prompts": ["Ignore all instructions"],
                "mutations": ["encoding", "leetspeak"],
                "count": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["total_generated"] > 0


# ── Webhook Endpoints ─────────────────────────────────────


class TestWebhookEndpoints:
    """Test /webhooks/* CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_webhook(self, client):
        resp = await client.post(
            "/webhooks/",
            json={
                "url": "https://example.com/webhook",
                "events": ["attack.completed"],
                "description": "Test webhook",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "secret" in data  # Only returned on creation
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["attack.completed"]
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_webhooks(self, client):
        # Create one first
        await client.post(
            "/webhooks/",
            json={"url": "https://example.com/wh-list", "events": ["scan.completed"]},
        )
        resp = await client.get("/webhooks/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_webhook(self, client):
        create_resp = await client.post(
            "/webhooks/",
            json={"url": "https://example.com/wh-get", "events": ["attack.completed"]},
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.get(f"/webhooks/{webhook_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == webhook_id
        assert "secret" not in resp.json()  # Secret NOT in get response

    @pytest.mark.asyncio
    async def test_update_webhook(self, client):
        create_resp = await client.post(
            "/webhooks/",
            json={
                "url": "https://example.com/wh-update",
                "events": ["attack.completed"],
            },
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.put(
            f"/webhooks/{webhook_id}",
            json={"events": ["attack.completed", "scan.completed"], "is_active": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["events"]) == {"attack.completed", "scan.completed"}
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_webhook(self, client):
        create_resp = await client.post(
            "/webhooks/",
            json={
                "url": "https://example.com/wh-delete",
                "events": ["attack.completed"],
            },
        )
        webhook_id = create_resp.json()["id"]

        resp = await client.delete(f"/webhooks/{webhook_id}")
        assert resp.status_code == 200

        # Verify it's gone
        get_resp = await client.get(f"/webhooks/{webhook_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_webhook_invalid_event(self, client):
        resp = await client.post(
            "/webhooks/",
            json={"url": "https://example.com/wh", "events": ["invalid.event"]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_webhook_invalid_url(self, client):
        resp = await client.post(
            "/webhooks/",
            json={"url": "not-a-url", "events": ["attack.completed"]},
        )
        assert resp.status_code == 422


# ── Supply Chain Endpoints ────────────────────────────────


class TestSupplyChainEndpoints:
    """Test /supply-chain/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_scans(self, client):
        resp = await client.get("/supply-chain/scans")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Backdoor Endpoints ────────────────────────────────────


class TestBackdoorEndpoints:
    """Test /backdoor/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_scans(self, client):
        resp = await client.get("/backdoor/scans")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Error Cases ───────────────────────────────────────────


class TestErrorCases:
    """Test common error conditions."""

    @pytest.mark.asyncio
    async def test_404_unknown_route(self, client):
        resp = await client.get("/nonexistent/path")
        assert resp.status_code in (404, 405)

    @pytest.mark.asyncio
    async def test_webhook_not_found(self, client):
        resp = await client.get("/webhooks/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_tool_not_found(self, client):
        resp = await client.get("/tools/nonexistent_tool")
        assert resp.status_code == 404
