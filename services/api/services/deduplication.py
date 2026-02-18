"""
Findings deduplication — fingerprint-based detection of new vs. recurring findings.
"""

import hashlib
import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Finding

logger = logging.getLogger("sentinelforge.dedup")


def compute_fingerprint(
    title: str,
    tool_name: str,
    severity: str,
    mitre_technique: Optional[str] = None,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint for a finding.

    The fingerprint is based on the canonical combination of:
    - title (lowercased, stripped)
    - tool_name (lowercased, stripped)
    - severity (lowercased)
    - mitre_technique (lowercased, stripped; empty string if None)

    This means two findings from different runs with the same title, tool,
    severity, and MITRE technique will produce the same fingerprint.
    """
    canonical = "|".join([
        title.strip().lower(),
        tool_name.strip().lower(),
        severity.strip().lower(),
        (mitre_technique or "").strip().lower(),
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def classify_findings(run_id: str, db: AsyncSession) -> dict:
    """
    Classify findings for a given run as NEW or RECURRING.

    For each finding in the run:
    1. Compute its fingerprint (if not already set)
    2. Check if any other finding with the same fingerprint exists in a *previous* run
    3. Set is_new=True if first occurrence, is_new=False if recurring

    Returns summary dict: {"new": int, "recurring": int, "total": int}
    """
    result = await db.execute(
        select(Finding).where(Finding.run_id == run_id)
    )
    findings = result.scalars().all()

    stats = {"new": 0, "recurring": 0, "total": len(findings)}

    for finding in findings:
        # Compute fingerprint if missing
        fp = compute_fingerprint(
            title=finding.title,
            tool_name=finding.tool_name,
            severity=finding.severity,
            mitre_technique=finding.mitre_technique,
        )
        finding.fingerprint = fp

        # Check for prior occurrences in other runs
        prior = await db.execute(
            select(func.count(Finding.id)).where(
                Finding.fingerprint == fp,
                Finding.run_id != run_id,
            )
        )
        prior_count = prior.scalar() or 0

        finding.is_new = prior_count == 0
        if finding.is_new:
            stats["new"] += 1
        else:
            stats["recurring"] += 1

    await db.flush()
    logger.info(
        f"Dedup run {run_id}: {stats['new']} new, {stats['recurring']} recurring "
        f"out of {stats['total']} findings"
    )
    return stats
