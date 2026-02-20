"""
Attack scenario management and execution endpoints.
"""

import asyncio
import csv
import io
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Callable, Awaitable

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, AsyncSessionLocal
from models import AttackRun, RunStatus, Finding, Report, User, AuditLog
from schemas import (
    AttackScenario,
    AttackRunRequest,
    AttackRunResponse,
    AttackRunDetail,
    ComparisonRequest,
    ComparisonResponse,
    AuditRequest,
    AuditResponse,
)
from middleware.auth import get_current_user, require_operator, require_admin
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
        Path(__file__).parent.parent.parent.parent / "scenarios",
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
    results = []
    for s in scenarios:
        test_cases = s.get("test_cases", [])
        prompt_count = sum(len(tc.get("prompts", [])) for tc in test_cases)
        results.append(
            AttackScenario(
                id=s["id"],
                name=s["name"],
                description=s.get("description", ""),
                severity=s.get("severity", "medium"),
                category=s.get("category", "general"),
                tools=s.get("tools", []),
                mitre_techniques=s.get("mitre_techniques", []),
                owasp_llm=s.get("owasp_llm", []),
                arcanum_taxonomy=s.get("arcanum_taxonomy", []),
                test_cases_count=len(test_cases),
                prompt_count=prompt_count,
                multi_turn=s.get("default_config", {}).get("multi_turn", False),
                config=s.get("default_config", {}),
            )
        )
    return results


