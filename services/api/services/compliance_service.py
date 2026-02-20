"""
Compliance Service — auto-tag findings, aggregate by framework, generate PDF reports.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data.compliance_frameworks import (
    lookup_compliance_tags,
    get_framework_categories,
    SUPPORTED_FRAMEWORKS,
)
from models import Finding

logger = logging.getLogger("sentinelforge.compliance")


def tag_finding(finding: dict) -> List[Dict[str, str]]:
    """Auto-tag a single finding with compliance framework categories.

    Uses the finding's `mitre_technique` field to look up relevant
    OWASP ML Top 10, NIST AI RMF, and EU AI Act categories.
    """
    technique = finding.get("mitre_technique", "")
    if not technique:
        return []
    return lookup_compliance_tags(technique)


def aggregate_by_framework(
    findings: List[dict],
    framework: str,
) -> Dict[str, Any]:
    """Aggregate findings into compliance categories for a specific framework.

    Returns a summary with per-category counts and severity distribution.
    """
    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError(
            f"Unknown framework: {framework}. Supported: {SUPPORTED_FRAMEWORKS}"
        )

    categories = get_framework_categories(framework)
    summary: Dict[str, Dict[str, Any]] = {}

    for cat_id, cat in categories.items():
        summary[cat_id] = {
            "id": cat_id,
            "name": cat["name"],
            "description": cat["description"],
            "total_findings": 0,
            "by_severity": defaultdict(int),
            "finding_ids": [],
        }

    # Tag each finding and bin into categories
    for finding in findings:
        tags = tag_finding(finding)
        for tag in tags:
            if tag["framework"] != framework:
                continue
            cat_id = tag["category_id"]
            if cat_id in summary:
                summary[cat_id]["total_findings"] += 1
                severity = finding.get("severity", "unknown")
                summary[cat_id]["by_severity"][severity] += 1
                fid = finding.get("id", "")
                if fid:
                    summary[cat_id]["finding_ids"].append(fid)

    # Convert defaultdicts for serialization
    for cat_id in summary:
        summary[cat_id]["by_severity"] = dict(summary[cat_id]["by_severity"])

    total_findings = sum(c["total_findings"] for c in summary.values())
    total_critical = sum(c["by_severity"].get("critical", 0) for c in summary.values())
    total_high = sum(c["by_severity"].get("high", 0) for c in summary.values())

    # Overall risk score (0-100)
    risk_score = min(
        100,
        total_critical * 25
        + total_high * 10
        + (total_findings - total_critical - total_high) * 3,
    )

    return {
        "framework": framework,
        "framework_name": _framework_display_name(framework),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_findings": total_findings,
        "risk_score": risk_score,
        "categories": list(summary.values()),
    }


async def get_all_findings_dicts(db: AsyncSession) -> List[dict]:
    """Load all findings from DB as dicts for compliance processing."""
    result = await db.execute(select(Finding))
    findings = result.scalars().all()
    return [
        {
            "id": f.id,
            "tool_name": f.tool_name,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "mitre_technique": f.mitre_technique,
            "evidence": f.evidence,
            "remediation": f.remediation,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in findings
    ]


def generate_compliance_pdf(
    summary: Dict[str, Any],
    framework: str,
) -> bytes:
    """Generate an auditor-friendly PDF compliance report using WeasyPrint."""
    html = _render_compliance_html(summary, framework)

    try:
        from weasyprint import HTML

        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes
    except ImportError:
        logger.warning("WeasyPrint not available — returning HTML as fallback")
        return html.encode("utf-8")


def _render_compliance_html(summary: Dict[str, Any], framework: str) -> str:
    """Render compliance summary as styled HTML for PDF conversion."""
    framework_name = summary.get("framework_name", framework)
    generated_at = summary.get("generated_at", "")
    risk_score = summary.get("risk_score", 0)
    total = summary.get("total_findings", 0)

    risk_color = (
        "#e74c3c" if risk_score >= 70 else "#f39c12" if risk_score >= 40 else "#27ae60"
    )

    categories_html = ""
    for cat in summary.get("categories", []):
        if cat["total_findings"] == 0:
            status = '<span style="color: #27ae60; font-weight: bold;">✓ PASS</span>'
        else:
            status = f'<span style="color: #e74c3c; font-weight: bold;">⚠ {cat["total_findings"]} finding(s)</span>'

        severity_pills = ""
        for sev, count in cat.get("by_severity", {}).items():
            sev_color = {
                "critical": "#e74c3c",
                "high": "#e67e22",
                "medium": "#f1c40f",
                "low": "#3498db",
            }.get(sev, "#95a5a6")
            severity_pills += f'<span style="background: {sev_color}; color: white; padding: 2px 8px; border-radius: 12px; margin-right: 4px; font-size: 12px;">{sev}: {count}</span>'

        categories_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee;"><strong>{cat['id']}</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{cat['name']}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{status}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee;">{severity_pills}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #333; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #16213e; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 14px; margin-bottom: 30px; }}
        .risk-badge {{ display: inline-block; padding: 8px 20px; border-radius: 8px; color: white; font-size: 18px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #16213e; color: white; padding: 12px; text-align: left; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>🛡️ SentinelForge Compliance Report</h1>
    <p class="meta">Framework: <strong>{framework_name}</strong> | Generated: {generated_at}</p>

    <h2>Executive Summary</h2>
    <p>
        Risk Score: <span class="risk-badge" style="background: {risk_color};">{risk_score}/100</span>
        &nbsp;&nbsp; Total Findings: <strong>{total}</strong>
    </p>

    <h2>Compliance Categories</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Status</th>
                <th>Severity</th>
            </tr>
        </thead>
        <tbody>
            {categories_html}
        </tbody>
    </table>

    <div class="footer">
        <p>This report was automatically generated by SentinelForge v2.4.1.<br>
        For audit purposes: findings are mapped via MITRE ATLAS technique identifiers.</p>
    </div>
</body>
</html>"""


def _framework_display_name(framework: str) -> str:
    return {
        "owasp_llm_top10": "OWASP Top 10 for LLM Applications",
        "owasp_ml_top10": "OWASP Machine Learning Top 10",
        "nist_ai_rmf": "NIST AI Risk Management Framework",
        "eu_ai_act": "EU Artificial Intelligence Act",
        "arcanum_pi": "Arcanum Prompt Injection Taxonomy",
    }.get(framework, framework)
