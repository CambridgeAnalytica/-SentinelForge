"""
SentinelForge Tool Executor
Wraps BlackICE tools with unified execution, timeout, and sandboxing.

Supports:
- Dry-run mode (SENTINELFORGE_DRY_RUN=1) — returns stub output without subprocess
- Tool-specific adapters (garak, promptfoo) for argument mapping
- target_arg override per tool (e.g., garak uses --model_type/--model_name)
- default_args merge from registry.yaml
"""

import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

logger = logging.getLogger("sentinelforge.executor")

# Patterns that must never appear in user-supplied argument values
_DANGEROUS_PATTERNS = re.compile(
    r"[;&|`$\(\)\{\}!<>]"  # shell metacharacters
    r"|\.\./"  # path traversal
    r"|/etc/"  # system paths
    r"|/proc/"
    r"|/dev/"
    r"|~/"  # home directory expansion
)
_MAX_ARG_KEY_LEN = 64
_MAX_ARG_VALUE_LEN = 1024
_MAX_ARGS_COUNT = 20
_VALID_ARG_KEY = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def _sanitize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize user-supplied tool arguments.

    Raises ValueError on any suspicious input.
    """
    if not args:
        return {}

    if len(args) > _MAX_ARGS_COUNT:
        raise ValueError(
            f"Too many arguments ({len(args)}). Maximum is {_MAX_ARGS_COUNT}."
        )

    sanitized = {}
    for key, value in args.items():
        # Validate key format
        key_str = str(key)
        if not _VALID_ARG_KEY.match(key_str):
            raise ValueError(
                f"Invalid argument key '{key_str}'. "
                "Keys must start with a letter and contain only letters, digits, hyphens, underscores."
            )
        if len(key_str) > _MAX_ARG_KEY_LEN:
            raise ValueError(f"Argument key '{key_str[:20]}...' is too long.")

        # Validate value
        value_str = str(value)
        if len(value_str) > _MAX_ARG_VALUE_LEN:
            raise ValueError(
                f"Argument value for '{key_str}' is too long ({len(value_str)} chars)."
            )
        if _DANGEROUS_PATTERNS.search(value_str):
            raise ValueError(
                f"Argument value for '{key_str}' contains forbidden characters."
            )

        sanitized[key_str] = value

    return sanitized


def _dry_run_result(
    tool_name: str, target: str, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Return a stub result for dry-run mode (no actual subprocess execution)."""
    logger.info(f"DRY RUN: {tool_name} target={target} args={args}")
    import json

    stub_output = json.dumps(
        {
            "dry_run": True,
            "tool": tool_name,
            "target": target,
            "args": {k: str(v) for k, v in args.items()} if args else {},
            "message": f"Dry-run mode — {tool_name} was NOT executed. "
            "Set SENTINELFORGE_DRY_RUN=0 to run for real.",
        }
    )
    return {
        "success": True,
        "stdout": stub_output,
        "stderr": "",
        "duration": 0.0,
        "return_code": 0,
    }


