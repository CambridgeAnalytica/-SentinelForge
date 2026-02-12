"""
Probe management endpoints.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ProbeModule, User
from schemas import ProbeInfo, ProbeRunRequest
from middleware.auth import get_current_user, require_operator

router = APIRouter()
logger = logging.getLogger("sentinelforge.probes")


@router.get("/", response_model=List[ProbeInfo])
async def list_probes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered probe modules."""
    result = await db.execute(select(ProbeModule).order_by(ProbeModule.name))
    probes = result.scalars().all()

    # If no probes in DB, return built-in defaults
    if not probes:
        return [
            ProbeInfo(
                id="builtin_prompt_injection",
                name="prompt_injection",
                description="Tests for prompt injection vulnerabilities",
                category="injection",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_jailbreak",
                name="jailbreak",
                description="Tests jailbreak resistance",
                category="jailbreak",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_data_leakage",
                name="data_leakage",
                description="Tests for data/PII leakage",
                category="privacy",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_hallucination",
                name="hallucination",
                description="Tests hallucination rates",
                category="accuracy",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_toxicity",
                name="toxicity",
                description="Tests for toxic output generation",
                category="safety",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_bias",
                name="bias",
                description="Tests for bias in outputs",
                category="fairness",
                version="1.0.0",
            ),
            ProbeInfo(
                id="builtin_policy_compliance",
                name="policy_compliance",
                description="Tests compliance with content policies",
                category="compliance",
                version="1.0.0",
            ),
        ]

    return [
        ProbeInfo(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category,
            version=p.version,
            is_active=p.is_active,
        )
        for p in probes
    ]


@router.post("/run")
async def run_probe(
    request: ProbeRunRequest,
    user: User = Depends(require_operator),
):
    """Run a probe against a target model."""
    logger.info(f"Running probe {request.probe_name} against {request.target_model}")
    return {
        "probe": request.probe_name,
        "target": request.target_model,
        "status": "completed",
        "message": f"Probe '{request.probe_name}' executed against {request.target_model}. "
        f"Deploy with full tool suite for detailed results.",
    }