@router.post("/run", response_model=AttackRunResponse)
async def launch_attack(
    request: AttackRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch an attack scenario against a target model.

    Creates the run immediately and returns. Execution happens
    asynchronously so the dashboard receives the run ID instantly
    and can track progress via SSE.
    """
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

    # Create attack run as QUEUED
    merged_config = {**scenario.get("default_config", {}), **request.config}
    run = AttackRun(
        scenario_id=request.scenario_id,
        target_model=request.target_model,
        status=RunStatus.QUEUED,
        config=merged_config,
        user_id=user.id,
    )
    db.add(run)

    # Audit log: attack launched
    db.add(
        AuditLog(
            user_id=user.id,
            action="attack.launched",
            resource_type="attack_run",
            resource_id=run.id,
            details={
                "scenario_id": request.scenario_id,
                "target_model": request.target_model,
            },
        )
    )

    # Commit immediately so the run is visible to SSE and list queries
    await db.commit()

    logger.info(
        f"Created attack run {run.id}: {request.scenario_id} → {request.target_model}"
    )

    # Kick off async execution (runs in the event loop, not blocking response)
    asyncio.create_task(
        _run_attack_async(
            run.id, scenario, request.target_model, merged_config, user.id
        )
    )

    return AttackRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        target_model=run.target_model,
        status="queued",
        progress=0.0,
        created_at=run.created_at,
        started_at=None,
        completed_at=None,
        findings=[],
    )


async def _run_attack_async(
    run_id: str,
    scenario: dict,
    target_model: str,
    config: dict,
    user_id: str,
):
    """Background task: execute attack with its own DB session and live progress."""
    async with AsyncSessionLocal() as db:
        try:
            # Mark as RUNNING
            result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
            run = result.scalar_one()
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Progress callback — updates DB so SSE can read it
            async def update_progress(fraction: float):
                run.progress = min(fraction, 0.99)
                await db.commit()

            results = await _execute_scenario(
                scenario, target_model, config, progress_callback=update_progress
            )

            run.results = results
            run.status = RunStatus.COMPLETED
            run.progress = 1.0

            # Create findings with evidence hashing + Arcanum taxonomy tags
            from services.evidence_hashing import compute_evidence_hash
            from data.arcanum_taxonomy import classify_finding as arc_classify

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

                # Auto-tag with Arcanum taxonomy
                test_type = evidence.get("test_type") or evidence.get("strategy")
                mitre_tech = finding_data.get("mitre_technique")
                arcanum_tags = arc_classify(
                    test_type=test_type, mitre_technique=mitre_tech
                )
                if arcanum_tags:
                    evidence["arcanum_taxonomy"] = arcanum_tags

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

            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

            # Classify findings as new vs. recurring
            try:
                dedup_stats = await classify_findings(run.id, db)
                logger.info(f"Dedup stats for run {run.id}: {dedup_stats}")
            except Exception as e:
                logger.warning(f"Dedup classification failed for run {run.id}: {e}")

            # Audit log: completed
            findings_count = len(results.get("findings", []))
            db.add(
                AuditLog(
                    user_id=user_id,
                    action="attack.completed",
                    resource_type="attack_run",
                    resource_id=run.id,
                    details={
                        "scenario_id": run.scenario_id,
                        "target_model": run.target_model,
                        "status": "completed",
                        "findings_count": findings_count,
                    },
                )
            )
            await db.commit()

            # Dispatch webhook
            await _dispatch_webhook(
                "attack.completed",
                {
                    "run_id": run.id,
                    "scenario_id": run.scenario_id,
                    "target_model": run.target_model,
                    "status": "completed",
                },
            )

            logger.info(f"Attack run {run_id} completed: {findings_count} findings")

        except Exception as e:
            logger.error(f"Attack run {run_id} failed: {e}")
            try:
                run.status = RunStatus.FAILED
                run.error_message = str(e)
                run.completed_at = datetime.now(timezone.utc)
                db.add(
                    AuditLog(
                        user_id=user_id,
                        action="attack.failed",
                        resource_type="attack_run",
                        resource_id=run_id,
                        details={"error": str(e)[:500]},
                    )
                )
                await db.commit()
                await _dispatch_webhook(
                    "attack.failed",
                    {
                        "run_id": run_id,
                        "scenario_id": scenario.get("id", ""),
                        "target_model": target_model,
                        "status": "failed",
                    },
                )
            except Exception as inner:
                logger.error(f"Failed to update run {run_id} status: {inner}")


@router.get("/runs", response_model=List[AttackRunResponse])
async def list_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all attack runs with their findings."""
    result = await db.execute(
        select(AttackRun).order_by(AttackRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()

    responses = []
    for r in runs:
        # Load findings for each run
        findings_result = await db.execute(
            select(Finding).where(Finding.run_id == r.id)
        )
        findings = findings_result.scalars().all()

        responses.append(
            AttackRunResponse(
                id=r.id,
                scenario_id=r.scenario_id,
                target_model=r.target_model,
                status=r.status.value,
                progress=r.progress,
                created_at=r.created_at,
                started_at=r.started_at,
                completed_at=r.completed_at,
                findings=[
                    {
                        "id": f.id,
                        "tool_name": f.tool_name,
                        "severity": (
                            f.severity.value
                            if hasattr(f.severity, "value")
                            else str(f.severity)
                        ),
                        "title": f.title,
                        "description": f.description,
                        "mitre_technique": f.mitre_technique,
                        "remediation": f.remediation,
                        "evidence": f.evidence,
                        "evidence_hash": f.evidence_hash,
                        "is_new": f.is_new,
                        "false_positive": f.false_positive,
                        "created_at": (
                            f.created_at.isoformat() if f.created_at else None
                        ),
                    }
                    for f in findings
                ],
            )
        )
    return responses


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
                "severity": (
                    f.severity.value
                    if hasattr(f.severity, "value")
                    else str(f.severity)
                ),
                "title": f.title,
                "description": f.description,
                "mitre_technique": f.mitre_technique,
                "remediation": f.remediation,
                "fingerprint": f.fingerprint,
                "is_new": f.is_new,
                "false_positive": f.false_positive,
                "evidence": f.evidence,
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


@router.delete("/runs/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete an attack run and its findings + reports (admin only)."""
    from sqlalchemy import delete as sql_delete

    result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Delete related records first (foreign key constraints)
    await db.execute(sql_delete(Finding).where(Finding.run_id == run_id))
    await db.execute(sql_delete(Report).where(Report.run_id == run_id))
    # Delete the run itself
    await db.execute(sql_delete(AttackRun).where(AttackRun.id == run_id))

    # Audit log
    db.add(
        AuditLog(
            user_id=user.id,
            action="attack.deleted",
            resource_type="attack_run",
            resource_id=run_id,
            details={
                "scenario_id": run.scenario_id,
                "target_model": run.target_model,
            },
        )
    )
    await db.commit()

    logger.info(f"Attack run {run_id} deleted by {user.username}")


@router.patch("/findings/{finding_id}/false-positive")
async def toggle_false_positive(
    finding_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark or unmark a finding as a false positive (admin only)."""
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.false_positive = not finding.false_positive
    db.add(
        AuditLog(
            user_id=user.id,
            action="finding.false_positive_toggled",
            resource_type="finding",
            resource_id=finding_id,
            details={
                "false_positive": finding.false_positive,
                "title": finding.title,
            },
        )
    )
    await db.commit()

    return {
        "id": finding.id,
        "false_positive": finding.false_positive,
    }


# ---------- Feature 5: CSV Export ----------


@router.get("/runs/{run_id}/export")
async def export_findings_csv(
    run_id: str,
    format: str = Query("csv", description="Export format (csv)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export findings for a run as CSV."""
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

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "severity",
            "title",
            "tool_name",
            "mitre_technique",
            "description",
            "remediation",
            "evidence_hash",
            "is_new",
            "false_positive",
            "created_at",
        ]
    )
    for f in findings:
        writer.writerow(
            [
                f.id,
                f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                f.title,
                f.tool_name,
                f.mitre_technique or "",
                (f.description or "")[:1000],
                (f.remediation or "")[:500],
                f.evidence_hash or "",
                f.is_new,
                f.false_positive,
                f.created_at.isoformat() if f.created_at else "",
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"sentinelforge_{run.scenario_id}_{run_id[:8]}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------- Feature 3: Hardening Advisor ----------


@router.get("/runs/{run_id}/harden")
async def hardening_advisor(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze completed run findings and generate system prompt hardening advice."""
    result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != RunStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Run must be completed first")

    findings_result = await db.execute(select(Finding).where(Finding.run_id == run_id))
    findings = findings_result.scalars().all()

    from services.hardening_service import generate_hardening_advice

    return generate_hardening_advice(findings, run.scenario_id)


# ---------- Feature 6: Historical Trends ----------


@router.get("/trends")
async def get_trends(
    model: Optional[str] = Query(None, description="Filter by target model"),
    days: int = Query(30, description="Number of days to look back"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical safety trends per model and scenario."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = (
        select(AttackRun)
        .where(
            AttackRun.status == RunStatus.COMPLETED,
            AttackRun.completed_at >= cutoff,
        )
        .order_by(AttackRun.completed_at.asc())
    )
    if model:
        query = query.where(AttackRun.target_model == model)

    result = await db.execute(query)
    runs = result.scalars().all()

    # Gather distinct models
    models_query = await db.execute(
        select(AttackRun.target_model)
        .where(AttackRun.status == RunStatus.COMPLETED)
        .distinct()
    )
    available_models = [row[0] for row in models_query.all()]

    data_points = []
    for run in runs:
        summary = (run.results or {}).get("summary", {})
        direct = summary.get("direct_tests", {})
        pass_rate = direct.get("pass_rate", direct.get("overall_pass_rate"))

        # Count findings by severity
        findings_result = await db.execute(
            select(Finding).where(Finding.run_id == run.id)
        )
        findings = findings_result.scalars().all()
        critical_count = sum(
            1
            for f in findings
            if (f.severity.value if hasattr(f.severity, "value") else str(f.severity))
            == "critical"
        )

        data_points.append(
            {
                "date": (
                    run.completed_at.strftime("%Y-%m-%d") if run.completed_at else None
                ),
                "run_id": run.id,
                "scenario_id": run.scenario_id,
                "target_model": run.target_model,
                "pass_rate": pass_rate,
                "findings_count": len(findings),
                "critical_count": critical_count,
            }
        )

    # Compute summary
    avg_pass_rate = None
    trend = "stable"
    worst_scenario = None
    if data_points:
        rates = [d["pass_rate"] for d in data_points if d["pass_rate"] is not None]
        if rates:
            avg_pass_rate = sum(rates) / len(rates)
            if len(rates) >= 2:
                first_half = rates[: len(rates) // 2]
                second_half = rates[len(rates) // 2 :]
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                if avg_second < avg_first - 0.05:
                    trend = "degrading"
                elif avg_second > avg_first + 0.05:
                    trend = "improving"

        # Worst scenario by lowest pass rate
        scenario_rates: dict = {}
        for d in data_points:
            if d["pass_rate"] is not None:
                scenario_rates.setdefault(d["scenario_id"], []).append(d["pass_rate"])
        if scenario_rates:
            worst_scenario = min(
                scenario_rates,
                key=lambda s: sum(scenario_rates[s]) / len(scenario_rates[s]),
            )

    return {
        "model": model,
        "days": days,
        "available_models": available_models,
        "data_points": data_points,
        "summary": {
            "avg_pass_rate": round(avg_pass_rate, 4) if avg_pass_rate else None,
            "trend": trend,
            "worst_scenario": worst_scenario,
            "total_runs": len(data_points),
        },
    }


# ---------- Feature 1: Model Comparison ----------


@router.post("/compare", response_model=ComparisonResponse)
async def compare_models(
    request: ComparisonRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch the same scenario against multiple models for side-by-side comparison."""
    if len(request.target_models) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models required")
    if len(request.target_models) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 models per comparison")

    # Validate scenario
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

    comparison_id = str(uuid.uuid4())
    merged_config = {**scenario.get("default_config", {}), **request.config}
    run_ids = []

    for target_model in request.target_models:
        run = AttackRun(
            scenario_id=request.scenario_id,
            target_model=target_model,
            status=RunStatus.QUEUED,
            config=merged_config,
            user_id=user.id,
            comparison_id=comparison_id,
        )
        db.add(run)
        run_ids.append(run.id)

        db.add(
            AuditLog(
                user_id=user.id,
                action="comparison.launched",
                resource_type="attack_run",
                resource_id=run.id,
                details={
                    "comparison_id": comparison_id,
                    "scenario_id": request.scenario_id,
                    "target_model": target_model,
                },
            )
        )

    await db.commit()

    # Kick off all runs in parallel
    for i, target_model in enumerate(request.target_models):
        asyncio.create_task(
            _run_attack_async(
                run_ids[i], scenario, target_model, merged_config, user.id
            )
        )

    logger.info(
        f"Comparison {comparison_id}: {request.scenario_id} → {request.target_models}"
    )

    return ComparisonResponse(
        id=comparison_id,
        scenario_id=request.scenario_id,
        target_models=request.target_models,
        run_ids=run_ids,
        status="running",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/comparisons")
async def list_comparisons(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all model comparisons."""
    result = await db.execute(
        select(
            AttackRun.comparison_id,
            AttackRun.scenario_id,
            func.count(AttackRun.id).label("run_count"),
            func.min(AttackRun.created_at).label("created_at"),
        )
        .where(AttackRun.comparison_id.isnot(None))
        .group_by(AttackRun.comparison_id, AttackRun.scenario_id)
        .order_by(func.min(AttackRun.created_at).desc())
        .limit(50)
    )
    rows = result.all()

    comparisons = []
    for row in rows:
        # Get all runs in this comparison
        runs_result = await db.execute(
            select(AttackRun).where(AttackRun.comparison_id == row.comparison_id)
        )
        runs = runs_result.scalars().all()
        statuses = [r.status.value for r in runs]
        overall = (
            "completed"
            if all(s == "completed" for s in statuses)
            else (
                "running"
                if any(s in ("running", "queued") for s in statuses)
                else "failed"
            )
        )
        comparisons.append(
            {
                "id": row.comparison_id,
                "scenario_id": row.scenario_id,
                "target_models": [r.target_model for r in runs],
                "run_ids": [r.id for r in runs],
                "status": overall,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return comparisons


@router.get("/comparisons/{comparison_id}")
async def get_comparison(
    comparison_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comparison detail with per-model scorecard."""
    result = await db.execute(
        select(AttackRun).where(AttackRun.comparison_id == comparison_id)
    )
    runs = result.scalars().all()
    if not runs:
        raise HTTPException(status_code=404, detail="Comparison not found")

    scorecard = []
    for run in runs:
        findings_result = await db.execute(
            select(Finding).where(Finding.run_id == run.id)
        )
        findings = findings_result.scalars().all()

        severity_counts = {}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary = (run.results or {}).get("summary", {})
        direct = summary.get("direct_tests", {})
        pass_rate = direct.get("pass_rate", direct.get("overall_pass_rate"))

        scorecard.append(
            {
                "run_id": run.id,
                "target_model": run.target_model,
                "status": run.status.value,
                "progress": run.progress,
                "pass_rate": pass_rate,
                "findings_count": len(findings),
                "severity_breakdown": severity_counts,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
            }
        )

    statuses = [r.status.value for r in runs]
    overall = (
        "completed"
        if all(s == "completed" for s in statuses)
        else (
            "running" if any(s in ("running", "queued") for s in statuses) else "failed"
        )
    )

    return {
        "id": comparison_id,
        "scenario_id": runs[0].scenario_id,
        "status": overall,
        "scorecard": scorecard,
        "created_at": (
            min(r.created_at for r in runs).isoformat() if runs[0].created_at else None
        ),
    }


# ---------- Feature 2: Batch Audit ----------


@router.post("/audit", response_model=AuditResponse)
async def launch_audit(
    request: AuditRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch a full audit — run all (or selected) scenarios against a target model."""
    scenarios = _load_scenarios()

    if request.scenario_ids:
        selected = [s for s in scenarios if s["id"] in request.scenario_ids]
        if not selected:
            raise HTTPException(status_code=404, detail="No matching scenarios found")
    else:
        selected = scenarios

    audit_id = str(uuid.uuid4())
    run_ids = []

    for scenario in selected:
        merged_config = {**scenario.get("default_config", {}), **request.config}
        run = AttackRun(
            scenario_id=scenario["id"],
            target_model=request.target_model,
            status=RunStatus.QUEUED,
            config=merged_config,
            user_id=user.id,
            audit_id=audit_id,
        )
        db.add(run)
        run_ids.append(run.id)

    db.add(
        AuditLog(
            user_id=user.id,
            action="audit.launched",
            resource_type="audit",
            resource_id=audit_id,
            details={
                "target_model": request.target_model,
                "scenario_count": len(selected),
            },
        )
    )

    await db.commit()

    # Kick off all scenario runs
    for i, scenario in enumerate(selected):
        merged_config = {**scenario.get("default_config", {}), **request.config}
        asyncio.create_task(
            _run_attack_async(
                run_ids[i], scenario, request.target_model, merged_config, user.id
            )
        )

    logger.info(f"Audit {audit_id}: {len(selected)} scenarios → {request.target_model}")

    return AuditResponse(
        id=audit_id,
        target_model=request.target_model,
        scenario_count=len(selected),
        run_ids=run_ids,
        status="running",
        created_at=datetime.now(timezone.utc),
    )


@router.get("/audits")
async def list_audits(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all audits."""
    result = await db.execute(
        select(
            AttackRun.audit_id,
            AttackRun.target_model,
            func.count(AttackRun.id).label("scenario_count"),
            func.min(AttackRun.created_at).label("created_at"),
        )
        .where(AttackRun.audit_id.isnot(None))
        .group_by(AttackRun.audit_id, AttackRun.target_model)
        .order_by(func.min(AttackRun.created_at).desc())
        .limit(50)
    )
    rows = result.all()

    audits = []
    for row in rows:
        runs_result = await db.execute(
            select(AttackRun).where(AttackRun.audit_id == row.audit_id)
        )
        runs = runs_result.scalars().all()
        statuses = [r.status.value for r in runs]
        completed = sum(1 for s in statuses if s == "completed")
        overall = (
            "completed"
            if all(s == "completed" for s in statuses)
            else (
                "running"
                if any(s in ("running", "queued") for s in statuses)
                else "failed"
            )
        )
        audits.append(
            {
                "id": row.audit_id,
                "target_model": row.target_model,
                "scenario_count": row.scenario_count,
                "completed_count": completed,
                "status": overall,
                "run_ids": [r.id for r in runs],
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return audits


@router.get("/audits/{audit_id}")
async def get_audit(
    audit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit detail with per-scenario results and aggregate posture report."""
    result = await db.execute(select(AttackRun).where(AttackRun.audit_id == audit_id))
    runs = result.scalars().all()
    if not runs:
        raise HTTPException(status_code=404, detail="Audit not found")

    scenario_results = []
    total_findings = 0
    total_critical = 0
    total_high = 0
    all_pass_rates = []

    for run in runs:
        findings_result = await db.execute(
            select(Finding).where(Finding.run_id == run.id)
        )
        findings = findings_result.scalars().all()

        severity_counts = {}
        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary = (run.results or {}).get("summary", {})
        direct = summary.get("direct_tests", {})
        pass_rate = direct.get("pass_rate", direct.get("overall_pass_rate"))
        if pass_rate is not None:
            all_pass_rates.append(pass_rate)

        total_findings += len(findings)
        total_critical += severity_counts.get("critical", 0)
        total_high += severity_counts.get("high", 0)

        scenario_results.append(
            {
                "run_id": run.id,
                "scenario_id": run.scenario_id,
                "status": run.status.value,
                "progress": run.progress,
                "pass_rate": pass_rate,
                "findings_count": len(findings),
                "severity_breakdown": severity_counts,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
            }
        )

    statuses = [r.status.value for r in runs]
    completed_count = sum(1 for s in statuses if s == "completed")
    overall_status = (
        "completed"
        if all(s == "completed" for s in statuses)
        else (
            "running" if any(s in ("running", "queued") for s in statuses) else "failed"
        )
    )

    posture_score = (
        round(sum(all_pass_rates) / len(all_pass_rates) * 100, 1)
        if all_pass_rates
        else None
    )

    return {
        "id": audit_id,
        "target_model": runs[0].target_model,
        "status": overall_status,
        "scenario_count": len(runs),
        "completed_count": completed_count,
        "posture_score": posture_score,
        "total_findings": total_findings,
        "total_critical": total_critical,
        "total_high": total_high,
        "scenarios": scenario_results,
        "created_at": (
            min(r.created_at for r in runs).isoformat() if runs[0].created_at else None
        ),
    }


@router.get("/audits/{audit_id}/export")
async def export_audit_csv(
    audit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all findings from an audit as CSV."""
    result = await db.execute(select(AttackRun).where(AttackRun.audit_id == audit_id))
    runs = result.scalars().all()
    if not runs:
        raise HTTPException(status_code=404, detail="Audit not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "scenario_id",
            "target_model",
            "finding_id",
            "severity",
            "title",
            "tool_name",
            "mitre_technique",
            "description",
            "remediation",
            "is_new",
            "false_positive",
            "created_at",
        ]
    )

    for run in runs:
        findings_result = await db.execute(
            select(Finding).where(Finding.run_id == run.id)
        )
        findings = findings_result.scalars().all()
        for f in findings:
            writer.writerow(
                [
                    run.scenario_id,
                    run.target_model,
                    f.id,
                    (
                        f.severity.value
                        if hasattr(f.severity, "value")
                        else str(f.severity)
                    ),
                    f.title,
                    f.tool_name,
                    f.mitre_technique or "",
                    (f.description or "")[:1000],
                    (f.remediation or "")[:500],
                    f.is_new,
                    f.false_positive,
                    f.created_at.isoformat() if f.created_at else "",
                ]
            )

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"sentinelforge_audit_{audit_id[:8]}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _execute_scenario(
    scenario: dict,
    target: str,
    config: dict,
    progress_callback: Optional[Callable[[float], Awaitable[None]]] = None,
) -> dict:
    """Execute an attack scenario. Returns results dict.

    Execution phases:
    1. Direct LLM testing — sends scenario test-case prompts to the target
    2. External tool execution — runs installed tools (garak, etc.) if available
    3. Multi-turn adversarial — escalation-based conversation attacks

    progress_callback receives a float 0.0–1.0 after each prompt/turn.
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

    # ── Count total prompts upfront for progress calculation ──
    test_cases = scenario.get("test_cases", [])
    direct_prompt_count = sum(
        len(tc.get("prompts", []))
        for tc in test_cases
        if tc.get("type") != "multi_turn" and tc.get("prompts")
    )

    mt_prompt_count = 0
    if config.get("multi_turn"):
        max_turns = config.get("max_turns", 10)
        mt_cases = [tc for tc in test_cases if tc.get("type") == "multi_turn"]
        # Only count multi-turn prompts if the scenario defines its own
        # multi-turn test cases — don't inject generic prompts into unrelated scenarios
        mt_prompt_count = len(mt_cases) * max_turns

    total_work = max(direct_prompt_count + mt_prompt_count, 1)
    completed_work = 0

    async def on_prompt_done():
        """Called after each prompt/turn to update progress."""
        nonlocal completed_work
        completed_work += 1
        if progress_callback:
            await progress_callback(completed_work / total_work)

    # ── Phase 1: Direct LLM testing (always runs) ──
    try:
        from services.direct_test_service import run_direct_tests

        direct_results = await run_direct_tests(
            scenario, target, config, on_prompt_done=on_prompt_done
        )
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

        # Only run multi-turn if the scenario explicitly defines multi-turn
        # test cases. Don't inject generic gradual_trust/hacking prompts
        # into scenarios that don't define their own — the generic prompts
        # are unrelated to the scenario's actual attack category.
        multi_turn_cases = [tc for tc in test_cases if tc.get("type") == "multi_turn"]
        if not multi_turn_cases:
            logger.info(
                f"Scenario '{scenario['id']}' has no multi-turn test cases, "
                "skipping multi-turn phase"
            )

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
                    on_prompt_done=on_prompt_done,
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
            len(tc.get("prompt_results", [])) for tc in results["direct_test_results"]
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


def _parse_tool_findings(tool_name: str, stdout: str, scenario: dict) -> list:
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
