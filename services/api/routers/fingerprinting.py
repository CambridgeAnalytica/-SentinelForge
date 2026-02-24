"""
Model Fingerprinting router — identify unknown LLMs via behavioral probes.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, AsyncSessionLocal
from middleware.auth import get_current_user, require_operator
from models import AttackRun, RunStatus, User, Finding, Severity
from schemas import FingerprintRequest, FingerprintResponse, FingerprintDetail

router = APIRouter()
logger = logging.getLogger("sentinelforge.fingerprinting")


@router.post("/run", response_model=FingerprintResponse, status_code=201)
async def start_fingerprint(
    request: FingerprintRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Launch a model fingerprinting run."""
    run = AttackRun(
        scenario_id="model_fingerprinting",
        target_model=request.target_model,
        status=RunStatus.QUEUED,
        run_type="fingerprint",
        config=request.config,
        user_id=user.id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    logger.info(
        f"Fingerprint run '{run.id}' queued for {request.target_model} by {user.username}"
    )

    asyncio.create_task(
        _run_fingerprint_async(
            run.id,
            request.target_model,
            request.provider,
            request.config,
            request.probe_categories,
        )
    )

    return FingerprintResponse(
        id=run.id,
        target_model=run.target_model,
        status=run.status.value,
        run_type="fingerprint",
        progress=0.0,
        created_at=run.created_at,
    )


@router.get("/runs", response_model=list[FingerprintResponse])
async def list_fingerprints(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all fingerprint runs."""
    result = await db.execute(
        select(AttackRun)
        .where(AttackRun.run_type == "fingerprint")
        .order_by(AttackRun.created_at.desc())
    )
    runs = result.scalars().all()
    return [
        FingerprintResponse(
            id=r.id,
            target_model=r.target_model,
            status=r.status.value if hasattr(r.status, "value") else r.status,
            run_type="fingerprint",
            progress=r.progress or 0.0,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=FingerprintDetail)
async def get_fingerprint(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed fingerprint results."""
    result = await db.execute(
        select(AttackRun)
        .where(AttackRun.id == run_id, AttackRun.run_type == "fingerprint")
        .options(selectinload(AttackRun.findings))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Fingerprint run not found")

    results = run.results or {}
    findings = []
    if run.findings:
        findings = [
            {
                "id": f.id,
                "title": f.title,
                "severity": (
                    f.severity.value if hasattr(f.severity, "value") else f.severity
                ),
                "description": f.description,
            }
            for f in run.findings
        ]

    return FingerprintDetail(
        id=run.id,
        target_model=run.target_model,
        status=run.status.value if hasattr(run.status, "value") else run.status,
        run_type="fingerprint",
        progress=run.progress or 0.0,
        created_at=run.created_at,
        results=results,
        findings=findings,
        completed_at=run.completed_at,
    )


async def _run_fingerprint_async(
    run_id: str,
    target_model: str,
    provider: str,
    config: dict,
    probe_categories: list,
):
    """Background task: run fingerprinting probes and update DB."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
            run = result.scalar_one_or_none()
            if not run:
                return
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Get adapter
            adapter = _get_fingerprint_adapter(provider, target_model, config)
            if not adapter:
                raise ValueError(
                    f"Could not create adapter for provider '{provider}'. "
                    "Check API key configuration."
                )

            # Filter probes by category
            from data.model_signatures import FINGERPRINT_PROBES

            if "all" in probe_categories or not probe_categories:
                probes = FINGERPRINT_PROBES
            else:
                probes = [
                    p for p in FINGERPRINT_PROBES if p["category"] in probe_categories
                ]

            # Progress callback
            async def on_progress(progress: float):
                r2 = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
                r = r2.scalar_one_or_none()
                if r:
                    r.progress = progress
                    await db.commit()

            # Run fingerprinting
            from services.fingerprinting_service import run_fingerprint

            results = await run_fingerprint(adapter, probes, on_progress)

            # Create finding for the identification result
            top = results.get("top_matches", [])
            if top:
                best = top[0]
                confidence = best["confidence"]
                severity = (
                    Severity.INFO
                    if confidence < 0.5
                    else Severity.LOW if confidence < 0.7 else Severity.MEDIUM
                )
                finding = Finding(
                    run_id=run_id,
                    tool_name="fingerprinting",
                    severity=severity,
                    title=f"Model identified: {best['model']} ({confidence:.0%} confidence)",
                    description=(
                        f"Behavioral analysis suggests this endpoint is running {best['model']} "
                        f"({best['family']} family) with {confidence:.0%} confidence.\n\n"
                        f"Runner-up: {top[1]['model']} ({top[1]['confidence']:.0%})\n"
                        f"Third: {top[2]['model']} ({top[2]['confidence']:.0%})"
                        if len(top) >= 3
                        else f"Behavioral analysis suggests {best['model']}."
                    ),
                    mitre_technique="AML.T0044",
                    evidence={
                        "top_matches": top,
                        "category_scores": results.get("category_scores", {}),
                        "profile": results.get("behavioral_profile", ""),
                    },
                )
                db.add(finding)

            # Update run
            r3 = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
            run = r3.scalar_one_or_none()
            if run:
                run.status = RunStatus.COMPLETED
                run.progress = 1.0
                run.results = results
                run.completed_at = datetime.now(timezone.utc)
                await db.commit()

            logger.info(f"Fingerprint run '{run_id}' completed")

        except Exception as e:
            logger.error(f"Fingerprint run '{run_id}' failed: {e}")
            try:
                r4 = await db.execute(select(AttackRun).where(AttackRun.id == run_id))
                run = r4.scalar_one_or_none()
                if run:
                    run.status = RunStatus.FAILED
                    run.error_message = str(e)
                    run.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


def _get_fingerprint_adapter(provider: str, target_model: str, config: dict):
    """Create an appropriate model adapter for fingerprinting."""
    from adapters.models import get_adapter

    p = provider.lower()

    key_map = {
        "openai": "OPENAI_API_KEY",
        "ollama": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "azure_openai": "AZURE_OPENAI_API_KEY",
        "bedrock": "AWS_ACCESS_KEY_ID",
        "custom": "CUSTOM_GATEWAY_API_KEY",
    }

    # For ollama, use OpenAI adapter with base URL
    if p == "ollama":
        base_url = config.get(
            "base_url", os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        )
        from adapters.models import OpenAIAdapter

        return OpenAIAdapter(
            api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
            model=target_model,
            base_url=base_url,
        )

    if p == "custom":
        from adapters.models import CustomGatewayAdapter

        return CustomGatewayAdapter(
            base_url=config.get("base_url", os.environ.get("CUSTOM_GATEWAY_URL", "")),
            api_key=os.environ.get("CUSTOM_GATEWAY_API_KEY", config.get("api_key", "")),
            model=target_model,
            auth_header=config.get("auth_header", "Authorization"),
            auth_prefix=config.get("auth_prefix", "Bearer"),
            request_template=config.get("request_template", "openai"),
            response_path=config.get("response_path", ""),
        )

    # Standard providers
    env_key = key_map.get(p, "")
    if p != "custom" and env_key and not os.environ.get(env_key):
        return None

    api_key = os.environ.get(env_key, "") if env_key else ""
    base_url = config.get("base_url", "")

    kwargs = {"api_key": api_key, "model": target_model}
    if base_url:
        kwargs["base_url"] = base_url

    return get_adapter(p, **kwargs)
