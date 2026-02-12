"""
Attack scenario management and execution endpoints.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AttackRun, RunStatus, Finding, User
from schemas import AttackScenario, AttackRunRequest, AttackRunResponse, AttackRunDetail
from middleware.auth import get_current_user, require_operator

router = APIRouter()
logger = logging.getLogger("sentinelforge.attacks")

_scenarios_cache = None


def _load_scenarios() -> List[dict]:
    """Load YAML scenario definitions."""
    global _scenarios_cache
    if _scenarios_cache is not None:
        return _scenarios_cache

    scenarios = []
    scenario_dirs = [
        Path("scenarios"),
        Path("/app/scenarios"),
        Path(__file__).parent.parent.parent.parent.parent / "scenarios",
    ]

    for scenario_dir in scenario_dirs:
        if scenario_dir.exists():
            for f in sorted(scenario_dir.glob("*.yaml")):
                try:
                    with open(f) as fh:
                        data = yaml.safe_load(fh)
                        if data:
                            scenarios.append(data)
                except Exception as e:
                    logger.warning(f"Failed to load scenario {f}: {e}")
            break

    _scenarios_cache = scenarios
    return scenarios


@router.get("/scenarios", response_model=List[AttackScenario])
async def list_scenarios(user: User = Depends(get_current_user)):
    """List all available attack scenarios."""
    scenarios = _load_scenarios()
    return [
        AttackScenario(
            id=s["id"],
            name=s["name"],
            description=s.get("description", ""),
            tools=s.get("tools", []),
            mitre_techniques=s.get("mitre_techniques", []),
            config=s.get("default_config", {}),
        )
        for s in scenarios
    ]


@router.post("/run", response_model=AttackRunResponse)
async def launch_attack(
    request: AttackRunRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch an attack scenario against a target model."""
    # Validate scenario exists
    scenarios = _load_scenarios()
    scenario = None
    for s in scenarios:
        if s["id"] == request.scenario_id:
            scenario = s
            break

    if not scenario:
        raise HTTPException(
            status_code=404, detail=f"Scenario '{request.scenario_id}' not found"
        )

    # Create attack run
    run = AttackRun(
        scenario_id=request.scenario_id,
        target_model=request.target_model,
        status=RunStatus.QUEUED,
        config={**scenario.get("default_config", {}), **request.config},
        user_id=user.id,
    )
    db.add(run)
    await db.flush()

    logger.info(
        f"Created attack run {run.id}: {request.scenario_id} → {request.target_model}"
    )

    # In a production system, this would be dispatched to the worker pool.
    # For now, we run synchronously in-process.
    run.status = RunStatus.RUNNING
    run.started_at = datetime.now(timezone.utc)

    try:
        results = await _execute_scenario(scenario, request.target_model, run.config)
        run.results = results
        run.status = RunStatus.COMPLETED
        run.progress = 100.0

        # Create findings from results with evidence hashing
        from services.evidence_hashing import compute_evidence_hash

        previous_hash = None

        for finding_data in results.get("findings", []):
            evidence = finding_data.get("evidence", {})
            tool_name = finding_data.get("tool", "unknown")
            evidence_hash = compute_evidence_hash(
                evidence=evidence,
                run_id=run.id,
                tool_name=tool_name,
                previous_hash=previous_hash,
            )
            finding = Finding(
                run_id=run.id,
                tool_name=tool_name,
                severity=finding_data.get("severity", "info"),
                title=finding_data.get("title", "Unnamed finding"),
                description=finding_data.get("description"),
                mitre_technique=finding_data.get("mitre_technique"),
                evidence=evidence,
                remediation=finding_data.get("remediation"),
                evidence_hash=evidence_hash,
                previous_hash=previous_hash,
            )
            db.add(finding)
            previous_hash = evidence_hash

    except Exception as e:
        run.status = RunStatus.FAILED
        run.error_message = str(e)
        logger.error(f"Attack run {run.id} failed: {e}")

    run.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return AttackRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        target_model=run.target_model,
        status=run.status.value,
        progress=run.progress,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/runs", response_model=List[AttackRunResponse])
