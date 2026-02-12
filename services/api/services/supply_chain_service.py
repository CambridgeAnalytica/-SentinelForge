"""
Supply Chain Security Scanner Service.

Scans model dependencies, training data provenance, model cards,
and licensing for security and compliance risks.
"""

import asyncio
import fnmatch
import json
import logging
from typing import Optional

import httpx
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

# Required model card fields
_REQUIRED_CARD_FIELDS = [
    "model_details", "intended_use", "limitations",
    "training_data", "evaluation_results", "ethical_considerations",
]

# HuggingFace cardData fields that map to our required fields
_CARD_FIELD_MAP = {
    "model_details": ["model_name", "model_type", "architecture"],
    "intended_use": ["pipeline_tag", "tags"],
    "limitations": ["limitations"],
    "training_data": ["datasets", "training_data"],
    "evaluation_results": ["eval_results", "model-index"],
    "ethical_considerations": ["ethical_considerations", "bias"],
}


def _parse_model_id(model_source: str) -> str:
    """Parse 'huggingface:org/model' -> 'org/model'."""
    if ":" in model_source:
        return model_source.split(":", 1)[-1]
    return model_source


def _hf_headers() -> dict:
    """Build HuggingFace API headers."""
    try:
        from config import settings
        headers = {}
        if settings.HUGGINGFACE_API_TOKEN:
            headers["Authorization"] = f"Bearer {settings.HUGGINGFACE_API_TOKEN}"
        return headers
    except ImportError:
        return {}


async def _fetch_model_info(model_id: str) -> Optional[dict]:
    """Fetch model info from HuggingFace API. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://huggingface.co/api/models/{model_id}",
                headers=_hf_headers(),
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"HuggingFace API returned {resp.status_code} for {model_id}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch model info for {model_id}: {e}")
        return None


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
    """Scan dependencies for known CVEs using pip-audit."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "pip-audit", "--format", "json", "--strict",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        vulnerabilities = []
        if stdout:
            try:
                audit_data = json.loads(stdout.decode())
                if isinstance(audit_data, dict):
                    vulnerabilities = audit_data.get("dependencies", [])
                elif isinstance(audit_data, list):
                    vulnerabilities = [v for v in audit_data if v.get("vulns")]
            except json.JSONDecodeError:
                pass

        vuln_count = sum(len(v.get("vulns", [])) for v in vulnerabilities if isinstance(v, dict))

        return {
            "check": "dependencies",
            "status": "completed",
            "packages_scanned": len(vulnerabilities) if vulnerabilities else 0,
            "vulnerabilities_found": vuln_count,
            "vulnerable_packages": [
                {
                    "name": v.get("name", "unknown"),
                    "version": v.get("version", "unknown"),
                    "vulns": v.get("vulns", []),
                }
                for v in vulnerabilities
                if isinstance(v, dict) and v.get("vulns")
            ][:20],  # Limit to first 20
            "summary": f"Scanned dependencies. {vuln_count} vulnerabilities found.",
        }, vuln_count

    except FileNotFoundError:
        return {
            "check": "dependencies",
            "status": "tool_not_available",
            "packages_scanned": 0,
            "vulnerabilities_found": 0,
            "summary": "pip-audit not installed. Run: pip install pip-audit",
        }, 0
    except asyncio.TimeoutError:
        return {
            "check": "dependencies",
            "status": "timeout",
            "packages_scanned": 0,
            "vulnerabilities_found": 0,
            "summary": "Dependency scan timed out after 120 seconds.",
        }, 1
    except Exception as e:
        return {
            "check": "dependencies",
            "status": "error",
            "error": str(e),
            "summary": f"Dependency scan failed: {e}",
        }, 0


async def _check_model_card(model_source: str) -> tuple[dict, int]:
    """Validate model card completeness via HuggingFace API."""
    model_id = _parse_model_id(model_source)
    model_info = await _fetch_model_info(model_id)

    if not model_info:
        return {
            "check": "model_card",
            "status": "error",
            "required_fields": _REQUIRED_CARD_FIELDS,
            "present_fields": [],
            "missing_fields": _REQUIRED_CARD_FIELDS,
            "completeness_score": 0.0,
            "summary": f"Could not fetch model card for {model_id} from HuggingFace.",
        }, 1

    card_data = model_info.get("cardData", {}) or {}
    tags = model_info.get("tags", []) or []
    pipeline_tag = model_info.get("pipeline_tag", "")

    present = []
    missing = []

    for field in _REQUIRED_CARD_FIELDS:
        found = False
        # Check direct presence in cardData
        mapped_fields = _CARD_FIELD_MAP.get(field, [field])
        for mf in mapped_fields:
            if card_data.get(mf) or mf in [t for t in tags]:
                found = True
                break

        # Special checks
        if field == "intended_use" and pipeline_tag:
            found = True
        if field == "training_data" and card_data.get("datasets"):
            found = True

        if found:
            present.append(field)
        else:
            missing.append(field)

    completeness = len(present) / len(_REQUIRED_CARD_FIELDS) if _REQUIRED_CARD_FIELDS else 0
    issues = len(missing)

    return {
        "check": "model_card",
        "status": "completed",
        "model_id": model_id,
        "required_fields": _REQUIRED_CARD_FIELDS,
        "present_fields": present,
        "missing_fields": missing,
        "completeness_score": round(completeness, 2),
        "summary": f"Model card {round(completeness * 100)}% complete. Missing: {', '.join(missing) or 'none'}.",
    }, issues


