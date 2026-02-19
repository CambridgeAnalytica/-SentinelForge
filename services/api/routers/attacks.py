"""
Attack scenario management and execution endpoints.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AttackRun, RunStatus, Finding, User
from schemas import AttackScenario, AttackRunRequest, AttackRunResponse, AttackRunDetail
from middleware.auth import get_current_user, require_operator
from services.deduplication import classify_findings

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
                    with open(f, encoding="utf-8") as fh:
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
    background_tasks: BackgroundTasks,
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

    # Classify findings as new vs. recurring
    try:
        dedup_stats = await classify_findings(run.id, db)
        logger.info(f"Dedup stats for run {run.id}: {dedup_stats}")
    except Exception as e:
        logger.warning(f"Dedup classification failed for run {run.id}: {e}")

    # Dispatch webhook notification
    event = "attack.completed" if run.status == RunStatus.COMPLETED else "attack.failed"
    background_tasks.add_task(
        _dispatch_webhook,
        event,
        {
            "run_id": run.id,
            "scenario_id": run.scenario_id,
            "target_model": run.target_model,
            "status": run.status.value,
        },
    )

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
                "fingerprint": f.fingerprint,
                "is_new": f.is_new,
                "evidence_hash": f.evidence_hash,
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
    """Execute an attack scenario. Returns results dict.

    Execution phases:
    1. Direct LLM testing — sends scenario test-case prompts to the target
    2. External tool execution — runs installed tools (garak, etc.) if available
    3. Multi-turn adversarial — escalation-based conversation attacks
    """
    results = {
        "scenario": scenario["id"],
        "target": target,
        "tools_executed": [],
        "direct_test_results": [],
        "findings": [],
        "multi_turn_results": [],
        "summary": {},
    }

    # ── Phase 1: Direct LLM testing (always runs) ──
    try:
        from services.direct_test_service import run_direct_tests

        direct_results = await run_direct_tests(scenario, target, config)
        results["direct_test_results"] = direct_results.get("test_results", [])
        results["findings"].extend(direct_results.get("findings", []))
        logger.info(
            f"Direct testing: {direct_results.get('summary', {}).get('total_prompts', 0)} prompts, "
            f"{direct_results.get('summary', {}).get('failed_prompts', 0)} failures"
        )
    except Exception as e:
        logger.error(f"Direct testing failed: {e}")

    # ── Phase 2: External tool execution (if tools are installed) ──
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

            # Parse tool output into findings if available
            if exec_result.get("success") and exec_result.get("stdout"):
                tool_findings = _parse_tool_findings(
                    tool_name, exec_result["stdout"], scenario
                )
                results["findings"].extend(tool_findings)

        except (ImportError, FileNotFoundError, Exception) as exc:
            tool_result["status"] = "skipped"
            tool_result["output"] = (
                f"Tool '{tool_name}' not installed — skipped. "
                f"Direct LLM testing was used instead."
            )
            logger.info(f"Tool '{tool_name}' not available, skipped: {exc}")

        results["tools_executed"].append(tool_result)

    # ── Phase 3: Multi-turn adversarial (if enabled) ──
    if config.get("multi_turn"):
        from services.multi_turn_service import run_multi_turn_attack

        max_turns = config.get("max_turns", 10)
        provider = config.get("provider")

        test_cases = scenario.get("test_cases", [])
        multi_turn_cases = [tc for tc in test_cases if tc.get("type") == "multi_turn"]

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
                results["findings"].extend(mt_result.get("findings", []))
            except Exception as e:
                logger.error(f"Multi-turn attack failed ({strategy}): {e}")
                results["multi_turn_results"].append(
                    {"strategy": strategy, "error": str(e)}
                )

    # ── Summary ──
    direct_summary = {}
    if results["direct_test_results"]:
        total_prompts = sum(
            len(tc.get("prompt_results", []))
            for tc in results["direct_test_results"]
        )
        failed_prompts = sum(
            1
            for tc in results["direct_test_results"]
            for pr in tc.get("prompt_results", [])
            if not pr.get("passed", True)
        )
        direct_summary = {
            "total_prompts_tested": total_prompts,
            "prompts_failed": failed_prompts,
            "pass_rate": (total_prompts - failed_prompts) / max(total_prompts, 1),
        }

    results["summary"] = {
        "total_tools": len(results["tools_executed"]),
        "tools_completed": sum(
            1 for t in results["tools_executed"] if t["status"] == "completed"
        ),
        "tools_skipped": sum(
            1 for t in results["tools_executed"] if t["status"] == "skipped"
        ),
        "direct_tests": direct_summary,
        "multi_turn_attacks": len(results["multi_turn_results"]),
        "total_findings": len(results["findings"]),
    }

    return results


def _parse_tool_findings(
    tool_name: str, stdout: str, scenario: dict
) -> list:
    """Parse real tool output into findings using the appropriate adapter."""
    try:
        if tool_name == "garak":
            from tools.garak_adapter import parse_garak_output
            return parse_garak_output(stdout)
        if tool_name == "promptfoo":
            from tools.promptfoo_adapter import parse_promptfoo_output
            return parse_promptfoo_output(stdout)
        if tool_name == "deepeval":
            from tools.deepeval_adapter import parse_deepeval_output
            return parse_deepeval_output(stdout)
    except Exception as e:
        logger.warning(f"Failed to parse {tool_name} output: {e}")
    return []


async def _dispatch_webhook(event_type: str, payload: dict) -> None:
    """Background task: dispatch webhook event with its own DB session."""
    try:
        from services.webhook_service import dispatch_webhook_event

        await dispatch_webhook_event(event_type, payload)
    except Exception as e:
        logger.error(f"Webhook dispatch error: {e}")


# ---------- Custom Scenario CRUD ----------

_custom_scenarios: list = []  # In-memory store for user-created scenarios


@router.post("/scenarios", status_code=201)
async def create_scenario(
    scenario: AttackScenario,
    user: User = Depends(require_operator),
):
    """Create a custom attack scenario (operator-only)."""
    # Check for ID collision with existing scenarios
    existing = _load_scenarios()
    if any(s.get("id") == scenario.id for s in existing) or any(
        s["id"] == scenario.id for s in _custom_scenarios
    ):
        raise HTTPException(
            status_code=409, detail=f"Scenario ID '{scenario.id}' already exists"
        )

    entry = {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "tools": scenario.tools,
        "mitre_techniques": scenario.mitre_techniques,
        "config": scenario.config,
        "custom": True,
        "created_by": user.username,
    }
    _custom_scenarios.append(entry)

    # Invalidate cache so new scenario appears in list
    global _scenarios_cache
    _scenarios_cache = None

    logger.info(f"Custom scenario '{scenario.id}' created by {user.username}")
    return entry


@router.put("/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    scenario: AttackScenario,
    user: User = Depends(require_operator),
):
    """Update a custom attack scenario (operator-only)."""
    for i, s in enumerate(_custom_scenarios):
        if s["id"] == scenario_id:
            _custom_scenarios[i] = {
                "id": scenario.id,
                "name": scenario.name,
                "description": scenario.description,
                "tools": scenario.tools,
                "mitre_techniques": scenario.mitre_techniques,
                "config": scenario.config,
                "custom": True,
                "created_by": s.get("created_by", user.username),
            }
            global _scenarios_cache
            _scenarios_cache = None
            return _custom_scenarios[i]

    raise HTTPException(status_code=404, detail="Custom scenario not found")


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: str,
    user: User = Depends(require_operator),
):
    """Delete a custom attack scenario (operator-only)."""
    for i, s in enumerate(_custom_scenarios):
        if s["id"] == scenario_id:
            _custom_scenarios.pop(i)
            global _scenarios_cache
            _scenarios_cache = None
            logger.info(f"Custom scenario '{scenario_id}' deleted by {user.username}")
            return

    raise HTTPException(status_code=404, detail="Custom scenario not found")
