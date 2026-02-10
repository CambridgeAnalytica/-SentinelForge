"""
SentinelForge Python SDK
For authoring custom probes and interacting with the API.
"""

from typing import Dict, Any, List, Optional
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
        response = self._client.post("/auth/login", json={"username": username, "password": password})
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

    def run_tool(self, name: str, target: str, args: dict = None, timeout: int = 600) -> dict:
        return self._client.post(f"/tools/{name}/run", json={"target": target, "args": args or {}, "timeout": timeout}).json()

    # ── Attacks ──
    def list_scenarios(self) -> List[dict]:
        return self._client.get("/attacks/scenarios").json()

    def run_attack(self, scenario_id: str, target_model: str, config: dict = None) -> dict:
        return self._client.post("/attacks/run", json={
            "scenario_id": scenario_id,
            "target_model": target_model,
            "config": config or {},
        }).json()

    def get_run(self, run_id: str) -> dict:
        return self._client.get(f"/attacks/runs/{run_id}").json()

    def list_runs(self) -> List[dict]:
        return self._client.get("/attacks/runs").json()

    # ── Reports ──
    def generate_report(self, run_id: str, formats: List[str] = None) -> List[dict]:
        return self._client.post("/reports/generate", json={
            "run_id": run_id,
            "formats": formats or ["html"],
        }).json()

    def list_reports(self) -> List[dict]:
        return self._client.get("/reports/").json()

    # ── Probes ──
    def list_probes(self) -> List[dict]:
        return self._client.get("/probes/").json()

    def run_probe(self, probe_name: str, target_model: str, config: dict = None) -> dict:
        return self._client.post("/probes/run", json={
            "probe_name": probe_name,
            "target_model": target_model,
            "config": config or {},
        }).json()

    # ── Playbooks ──
    def list_playbooks(self) -> List[dict]:
        return self._client.get("/playbooks/").json()

    def run_playbook(self, playbook_id: str, context: dict = None) -> dict:
        return self._client.post(f"/playbooks/{playbook_id}/run", json={
            "playbook_id": playbook_id,
            "context": context or {},
        }).json()

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
