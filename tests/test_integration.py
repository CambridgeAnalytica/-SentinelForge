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


# ── Schedule Endpoints ────────────────────────────────────


class TestScheduleEndpoints:
    """Test /schedules/* CRUD + trigger endpoints."""

    @pytest.mark.asyncio
    async def test_create_schedule(self, client):
        resp = await client.post(
            "/schedules",
            json={
                "name": "Weekly prompt injection scan",
                "cron_expression": "0 6 * * 1",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
                "config": {},
                "compare_drift": False,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Weekly prompt injection scan"
        assert data["cron_expression"] == "0 6 * * 1"
        assert data["is_active"] is True
        assert data["next_run_at"] is not None

    @pytest.mark.asyncio
    async def test_list_schedules(self, client):
        # Create one first
        await client.post(
            "/schedules",
            json={
                "name": "List test schedule",
                "cron_expression": "0 0 * * *",
                "scenario_id": "jailbreak",
                "target_model": "openai:gpt-4",
            },
        )
        resp = await client.get("/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_schedule(self, client):
        create_resp = await client.post(
            "/schedules",
            json={
                "name": "Get test schedule",
                "cron_expression": "30 12 * * 5",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
            },
        )
        schedule_id = create_resp.json()["id"]

        resp = await client.get(f"/schedules/{schedule_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == schedule_id
        assert resp.json()["name"] == "Get test schedule"

    @pytest.mark.asyncio
    async def test_update_schedule(self, client):
        create_resp = await client.post(
            "/schedules",
            json={
                "name": "Update test schedule",
                "cron_expression": "0 6 * * 1",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
            },
        )
        schedule_id = create_resp.json()["id"]

        resp = await client.put(
            f"/schedules/{schedule_id}",
            json={"name": "Updated schedule name", "cron_expression": "0 12 * * *"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated schedule name"
        assert data["cron_expression"] == "0 12 * * *"

    @pytest.mark.asyncio
    async def test_delete_schedule(self, client):
        create_resp = await client.post(
            "/schedules",
            json={
                "name": "Delete test schedule",
                "cron_expression": "0 6 * * 1",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
            },
        )
        schedule_id = create_resp.json()["id"]

        resp = await client.delete(f"/schedules/{schedule_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/schedules/{schedule_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_schedule(self, client):
        create_resp = await client.post(
            "/schedules",
            json={
                "name": "Trigger test schedule",
                "cron_expression": "0 6 * * 1",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
            },
        )
        schedule_id = create_resp.json()["id"]

        resp = await client.post(f"/schedules/{schedule_id}/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Schedule triggered"
        assert "run_id" in data
        assert data["schedule_id"] == schedule_id

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_cron(self, client):
        resp = await client.post(
            "/schedules",
            json={
                "name": "Bad cron",
                "cron_expression": "not-a-cron",
                "scenario_id": "prompt_injection",
                "target_model": "openai:gpt-4",
            },
        )
        assert resp.status_code == 400


# ── API Key Endpoints ─────────────────────────────────────


class TestApiKeyEndpoints:
    """Test /api-keys/* CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, client):
        resp = await client.post(
            "/api-keys",
            json={"name": "CI pipeline key", "scopes": ["read", "write"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "raw_key" in data  # Only returned on creation
        assert data["raw_key"].startswith("sf_")
        assert data["name"] == "CI pipeline key"
        assert data["scopes"] == ["read", "write"]
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiry(self, client):
        resp = await client.post(
            "/api-keys",
            json={
                "name": "Expiring key",
                "scopes": ["read"],
                "expires_in_days": 30,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client):
        # Create one first
        await client.post(
            "/api-keys",
            json={"name": "List test key", "scopes": ["read"]},
        )
        resp = await client.get("/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # raw_key should NOT appear in list responses
        for key in data:
            assert "raw_key" not in key

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, client):
        create_resp = await client.post(
            "/api-keys",
            json={"name": "Revoke test key", "scopes": ["read"]},
        )
        key_id = create_resp.json()["id"]

        resp = await client.delete(f"/api-keys/{key_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, client):
        resp = await client.delete("/api-keys/nonexistent-id")
        assert resp.status_code == 404


# ── Notification Channel Endpoints ────────────────────────


class TestNotificationEndpoints:
    """Test /notifications/channels/* CRUD + test endpoints."""

    @pytest.mark.asyncio
    async def test_create_slack_channel(self, client):
        resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "slack",
                "name": "Test Slack channel",
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx"
                },
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["channel_type"] == "slack"
        assert data["name"] == "Test Slack channel"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_email_channel(self, client):
        resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "email",
                "name": "Test email channel",
                "config": {"to": "admin@example.com"},
                "events": ["scan.completed"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["channel_type"] == "email"

    @pytest.mark.asyncio
    async def test_create_webhook_channel(self, client):
        resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "webhook",
                "name": "Test webhook channel",
                "config": {"url": "https://example.com/hook"},
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["channel_type"] == "webhook"

    @pytest.mark.asyncio
    async def test_create_slack_missing_webhook_url(self, client):
        resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "slack",
                "name": "Bad slack",
                "config": {},
                "events": ["attack.completed"],
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_channels(self, client):
        # Create one first
        await client.post(
            "/notifications/channels",
            json={
                "channel_type": "webhook",
                "name": "List test channel",
                "config": {"url": "https://example.com/list-hook"},
                "events": ["attack.completed"],
            },
        )
        resp = await client.get("/notifications/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_update_channel(self, client):
        create_resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "webhook",
                "name": "Update test channel",
                "config": {"url": "https://example.com/update-hook"},
                "events": ["attack.completed"],
            },
        )
        channel_id = create_resp.json()["id"]

        resp = await client.put(
            f"/notifications/channels/{channel_id}",
            json={"name": "Updated channel name", "is_active": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated channel name"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_channel(self, client):
        create_resp = await client.post(
            "/notifications/channels",
            json={
                "channel_type": "webhook",
                "name": "Delete test channel",
                "config": {"url": "https://example.com/delete-hook"},
                "events": ["attack.completed"],
            },
        )
        channel_id = create_resp.json()["id"]

        resp = await client.delete(f"/notifications/channels/{channel_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get("/notifications/channels")
        ids = [ch["id"] for ch in get_resp.json()]
        assert channel_id not in ids

    @pytest.mark.asyncio
    async def test_channel_not_found(self, client):
        resp = await client.put(
            "/notifications/channels/nonexistent-id",
            json={"name": "nope"},
        )
        assert resp.status_code == 404


# ── Compliance Endpoints ──────────────────────────────────


class TestComplianceEndpoints:
    """Test /compliance/* endpoints."""

    @pytest.mark.asyncio
    async def test_list_frameworks(self, client):
        resp = await client.get("/compliance/frameworks")
        assert resp.status_code == 200
        data = resp.json()
        assert "frameworks" in data
        framework_ids = [f["id"] for f in data["frameworks"]]
        assert "owasp_ml_top10" in framework_ids
        assert "nist_ai_rmf" in framework_ids
        assert "eu_ai_act" in framework_ids

    @pytest.mark.asyncio
    async def test_compliance_summary_owasp(self, client):
        resp = await client.get(
            "/compliance/summary", params={"framework": "owasp_ml_top10"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "framework" in data
        assert data["framework"] == "owasp_ml_top10"
        assert "categories" in data

    @pytest.mark.asyncio
    async def test_compliance_summary_nist(self, client):
        resp = await client.get(
            "/compliance/summary", params={"framework": "nist_ai_rmf"}
        )
        assert resp.status_code == 200
        assert resp.json()["framework"] == "nist_ai_rmf"

    @pytest.mark.asyncio
    async def test_compliance_summary_eu_ai_act(self, client):
        resp = await client.get(
            "/compliance/summary", params={"framework": "eu_ai_act"}
        )
        assert resp.status_code == 200
        assert resp.json()["framework"] == "eu_ai_act"

    @pytest.mark.asyncio
    async def test_compliance_report_html(self, client):
        resp = await client.get(
            "/compliance/report",
            params={"framework": "owasp_ml_top10", "format": "html"},
        )
        assert resp.status_code == 200
        # HTML format returns JSON summary
        data = resp.json()
        assert "framework" in data

    @pytest.mark.asyncio
    async def test_compliance_summary_invalid_framework(self, client):
        resp = await client.get(
            "/compliance/summary", params={"framework": "not_a_framework"}
        )
        # Router validates the framework and returns 400
        assert resp.status_code == 400


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

    @pytest.mark.asyncio
    async def test_schedule_not_found(self, client):
        resp = await client.get("/schedules/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_api_key_revoke_not_found(self, client):
        resp = await client.delete("/api-keys/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_notification_channel_not_found(self, client):
        resp = await client.delete("/notifications/channels/nonexistent-id")
        assert resp.status_code == 404