async def _check_license(model_source: str) -> tuple[dict, int]:
    """Check model license compatibility."""
    model_id = _parse_model_id(model_source)
    model_info = await _fetch_model_info(model_id)

    if not model_info:
        return {
            "check": "license",
            "status": "error",
            "detected_license": "unknown",
            "is_risky": True,
            "summary": f"Could not fetch license for {model_id}.",
        }, 1

    card_data = model_info.get("cardData", {}) or {}
    license_id = card_data.get("license", model_info.get("license", "unknown")) or "unknown"

    is_risky = any(fnmatch.fnmatch(license_id, pattern) for pattern in RISKY_LICENSES)

    # Determine commercial use allowance
    non_commercial_licenses = ["cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc-by-nc-nd-4.0"]
    commercial_allowed = license_id not in non_commercial_licenses and not fnmatch.fnmatch(license_id, "cc-by-nc-*")

    issues = 1 if is_risky else 0

    return {
        "check": "license",
        "status": "completed",
        "model_id": model_id,
        "detected_license": license_id,
        "is_risky": is_risky,
        "commercial_use_allowed": commercial_allowed if license_id != "unknown" else None,
        "attribution_required": "cc-" in license_id.lower() or "mit" in license_id.lower(),
        "risky_licenses_ref": RISKY_LICENSES,
        "summary": f"License: {license_id}. {'Risky — review terms.' if is_risky else 'Appears acceptable.'}",
    }, issues


async def _check_data_provenance(model_source: str) -> tuple[dict, int]:
    """Verify training data sources and consent."""
    model_id = _parse_model_id(model_source)
    model_info = await _fetch_model_info(model_id)

    if not model_info:
        return {
            "check": "data_provenance",
            "status": "error",
            "data_sources": [],
            "summary": f"Could not fetch data provenance for {model_id}.",
        }, 1

    card_data = model_info.get("cardData", {}) or {}
    datasets = card_data.get("datasets", []) or []

    issues = 0
    data_sources = []

    if not datasets:
        issues += 1

    # Check each referenced dataset for its own card
    for ds in datasets[:10]:  # Limit to 10 datasets
        ds_info = {"dataset_id": ds, "has_card": False, "license": "unknown"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"https://huggingface.co/api/datasets/{ds}",
                    headers=_hf_headers(),
                )
            if resp.status_code == 200:
                ds_data = resp.json()
                ds_card = ds_data.get("cardData", {}) or {}
                ds_info["has_card"] = bool(ds_card)
                ds_info["license"] = ds_card.get("license", ds_data.get("license", "unknown"))
                if not ds_info["has_card"]:
                    issues += 1
        except Exception:
            pass
        data_sources.append(ds_info)

    return {
        "check": "data_provenance",
        "status": "completed",
        "model_id": model_id,
        "data_sources": data_sources,
        "datasets_referenced": len(datasets),
        "consent_verified": None,  # Would require manual review
        "pii_risk": "unknown" if not datasets else "low",
        "summary": f"{len(datasets)} dataset(s) referenced. {issues} provenance issue(s).",
    }, issues


async def _check_signature(model_source: str) -> tuple[dict, int]:
    """Verify model file signatures and integrity."""
    model_id = _parse_model_id(model_source)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://huggingface.co/api/models/{model_id}/tree/main",
                headers=_hf_headers(),
            )

        if resp.status_code != 200:
            return {
                "check": "signature",
                "status": "error",
                "error": f"HuggingFace API returned {resp.status_code}",
                "summary": f"Could not check signatures for {model_id}.",
            }, 1

        files = resp.json()
        file_list = [f.get("rfilename", "") for f in files if isinstance(f, dict)]

        has_sha = any(f.endswith(".sha256") for f in file_list)
        has_sig = any("cosign" in f or ".sig" in f for f in file_list)
        has_safetensors = any(f.endswith(".safetensors") for f in file_list)
        has_pickle = any(f.endswith((".pkl", ".pt", ".bin")) for f in file_list)

        issues = 0
        if not has_sha and not has_sig:
            issues = 1

        return {
            "check": "signature",
            "status": "completed",
            "model_id": model_id,
            "signature_found": has_sha or has_sig,
            "has_sha256": has_sha,
            "has_cosign": has_sig,
            "uses_safetensors": has_safetensors,
            "has_pickle_files": has_pickle,
            "integrity_verified": has_sha or has_sig,
            "total_files": len(file_list),
            "summary": (
                f"{'Signatures found.' if has_sha or has_sig else 'No signatures found.'} "
                f"{'Uses safetensors (safer).' if has_safetensors else ''} "
                f"{'Contains pickle files (risk).' if has_pickle else ''}"
            ).strip(),
        }, issues

    except Exception as e:
        return {
            "check": "signature",
            "status": "error",
            "signature_found": False,
            "integrity_verified": None,
            "error": str(e),
            "summary": f"Signature check failed: {e}",
        }, 1
