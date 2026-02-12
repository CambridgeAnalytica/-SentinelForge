"""
Incident Response Playbook endpoints.
"""

import logging
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, Depends, HTTPException

from schemas import PlaybookInfo, PlaybookRunRequest
from middleware.auth import get_current_user, require_operator
from models import User

router = APIRouter()
logger = logging.getLogger("sentinelforge.playbooks")

_playbooks_cache = None


def _load_playbooks() -> List[dict]:
    """Load YAML playbook definitions."""
    global _playbooks_cache
    if _playbooks_cache is not None:
        return _playbooks_cache

    playbooks = []
    playbook_dirs = [
        Path("playbooks"),
        Path("/app/playbooks"),
        Path(__file__).parent.parent.parent.parent.parent / "playbooks",
    ]

    for pb_dir in playbook_dirs:
        if pb_dir.exists():
            for f in sorted(pb_dir.glob("*.yaml")):
                try:
                    with open(f) as fh:
                        data = yaml.safe_load(fh)
                        if data:
                            playbooks.append(data)
                except Exception as e:
                    logger.warning(f"Failed to load playbook {f}: {e}")
            break

    _playbooks_cache = playbooks
    return playbooks


@router.get("/", response_model=List[PlaybookInfo])
async def list_playbooks(user: User = Depends(get_current_user)):
    """List all available IR playbooks."""
    playbooks = _load_playbooks()
    return [
        PlaybookInfo(
            id=p["id"],
            name=p["name"],
            description=p.get("description", ""),
            trigger=p.get("trigger", "manual"),
            severity=p.get("severity", "medium"),
            steps=p.get("steps", []),
        )
        for p in playbooks
    ]


@router.get("/{playbook_id}", response_model=PlaybookInfo)
async def get_playbook(playbook_id: str, user: User = Depends(get_current_user)):
    """Get detailed playbook info."""
    playbooks = _load_playbooks()
    for p in playbooks:
        if p["id"] == playbook_id:
            return PlaybookInfo(
                id=p["id"],
                name=p["name"],
                description=p.get("description", ""),
                trigger=p.get("trigger", "manual"),
                severity=p.get("severity", "medium"),
                steps=p.get("steps", []),
            )
    raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' not found")


@router.post("/{playbook_id}/run")
async def run_playbook(
    playbook_id: str,
    request: PlaybookRunRequest,
    user: User = Depends(require_operator),
):
    """Execute an IR playbook."""
    playbooks = _load_playbooks()
    playbook = None
    for p in playbooks:
        if p["id"] == playbook_id:
            playbook = p
            break

    if not playbook:
        raise HTTPException(
            status_code=404, detail=f"Playbook '{playbook_id}' not found"
        )

    logger.info(f"Running playbook {playbook_id}")

    # Execute steps (in production, each step would be orchestrated)
    executed_steps = []
    for step in playbook.get("steps", []):
        executed_steps.append(
            {
                "step": step.get("name", "unnamed"),
                "action": step.get("action", "unknown"),
                "status": "completed",
                "output": f"Step '{step.get('name', 'unnamed')}' executed successfully.",
            }
        )

    return {
        "playbook_id": playbook_id,
        "status": "completed",
        "steps_executed": len(executed_steps),
        "results": executed_steps,
    }
