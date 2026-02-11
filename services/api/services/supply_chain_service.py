"""
Supply Chain Security Scanner Service.

Scans model dependencies, training data provenance, model cards,
and licensing for security and compliance risks.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import SupplyChainScan, new_uuid

logger = logging.getLogger("sentinelforge.supply_chain")

# Available check types
CHECK_TYPES = {
    "dependencies": "Scan Python/npm dependencies for known vulnerabilities",
    "model_card": "Validate model card completeness and claims",
    "license": "Check model license compatibility and restrictions",
    "data_provenance": "Verify training data sources and consent",
    "signature": "Verify model file integrity and signatures",
}

# Known risky licenses for commercial use
RISKY_LICENSES = [
    "cc-by-nc-*",      # Non-commercial restriction
    "gpl-3.0",         # Copyleft requirement
    "agpl-3.0",        # Network copyleft
    "unknown",         # No license specified
    "other",           # Non-standard license
]


async def scan_model(
    db: AsyncSession,
    model_source: str,
    checks: list[str],
    user_id: str,
) -> SupplyChainScan:
    """Run supply chain security scan on a model."""
    invalid_checks = [c for c in checks if c not in CHECK_TYPES]
    if invalid_checks:
        raise ValueError(f"Invalid check types: {invalid_checks}. Must be one of: {list(CHECK_TYPES.keys())}")

    logger.info(f"Supply chain scan: source={model_source}, checks={checks}")

    results = {}
    total_issues = 0

    for check in checks:
        check_result, issues = await _run_check(model_source, check)
        results[check] = check_result
        total_issues += issues

    risk_level = _assess_risk(total_issues)

    scan = SupplyChainScan(
        id=new_uuid(),
        model_source=model_source,
        checks_requested=checks,
        results=results,
        risk_level=risk_level,
        issues_found=total_issues,
        user_id=user_id,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    logger.info(f"Supply chain scan complete: issues={total_issues}, risk={risk_level}")
    return scan


async def list_scans(
    db: AsyncSession,
    model_source: Optional[str] = None,
) -> list[SupplyChainScan]:
    """List supply chain scans."""
    query = select(SupplyChainScan).order_by(SupplyChainScan.created_at.desc())
    if model_source:
        query = query.where(SupplyChainScan.model_source == model_source)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_scan(db: AsyncSession, scan_id: str) -> Optional[SupplyChainScan]:
    """Get a specific scan."""
    result = await db.execute(select(SupplyChainScan).where(SupplyChainScan.id == scan_id))
    return result.scalar_one_or_none()


def _assess_risk(issues: int) -> str:
    """Assess risk level based on issue count."""
    if issues == 0:
        return "low"
    elif issues <= 3:
        return "medium"
    elif issues <= 7:
        return "high"
    return "critical"


async def _run_check(model_source: str, check_type: str) -> tuple[dict, int]:
    """Run a specific supply chain check."""
    if check_type == "dependencies":
        return await _check_dependencies(model_source)
    elif check_type == "model_card":
        return await _check_model_card(model_source)
    elif check_type == "license":
        return await _check_license(model_source)
    elif check_type == "data_provenance":
        return await _check_data_provenance(model_source)
    elif check_type == "signature":
        return await _check_signature(model_source)
    return {"error": f"Unknown check: {check_type}"}, 0


async def _check_dependencies(model_source: str) -> tuple[dict, int]:
    """Scan model dependencies for known CVEs."""
    # TODO: Integrate with pip-audit / safety in v1.2
    return {
        "check": "dependencies",
        "status": "framework_ready",
        "packages_scanned": 0,
        "vulnerabilities": [],
        "summary": "Dependency scanner ready. Will scan requirements.txt and package manifests.",
    }, 0


async def _check_model_card(model_source: str) -> tuple[dict, int]:
    """Validate model card completeness."""
    required_fields = [
        "model_details", "intended_use", "limitations",
        "training_data", "evaluation_results", "ethical_considerations",
    ]

    # TODO: Fetch actual model card from HuggingFace API in v1.2
    return {
        "check": "model_card",
        "status": "framework_ready",
        "required_fields": required_fields,
        "present_fields": [],
        "missing_fields": required_fields,
        "completeness_score": 0.0,
        "summary": "Model card validator ready. Will fetch and validate from HuggingFace Hub.",
    }, 0


async def _check_license(model_source: str) -> tuple[dict, int]:
    """Check model license compatibility."""
    # TODO: Fetch actual license from model source in v1.2
    return {
        "check": "license",
        "status": "framework_ready",
        "detected_license": "unknown",
        "risky_licenses": RISKY_LICENSES,
        "commercial_use_allowed": None,
        "attribution_required": None,
        "summary": "License checker ready. Will parse SPDX identifiers and flag restrictions.",
    }, 0


async def _check_data_provenance(model_source: str) -> tuple[dict, int]:
    """Verify training data sources and consent."""
    # TODO: Parse model card for data sources in v1.2
    return {
        "check": "data_provenance",
        "status": "framework_ready",
        "data_sources": [],
        "consent_verified": None,
        "pii_risk": "unknown",
        "summary": "Data provenance checker ready. Will analyze model card and dataset cards.",
    }, 0


async def _check_signature(model_source: str) -> tuple[dict, int]:
    """Verify model file signatures and integrity."""
    # TODO: Check cosign signatures on model files in v1.2
    return {
        "check": "signature",
        "status": "framework_ready",
        "signature_found": False,
        "integrity_verified": None,
        "summary": "Signature verifier ready. Will check model file hashes and cosign signatures.",
    }, 0
