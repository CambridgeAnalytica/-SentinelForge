"""
Tools management endpoints.
Integrates with the BlackICE tool registry.
"""

import logging
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, Depends, HTTPException

from schemas import ToolInfo, ToolRunRequest, ToolRunResponse
from middleware.auth import get_current_user, require_operator
from models import User

router = APIRouter()
logger = logging.getLogger("sentinelforge.tools")

# Load tool registry
_tools_cache = None


def _load_tools_registry() -> dict:
    global _tools_cache
    if _tools_cache is not None:
        return _tools_cache

    registry_paths = [
        Path("tools/registry.yaml"),
        Path("/app/tools/registry.yaml"),
        Path(__file__).parent.parent.parent.parent.parent / "tools" / "registry.yaml",
    ]

    for path in registry_paths:
        if path.exists():
            with open(path) as f:
                _tools_cache = yaml.safe_load(f)
                return _tools_cache

    logger.warning("Tool registry not found, using empty registry")
    _tools_cache = {"tools": []}
    return _tools_cache


@router.get("/", response_model=List[ToolInfo])
async def list_tools(user: User = Depends(get_current_user)):
    """List all available BlackICE tools."""
    registry = _load_tools_registry()
    tools = []
    for tool in registry.get("tools", []):
        tools.append(ToolInfo(
            name=tool["name"],
            version=tool.get("version", "0.0.0"),
            category=tool.get("category", "unknown"),
            description=tool.get("description", ""),
            capabilities=tool.get("capabilities", []),
            mitre_atlas=tool.get("mitre_atlas", []),
            venv_path=tool.get("venv", ""),
            cli_command=tool.get("cli", ""),
        ))
    return tools


@router.get("/{tool_name}", response_model=ToolInfo)
async def get_tool_info(tool_name: str, user: User = Depends(get_current_user)):
    """Get detailed info about a specific tool."""
    registry = _load_tools_registry()
    for tool in registry.get("tools", []):
        if tool["name"] == tool_name:
            return ToolInfo(
                name=tool["name"],
                version=tool.get("version", "0.0.0"),
                category=tool.get("category", "unknown"),
                description=tool.get("description", ""),
                capabilities=tool.get("capabilities", []),
                mitre_atlas=tool.get("mitre_atlas", []),
                venv_path=tool.get("venv", ""),
                cli_command=tool.get("cli", ""),
            )
    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")


@router.post("/{tool_name}/run", response_model=ToolRunResponse)
async def run_tool(
    tool_name: str,
    request: ToolRunRequest,
    user: User = Depends(require_operator),
):
    """Execute a tool against a target. Requires operator role."""
    registry = _load_tools_registry()
    tool_config = None
    for tool in registry.get("tools", []):
        if tool["name"] == tool_name:
            tool_config = tool
            break

    if not tool_config:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    # Import and use the tool executor
    try:
        from tools.executor import ToolExecutor
        executor = ToolExecutor()
        result = executor.execute_tool(
            tool_name,
            target=request.target,
            args=request.args,
            timeout=request.timeout,
        )
        return ToolRunResponse(
            tool=tool_name,
            target=request.target,
            status="completed" if result.get("success") else "failed",
            output=result.get("stdout", ""),
            duration_seconds=result.get("duration", 0.0),
        )
    except ImportError:
        logger.warning(f"Tool executor not available, returning stub for {tool_name}")
        return ToolRunResponse(
            tool=tool_name,
            target=request.target,
            status="stub",
            output=f"Tool '{tool_name}' executor not yet available in this environment. "
                   f"Install the tool in its venv at {tool_config.get('venv', 'N/A')} to enable execution.",
            duration_seconds=0.0,
        )
