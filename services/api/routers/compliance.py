"""
Compliance router — aggregate findings by framework and generate PDF reports.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from data.compliance_frameworks import SUPPORTED_FRAMEWORKS
from middleware.auth import get_current_user
from models import User
from services.compliance_service import (
    aggregate_by_framework,
    generate_compliance_pdf,
    get_all_findings_dicts,
)

router = APIRouter()


_FRAMEWORK_NAMES = {
    "owasp_llm_top10": "OWASP Top 10 for LLM Applications",
    "owasp_ml_top10": "OWASP Machine Learning Top 10",
    "nist_ai_rmf": "NIST AI Risk Management Framework",
    "eu_ai_act": "EU Artificial Intelligence Act",
    "arcanum_pi": "Arcanum Prompt Injection Taxonomy",
}


@router.get("/frameworks")
async def list_frameworks(user: User = Depends(get_current_user)):
    """List supported compliance frameworks with their categories."""
    from data.compliance_frameworks import get_framework_categories

    results = []
    for fw_id in SUPPORTED_FRAMEWORKS:
        cats = get_framework_categories(fw_id)
        cat_list = []
        for cid, c in cats.items():
            entry = {
                "id": cid,
                "name": c["name"],
                "description": c.get("description", ""),
            }
            # Include Arcanum-specific fields
            for extra in ("severity_baseline", "subcategories", "test_types"):
                if extra in c:
                    entry[extra] = c[extra]
            cat_list.append(entry)
        results.append(
            {
                "id": fw_id,
                "name": _FRAMEWORK_NAMES.get(fw_id, fw_id),
                "categories": cat_list,
            }
        )
    return {"frameworks": results}


@router.get("/summary")
async def compliance_summary(
    framework: str = Query(
        ...,
        description="Compliance framework ID",
        enum=SUPPORTED_FRAMEWORKS,
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance summary aggregating all findings by framework categories.

    Auto-tags findings with the selected framework's categories using
    MITRE ATLAS technique mapping.
    """
    if framework not in SUPPORTED_FRAMEWORKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown framework. Supported: {', '.join(SUPPORTED_FRAMEWORKS)}",
        )

    findings = await get_all_findings_dicts(db)
    summary = aggregate_by_framework(findings, framework)
    return summary


@router.get("/report")
async def compliance_report(
    framework: str = Query(
        ...,
        description="Compliance framework ID",
        enum=SUPPORTED_FRAMEWORKS,
    ),
    format: str = Query("pdf", description="Report format (pdf or html)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download a compliance report.

    Produces an auditor-friendly PDF (or HTML) with executive summary,
    per-category breakdown, and severity distribution.
    """
    if framework not in SUPPORTED_FRAMEWORKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown framework. Supported: {', '.join(SUPPORTED_FRAMEWORKS)}",
        )

    findings = await get_all_findings_dicts(db)
    summary = aggregate_by_framework(findings, framework)

    if format == "pdf":
        pdf_bytes = generate_compliance_pdf(summary, framework)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=sentinelforge_{framework}_report.pdf"
            },
        )
    else:
        # Return JSON summary
        return summary
