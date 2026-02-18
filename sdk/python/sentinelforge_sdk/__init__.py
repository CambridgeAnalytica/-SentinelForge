"""
SentinelForge Python SDK
For authoring custom probes and interacting with the API.
"""

from typing import List
import httpx


class SentinelForgeClient:
    """Python SDK client for SentinelForge API."""

    def __init__(self, api_url: str = "http://localhost:8000", token: str = None):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(
            base_url=self.api_url,
            timeout=60,
            headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    def login(self, username: str, password: str) -> str:
        """Authenticate and store token."""
        response = self._client.post(
            "/auth/login", json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self._client.headers["Authorization"] = f"Bearer {self.token}"
        return self.token

    # ── Tools ──
    def list_tools(self) -> List[dict]:
        return self._client.get("/tools/").json()

    def get_tool(self, name: str) -> dict:
        return self._client.get(f"/tools/{name}").json()

    def run_tool(
        self, name: str, target: str, args: dict = None, timeout: int = 600
    ) -> dict:
        return self._client.post(
            f"/tools/{name}/run",
            json={"target": target, "args": args or {}, "timeout": timeout},
        ).json()

    # ── Attacks ──
    def list_scenarios(self) -> List[dict]:
        return self._client.get("/attacks/scenarios").json()

    def run_attack(
        self, scenario_id: str, target_model: str, config: dict = None
    ) -> dict:
        return self._client.post(
            "/attacks/run",
            json={
                "scenario_id": scenario_id,
                "target_model": target_model,
                "config": config or {},
            },
        ).json()

    def get_run(self, run_id: str) -> dict:
        return self._client.get(f"/attacks/runs/{run_id}").json()

    def list_runs(self) -> List[dict]:
        return self._client.get("/attacks/runs").json()

    # ── Reports ──
    def generate_report(self, run_id: str, formats: List[str] = None) -> List[dict]:
        return self._client.post(
            "/reports/generate",
            json={
                "run_id": run_id,
                "formats": formats or ["html"],
            },
        ).json()

    def list_reports(self) -> List[dict]:
        return self._client.get("/reports/").json()

    # ── Probes ──
    def list_probes(self) -> List[dict]:
        return self._client.get("/probes/").json()

    def run_probe(
        self, probe_name: str, target_model: str, config: dict = None
    ) -> dict:
        return self._client.post(
            "/probes/run",
            json={
                "probe_name": probe_name,
                "target_model": target_model,
                "config": config or {},
            },
        ).json()

    # ── Playbooks ──
    def list_playbooks(self) -> List[dict]:
        return self._client.get("/playbooks/").json()

    def run_playbook(self, playbook_id: str, context: dict = None) -> dict:
        return self._client.post(
            f"/playbooks/{playbook_id}/run",
            json={
                "playbook_id": playbook_id,
                "context": context or {},
            },
        ).json()

    # ── Webhooks ──
    def list_webhooks(self) -> List[dict]:
        return self._client.get("/webhooks/").json()

    def create_webhook(
        self, url: str, events: List[str] = None, description: str = None
    ) -> dict:
        return self._client.post(
            "/webhooks/",
            json={
                "url": url,
                "events": events or ["attack.completed"],
                "description": description,
            },
        ).json()

    def get_webhook(self, webhook_id: str) -> dict:
        return self._client.get(f"/webhooks/{webhook_id}").json()

    def update_webhook(
        self,
        webhook_id: str,
        url: str = None,
        events: List[str] = None,
        is_active: bool = None,
        description: str = None,
    ) -> dict:
        payload = {}
        if url is not None:
            payload["url"] = url
        if events is not None:
            payload["events"] = events
        if is_active is not None:
            payload["is_active"] = is_active
        if description is not None:
            payload["description"] = description
        return self._client.put(f"/webhooks/{webhook_id}", json=payload).json()

    def delete_webhook(self, webhook_id: str) -> dict:
        return self._client.delete(f"/webhooks/{webhook_id}").json()

    def test_webhook(self, webhook_id: str) -> dict:
        return self._client.post(f"/webhooks/{webhook_id}/test").json()

    # ── Schedules ──
    def list_schedules(self) -> List[dict]:
        return self._client.get("/schedules").json()

    def create_schedule(
        self,
        name: str,
        cron_expression: str,
        scenario_id: str,
        target_model: str,
        config: dict = None,
        compare_drift: bool = False,
        baseline_id: str = None,
    ) -> dict:
        payload = {
            "name": name,
            "cron_expression": cron_expression,
            "scenario_id": scenario_id,
            "target_model": target_model,
            "config": config or {},
            "compare_drift": compare_drift,
        }
        if baseline_id:
            payload["baseline_id"] = baseline_id
        return self._client.post("/schedules", json=payload).json()

    def get_schedule(self, schedule_id: str) -> dict:
        return self._client.get(f"/schedules/{schedule_id}").json()

    def update_schedule(self, schedule_id: str, **kwargs) -> dict:
        return self._client.put(f"/schedules/{schedule_id}", json=kwargs).json()

    def delete_schedule(self, schedule_id: str) -> None:
        resp = self._client.delete(f"/schedules/{schedule_id}")
        resp.raise_for_status()

    def trigger_schedule(self, schedule_id: str) -> dict:
        return self._client.post(f"/schedules/{schedule_id}/trigger").json()

    # ── API Keys ──
    def list_api_keys(self) -> List[dict]:
        return self._client.get("/api-keys").json()

    def create_api_key(
        self,
        name: str,
        scopes: List[str] = None,
        expires_in_days: int = None,
    ) -> dict:
        payload = {"name": name, "scopes": scopes or ["read", "write"]}
        if expires_in_days is not None:
            payload["expires_in_days"] = expires_in_days
        return self._client.post("/api-keys", json=payload).json()

    def revoke_api_key(self, key_id: str) -> None:
        resp = self._client.delete(f"/api-keys/{key_id}")
        resp.raise_for_status()

    # ── Compliance ──
    def list_compliance_frameworks(self) -> dict:
        return self._client.get("/compliance/frameworks").json()

    def get_compliance_summary(self, framework: str) -> dict:
        return self._client.get(
            "/compliance/summary", params={"framework": framework}
        ).json()

    def download_compliance_report(
        self, framework: str, format: str = "pdf"
    ) -> bytes:
        resp = self._client.get(
            "/compliance/report",
            params={"framework": framework, "format": format},
        )
        resp.raise_for_status()
        return resp.content

    # ── Notification Channels ──
    def list_notification_channels(self) -> List[dict]:
        return self._client.get("/notifications/channels").json()

    def create_notification_channel(
        self,
        channel_type: str,
        name: str,
        config: dict = None,
        events: List[str] = None,
    ) -> dict:
        return self._client.post(
            "/notifications/channels",
            json={
                "channel_type": channel_type,
                "name": name,
                "config": config or {},
                "events": events or ["attack.completed"],
            },
        ).json()

    def update_notification_channel(
        self, channel_id: str, **kwargs
    ) -> dict:
        return self._client.put(
            f"/notifications/channels/{channel_id}", json=kwargs
        ).json()

    def delete_notification_channel(self, channel_id: str) -> None:
        resp = self._client.delete(f"/notifications/channels/{channel_id}")
        resp.raise_for_status()

    def test_notification_channel(self, channel_id: str) -> dict:
        return self._client.post(
            f"/notifications/channels/{channel_id}/test"
        ).json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ProbeBase:
    """Base class for custom probes.

    Subclass this to create your own probes:

        class MyProbe(ProbeBase):
            name = "my_probe"
            description = "My custom probe"

            def execute(self, target, config):
                # Your testing logic here
                return {"passed": True, "findings": []}
    """

    name: str = "unnamed_probe"
    description: str = ""
    category: str = "custom"
    version: str = "1.0.0"

    def execute(self, target: str, config: dict = None) -> dict:
        """Execute the probe. Override in subclass."""
        raise NotImplementedError("Subclass must implement execute()")

    def validate_config(self, config: dict) -> bool:
        """Validate config before execution. Override if needed."""
        return True
