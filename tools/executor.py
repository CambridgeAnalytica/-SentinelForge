"""
SentinelForge Tool Executor
Wraps BlackICE tools with unified execution, timeout, and sandboxing.
"""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

logger = logging.getLogger("sentinelforge.executor")

# Patterns that must never appear in user-supplied argument values
_DANGEROUS_PATTERNS = re.compile(
    r"[;&|`$\(\)\{\}!<>]"   # shell metacharacters
    r"|\.\./"                # path traversal
    r"|/etc/"                # system paths
    r"|/proc/"
    r"|/dev/"
    r"|~/"                   # home directory expansion
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

        venv_path = Path(tool_config.get("venv", ""))
        cli_cmd = tool_config.get("cli", tool_name)

        # Build the command
        if venv_path.exists():
            # Use the tool's isolated venv
            if (venv_path / "bin" / cli_cmd).exists():
                cmd = [str(venv_path / "bin" / cli_cmd)]
            elif (venv_path / "Scripts" / f"{cli_cmd}.exe").exists():
                cmd = [str(venv_path / "Scripts" / f"{cli_cmd}.exe")]
            else:
                cmd = [str(venv_path / "bin" / "python"), "-m", cli_cmd]
        else:
            # Fall back to system command
            cmd = [cli_cmd]

        # Add target and extra args
        if target:
            cmd.extend(["--target", target])

        if safe_args:
            # Only pass allowed args from the tool's declared allowed_args list
            allowed_keys = set(tool_config.get("allowed_args", []))
            for key, value in safe_args.items():
                # If the tool declares allowed_args, enforce it
                if allowed_keys and key not in allowed_keys:
                    logger.warning(f"Skipping disallowed arg '{key}' for tool {tool_name}")
                    continue
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                elif isinstance(value, list):
                    cmd.extend([f"--{key}", ",".join(str(v) for v in value)])
                else:
                    cmd.extend([f"--{key}", str(value)])

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

    def _build_env(self, tool_config: dict) -> dict:
        """Build environment for tool execution."""
        import os
        env = os.environ.copy()
        # Pass through API keys
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY",
                     "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "HUGGINGFACE_API_TOKEN"]:
            if key in os.environ:
                env[key] = os.environ[key]
        return env


if __name__ == "__main__":
    # Quick test
    executor = ToolExecutor()
    print(f"Available tools: {executor.list_tools()}")
    for name in executor.list_tools():
        config = executor.get_tool_config(name)
        print(f"  {name} v{config.get('version', '?')} - {config.get('description', '')}")