class ToolExecutor:
    """Execute BlackICE tools in isolated virtual environments."""

    def __init__(self, registry_path: str = None):
        self._registry = None
        self._registry_path = registry_path or self._find_registry()

    def _find_registry(self) -> str:
        """Find the registry.yaml file."""
        candidates = [
            Path("tools/registry.yaml"),
            Path("/app/tools/registry.yaml"),
            Path(__file__).parent / "registry.yaml",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return str(candidates[-1])

    @property
    def registry(self) -> dict:
        if self._registry is None:
            try:
                with open(self._registry_path) as f:
                    self._registry = yaml.safe_load(f)
            except FileNotFoundError:
                logger.error(f"Registry not found at {self._registry_path}")
                self._registry = {"tools": []}
        return self._registry

    def list_tools(self) -> list:
        """List all registered tools."""
        return [t["name"] for t in self.registry.get("tools", [])]

    def get_tool_config(self, tool_name: str) -> Optional[dict]:
        """Get config for a specific tool."""
        for tool in self.registry.get("tools", []):
            if tool["name"] == tool_name:
                return tool
        return None

    def execute_tool(
        self,
        tool_name: str,
        target: str = "",
        args: Dict[str, Any] = None,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """Execute a tool and return results.

        Args:
            tool_name: Name of the tool from registry
            target: Target model or endpoint
            args: Additional arguments (will be sanitized)
            timeout: Max execution time in seconds

        Returns:
            Dict with success, stdout, stderr, duration, return_code
        """
        tool_config = self.get_tool_config(tool_name)
        if not tool_config:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool '{tool_name}' not found in registry",
                "duration": 0.0,
                "return_code": -1,
            }

        # Sanitize user-supplied arguments BEFORE building the command
        try:
            safe_args = _sanitize_args(args) if args else {}
        except ValueError as e:
            logger.warning(f"Argument sanitization failed for {tool_name}: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Invalid arguments: {e}",
                "duration": 0.0,
                "return_code": -1,
            }

        # Sanitize target
        if target and _DANGEROUS_PATTERNS.search(target):
            return {
                "success": False,
                "stdout": "",
                "stderr": "Target contains forbidden characters.",
                "duration": 0.0,
                "return_code": -1,
            }

        # Merge default_args from registry (user args take precedence)
        default_args = tool_config.get("default_args", {})
        if default_args:
            merged = dict(default_args)
            merged.update(safe_args)
            safe_args = merged

        # --- Dry-run mode ---
        if os.environ.get("SENTINELFORGE_DRY_RUN", "").lower() in ("1", "true", "yes"):
            return _dry_run_result(tool_name, target, safe_args)

        # --- Tool-specific adapters ---
        adapter_result = self._try_adapter(tool_name, tool_config, target, safe_args)
        if adapter_result is not None:
            cmd, extra_cleanup = adapter_result
        else:
            extra_cleanup = None
            cmd = self._build_base_command(tool_config, tool_name)
            # Add target using tool-specific target_arg (or default --target)
            if target:
                target_arg = tool_config.get("target_arg", "--target")
                cmd.extend([target_arg, target])
            # Add sanitized args
            self._append_args(cmd, safe_args, tool_config)

        logger.info(f"Executing: {' '.join(cmd)}")
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(__file__).parent),
                env=self._build_env(tool_config),
            )
            duration = time.time() - start_time

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": round(duration, 2),
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"Tool {tool_name} timed out after {timeout}s")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool execution timed out after {timeout} seconds",
                "duration": round(duration, 2),
                "return_code": -1,
            }

        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Tool '{tool_name}' binary not found. "
                f"Install via: {tool_config.get('install_command', 'N/A')}",
                "duration": 0.0,
                "return_code": -1,
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "duration": round(duration, 2),
                "return_code": -1,
            }

        finally:
            # Clean up temp files from adapters
            if extra_cleanup:
                try:
                    Path(extra_cleanup).unlink(missing_ok=True)
                except Exception:
                    pass

    # ── Helper methods ──────────────────────────────────────

    def _build_base_command(self, tool_config: dict, tool_name: str) -> List[str]:
        """Build the base command (executable path) for a tool."""
        venv_path = Path(tool_config.get("venv", ""))
        cli_cmd = tool_config.get("cli", tool_name)

        if venv_path.exists():
            if (venv_path / "bin" / cli_cmd).exists():
                return [str(venv_path / "bin" / cli_cmd)]
            elif (venv_path / "Scripts" / f"{cli_cmd}.exe").exists():
                return [str(venv_path / "Scripts" / f"{cli_cmd}.exe")]
            else:
                return [str(venv_path / "bin" / "python"), "-m", cli_cmd]
        return [cli_cmd]

    def _append_args(
        self, cmd: List[str], safe_args: Dict[str, Any], tool_config: dict
    ) -> None:
        """Append sanitized arguments to the command list."""
        if not safe_args:
            return
        allowed_keys = set(tool_config.get("allowed_args", []))
        for key, value in safe_args.items():
            if allowed_keys and key not in allowed_keys:
                logger.warning(
                    f"Skipping disallowed arg '{key}' for tool {tool_config.get('name')}"
                )
                continue
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            elif isinstance(value, list):
                cmd.extend([f"--{key}", ",".join(str(v) for v in value)])
            else:
                cmd.extend([f"--{key}", str(value)])

    def _try_adapter(
        self,
        tool_name: str,
        tool_config: dict,
        target: str,
        safe_args: Dict[str, Any],
    ) -> Optional[tuple]:
        """Try to use a tool-specific adapter for command building.

        Returns (cmd_list, cleanup_path) if adapter handled it, None otherwise.
        """
        if tool_name == "garak":
            try:
                from tools.garak_adapter import build_garak_args
            except ImportError:
                return None

            base_cmd = self._build_base_command(tool_config, tool_name)
            default_probes = tool_config.get("probes", [])
            adapter_args = build_garak_args(target, safe_args, default_probes)
            return base_cmd + adapter_args, None

        if tool_name == "promptfoo":
            try:
                from tools.promptfoo_adapter import (
                    build_promptfoo_config,
                    build_promptfoo_args,
                )
            except ImportError:
                return None

            base_cmd = self._build_base_command(tool_config, tool_name)
            config_path = build_promptfoo_config(target, safe_args)
            adapter_args = build_promptfoo_args(config_path)
            return base_cmd + adapter_args, config_path

        return None

    def _build_env(self, tool_config: dict) -> dict:
        """Build environment for tool execution."""
        env = os.environ.copy()
        # Pass through API keys
        for key in [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "HUGGINGFACE_API_TOKEN",
        ]:
            if key in os.environ:
                env[key] = os.environ[key]
        return env


if __name__ == "__main__":
    # Quick test
    executor = ToolExecutor()
    print(f"Available tools: {executor.list_tools()}")
    for name in executor.list_tools():
        config = executor.get_tool_config(name)
        print(
            f"  {name} v{config.get('version', '?')} - {config.get('description', '')}"
        )