async def list_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all attack runs."""
    result = await db.execute(
        select(AttackRun).order_by(AttackRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return [
        AttackRunResponse(
            id=r.id,
            scenario_id=r.scenario_id,
            target_model=r.target_model,
            status=r.status.value,
            progress=r.progress,
            created_at=r.created_at,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=AttackRunDetail)
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of an attack run."""
    result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Load findings
    findings_result = await db.execute(select(Finding).where(Finding.run_id == run_id))
    findings = findings_result.scalars().all()

    return AttackRunDetail(
        id=run.id,
        scenario_id=run.scenario_id,
        target_model=run.target_model,
        status=run.status.value,
        progress=run.progress,
        config=run.config or {},
        results=run.results or {},
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        findings=[
            {
                "id": f.id,
                "tool_name": f.tool_name,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "mitre_technique": f.mitre_technique,
                "remediation": f.remediation,
            }
            for f in findings
        ],
    )


@router.get("/runs/{run_id}/verify")
async def verify_evidence_chain(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify the evidence hash chain for an attack run's findings."""
    from services.evidence_hashing import verify_evidence_chain as _verify

    result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings_result = await db.execute(
        select(Finding)
        .where(Finding.run_id == run_id)
        .order_by(Finding.created_at.asc())
    )
    findings = findings_result.scalars().all()

    return _verify(findings)


async def _execute_scenario(scenario: dict, target: str, config: dict) -> dict:
    """Execute an attack scenario. Returns results dict."""
    results = {
        "scenario": scenario["id"],
        "target": target,
        "tools_executed": [],
        "findings": [],
        "multi_turn_results": [],
        "summary": {},
    }

    # Execute tools
    for tool_name in scenario.get("tools", []):
        tool_result = {
            "tool": tool_name,
            "status": "completed",
            "output": f"Tool '{tool_name}' executed against {target}",
        }

        try:
            from tools.executor import ToolExecutor

            executor = ToolExecutor()
            exec_result = executor.execute_tool(tool_name, target=target, args=config)
            tool_result["output"] = exec_result.get("stdout", "")
            tool_result["status"] = (
                "completed" if exec_result.get("success") else "failed"
            )
        except (ImportError, Exception):
            tool_result["status"] = "stub"
            tool_result["output"] = (
                f"Tool '{tool_name}' not available in this environment. "
                f"Install via Docker tools image for full execution. Stub result generated."
            )

            # Generate stub findings for demo/testing
            results["findings"].append(
                {
                    "tool": tool_name,
                    "severity": "info",
                    "title": f"{tool_name}: Stub execution against {target}",
                    "description": f"Tool '{tool_name}' was not available. Install in Docker "
                    f"tools container for real results.",
                    "mitre_technique": (
                        scenario.get("mitre_techniques", [None])[0]
                        if scenario.get("mitre_techniques")
                        else None
                    ),
                    "remediation": f"Deploy SentinelForge with Docker to enable {tool_name}.",
                }
            )

        results["tools_executed"].append(tool_result)

    # Multi-turn adversarial conversations (if enabled in scenario config)
    if config.get("multi_turn"):
        from services.multi_turn_service import run_multi_turn_attack

        max_turns = config.get("max_turns", 10)
        provider = config.get("provider")

        # Run multi-turn for each test case of type "multi_turn"
        test_cases = scenario.get("test_cases", [])
        multi_turn_cases = [tc for tc in test_cases if tc.get("type") == "multi_turn"]

        # If no explicit multi-turn test cases, run with default strategy
        if not multi_turn_cases:
            multi_turn_cases = [
                {"strategy": "gradual_trust", "name": "Default Multi-Turn"}
            ]

        for tc in multi_turn_cases:
            strategy = tc.get("strategy", "gradual_trust")
            turns = tc.get("turns", max_turns)
            try:
                mt_result = await run_multi_turn_attack(
                    target_model=target,
                    strategy=strategy,
                    max_turns=turns,
                    provider=provider,
                    config=config,
                )
                results["multi_turn_results"].append(mt_result)
                # Merge multi-turn findings into main findings
                results["findings"].extend(mt_result.get("findings", []))
            except Exception as e:
                logger.error(f"Multi-turn attack failed ({strategy}): {e}")
                results["multi_turn_results"].append(
                    {
                        "strategy": strategy,
                        "error": str(e),
                    }
                )

    # Summary
    results["summary"] = {
        "total_tools": len(results["tools_executed"]),
        "completed": sum(
            1 for t in results["tools_executed"] if t["status"] == "completed"
        ),
        "failed": sum(1 for t in results["tools_executed"] if t["status"] == "failed"),
        "stubs": sum(1 for t in results["tools_executed"] if t["status"] == "stub"),
        "multi_turn_attacks": len(results["multi_turn_results"]),
        "total_findings": len(results["findings"]),
    }

    return results
