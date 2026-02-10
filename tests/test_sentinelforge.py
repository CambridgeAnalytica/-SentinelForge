"""
SentinelForge API Tests
"""

import pytest
from datetime import datetime, timezone


# ── Unit Tests ──

class TestSchemas:
    """Test Pydantic schema validation."""

    def test_login_request_valid(self):
        from services.api.schemas import LoginRequest
        req = LoginRequest(username="admin", password="secret")
        assert req.username == "admin"
        assert req.password == "secret"

    def test_attack_run_request(self):
        from services.api.schemas import AttackRunRequest
        req = AttackRunRequest(scenario_id="prompt_injection", target_model="gpt-4")
        assert req.scenario_id == "prompt_injection"
        assert req.config == {}

    def test_tool_info(self):
        from services.api.schemas import ToolInfo
        tool = ToolInfo(
            name="garak",
            version="0.9",
            category="prompt_injection",
            description="LLM vulnerability scanner",
            capabilities=["injection_detection"],
            mitre_atlas=["AML.T0051.000"],
        )
        assert tool.name == "garak"
        assert len(tool.capabilities) == 1

    def test_health_response(self):
        from services.api.schemas import HealthResponse
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            services={"database": "healthy"},
            timestamp=datetime.now(timezone.utc),
        )
        assert health.status == "healthy"


class TestToolRegistry:
    """Test tool registry loading."""

    def test_registry_loads(self):
        import yaml
        from pathlib import Path
        registry_path = Path(__file__).parent.parent / "tools" / "registry.yaml"
        if registry_path.exists():
            with open(registry_path) as f:
                registry = yaml.safe_load(f)
            assert "tools" in registry
            assert len(registry["tools"]) > 0
            for tool in registry["tools"]:
                assert "name" in tool
                assert "category" in tool
                assert "capabilities" in tool

    def test_registry_has_mitre_mapping(self):
        import yaml
        from pathlib import Path
        registry_path = Path(__file__).parent.parent / "tools" / "registry.yaml"
        if registry_path.exists():
            with open(registry_path) as f:
                registry = yaml.safe_load(f)
            for tool in registry["tools"]:
                assert "mitre_atlas" in tool, f"Tool {tool['name']} missing MITRE ATLAS mapping"
                assert len(tool["mitre_atlas"]) > 0


class TestToolExecutor:
    """Test tool executor."""

    def test_executor_init(self):
        from tools.executor import ToolExecutor
        executor = ToolExecutor()
        assert executor is not None

    def test_executor_list_tools(self):
        from tools.executor import ToolExecutor
        executor = ToolExecutor()
        tools = executor.list_tools()
        assert isinstance(tools, list)

    def test_executor_get_nonexistent_tool(self):
        from tools.executor import ToolExecutor
        executor = ToolExecutor()
        config = executor.get_tool_config("nonexistent_tool")
        assert config is None

    def test_executor_execute_nonexistent(self):
        from tools.executor import ToolExecutor
        executor = ToolExecutor()
        result = executor.execute_tool("nonexistent_tool")
        assert result["success"] is False
        assert "not found" in result["stderr"]


class TestScenarios:
    """Test scenario YAML files."""

    def test_scenarios_valid_yaml(self):
        import yaml
        from pathlib import Path
        scenarios_dir = Path(__file__).parent.parent / "scenarios"
        if scenarios_dir.exists():
            for f in scenarios_dir.glob("*.yaml"):
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                assert "id" in data, f"Scenario {f.name} missing id"
                assert "name" in data, f"Scenario {f.name} missing name"
                assert "tools" in data, f"Scenario {f.name} missing tools"


class TestPlaybooks:
    """Test playbook YAML files."""

    def test_playbooks_valid_yaml(self):
        import yaml
        from pathlib import Path
        playbooks_dir = Path(__file__).parent.parent / "playbooks"
        if playbooks_dir.exists():
            for f in playbooks_dir.glob("*.yaml"):
                with open(f) as fh:
                    data = yaml.safe_load(fh)
                assert "id" in data, f"Playbook {f.name} missing id"
                assert "name" in data, f"Playbook {f.name} missing name"
                assert "steps" in data, f"Playbook {f.name} missing steps"


class TestModelAdapters:
    """Test model adapter factory."""

    def test_get_openai_adapter(self):
        from adapters.models import get_adapter
        adapter = get_adapter("openai", api_key="test-key", model="gpt-4")
        assert adapter.provider == "openai"

    def test_get_anthropic_adapter(self):
        from adapters.models import get_adapter
        adapter = get_adapter("anthropic", api_key="test-key")
        assert adapter.provider == "anthropic"

    def test_get_unknown_adapter(self):
        from adapters.models import get_adapter
        with pytest.raises(ValueError):
            get_adapter("unknown_provider")


class TestSDK:
    """Test SDK client initialization."""

    def test_client_init(self):
        from sdk.python.sentinelforge_sdk import SentinelForgeClient
        client = SentinelForgeClient(api_url="http://localhost:8000")
        assert client.api_url == "http://localhost:8000"
        client.close()

    def test_client_context_manager(self):
        from sdk.python.sentinelforge_sdk import SentinelForgeClient
        with SentinelForgeClient() as client:
            assert client is not None
