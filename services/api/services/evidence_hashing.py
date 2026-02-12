"""
Evidence hashing service for tamper-proof finding chains.

Each finding's SHA-256 hash includes the previous finding's hash,
creating a verifiable chain that detects modifications or deletions.
"""

import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger("sentinelforge.evidence")


def compute_evidence_hash(
    evidence: dict,
    run_id: str,
    tool_name: str,
    previous_hash: Optional[str] = None,
) -> str:
    """Compute SHA-256 hash of evidence data for tamper detection.

    Creates a hash chain: each finding's hash includes the previous finding's hash,
    making it impossible to modify or remove findings without breaking the chain.
    """
    payload = json.dumps(
        {
            "evidence": evidence,
            "run_id": run_id,
            "tool_name": tool_name,
            "previous_hash": previous_hash or "genesis",
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_evidence_chain(findings: list) -> dict:
    """Verify the integrity of a finding chain.

    Findings must be ordered by created_at ascending.

    Returns:
        {"valid": bool, "total": int, "verified": int, "broken_at": str|None}
    """
    previous_hash = None
    verified = 0

    for finding in findings:
        if not finding.evidence_hash:
            # Findings without hashes (pre-v1.2) are skipped
            previous_hash = finding.evidence_hash
            continue

        expected = compute_evidence_hash(
            evidence=finding.evidence or {},
            run_id=finding.run_id,
            tool_name=finding.tool_name,
            previous_hash=previous_hash,
        )

        if expected != finding.evidence_hash:
            logger.warning(
                f"Evidence chain broken at finding {finding.id}: "
                f"expected={expected[:16]}..., got={finding.evidence_hash[:16]}..."
            )
            return {
                "valid": False,
                "total": len(findings),
                "verified": verified,
                "broken_at": finding.id,
            }

        previous_hash = finding.evidence_hash
        verified += 1

    return {
        "valid": True,
        "total": len(findings),
        "verified": verified,
        "broken_at": None,
    }
