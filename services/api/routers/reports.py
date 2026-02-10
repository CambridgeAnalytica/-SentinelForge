"""
Report generation and management endpoints.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Report, AttackRun, Finding, ReportFormat, User
from schemas import ReportRequest, ReportResponse
from middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("sentinelforge.reports")


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated reports."""
    result = await db.execute(select(Report).order_by(Report.generated_at.desc()).limit(50))
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=r.id,
            run_id=r.run_id,
            format=r.format.value,
            file_path=r.file_path,
            generated_at=r.generated_at,
        )
        for r in reports
    ]


@router.post("/generate", response_model=List[ReportResponse])
async def generate_report(
    request: ReportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate report(s) for an attack run."""
    # Verify run exists
    run_result = await db.execute(select(AttackRun).where(AttackRun.id == request.run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Attack run not found")

    # Load findings
    findings_result = await db.execute(select(Finding).where(Finding.run_id == request.run_id))
    findings = findings_result.scalars().all()

    reports = []
    for fmt in request.formats:
        report_format = ReportFormat(fmt)

        if report_format == ReportFormat.HTML:
            content = _generate_html_report(run, findings)
        elif report_format == ReportFormat.JSONL:
            content = _generate_jsonl_report(run, findings)
        else:
            content = _generate_html_report(run, findings)

        report = Report(
            run_id=request.run_id,
            format=report_format,
            file_path=f"reports/{run.id}.{fmt}",
            generated_at=datetime.now(timezone.utc),
        )
        db.add(report)
        await db.flush()

        reports.append(ReportResponse(
            id=report.id,
            run_id=report.run_id,
            format=report.format.value,
            file_path=report.file_path,
            generated_at=report.generated_at,
        ))

    return reports


@router.get("/{report_id}/view")
async def view_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View a generated report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    run_result = await db.execute(select(AttackRun).where(AttackRun.id == report.run_id))
    run = run_result.scalar_one_or_none()

    findings_result = await db.execute(select(Finding).where(Finding.run_id == report.run_id))
    findings = findings_result.scalars().all()

    if report.format == ReportFormat.HTML:
        html = _generate_html_report(run, findings)
        return HTMLResponse(content=html)
    else:
        return {
            "report_id": report.id,
            "run_id": report.run_id,
            "format": report.format.value,
            "data": _generate_report_data(run, findings),
        }


def _generate_report_data(run: AttackRun, findings: list) -> dict:
    """Generate structured report data."""
    severity_counts = {}
    for f in findings:
        sev = f.severity.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "run_id": run.id,
        "scenario": run.scenario_id,
        "target": run.target_model,
        "status": run.status.value,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_findings": len(findings),
        "severity_breakdown": severity_counts,
        "findings": [
            {
                "id": f.id,
                "tool": f.tool_name,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "mitre_technique": f.mitre_technique,
                "remediation": f.remediation,
            }
            for f in findings
        ],
    }


def _generate_html_report(run: AttackRun, findings: list) -> str:
    """Generate HTML report."""
    data = _generate_report_data(run, findings)

    severity_colors = {
        "critical": "#dc2626",
        "high": "#ea580c",
        "medium": "#d97706",
        "low": "#2563eb",
        "info": "#6b7280",
    }

    findings_html = ""
    for f in data["findings"]:
        color = severity_colors.get(f["severity"], "#6b7280")
        findings_html += f"""
        <div class="finding">
            <div class="finding-header">
                <span class="severity" style="background:{color}">{f['severity'].upper()}</span>
                <strong>{f['title']}</strong>
                <span class="tool">{f['tool']}</span>
            </div>
            <p>{f.get('description', 'No description')}</p>
            {'<p><strong>MITRE:</strong> ' + f['mitre_technique'] + '</p>' if f.get('mitre_technique') else ''}
            {'<p><strong>Remediation:</strong> ' + f['remediation'] + '</p>' if f.get('remediation') else ''}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SentinelForge Report - {data['run_id']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        h1 {{ color: #38bdf8; margin-bottom: 0.5rem; }}
        h2 {{ color: #7dd3fc; margin: 1.5rem 0 0.75rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; }}
        .meta {{ background: #1e293b; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }}
        .meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
        .meta-item {{ }}
        .meta-label {{ color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; }}
        .meta-value {{ font-size: 1.1rem; font-weight: 600; margin-top: 0.25rem; }}
        .finding {{ background: #1e293b; border-radius: 8px; padding: 1rem 1.5rem; margin: 0.75rem 0; border-left: 4px solid #334155; }}
        .finding-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap; }}
        .severity {{ padding: 0.15rem 0.5rem; border-radius: 4px; color: white; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
        .tool {{ background: #334155; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }}
        .summary-box {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .stat {{ background: #1e293b; border-radius: 8px; padding: 1rem; text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; color: #38bdf8; }}
        .stat-label {{ font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem; }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #334155; color: #64748b; font-size: 0.85rem; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ SentinelForge Security Report</h1>
        <p style="color:#94a3b8">Enterprise AI Security Testing Results</p>

        <div class="meta">
            <div class="meta-grid">
                <div class="meta-item"><div class="meta-label">Run ID</div><div class="meta-value">{data['run_id'][:12]}…</div></div>
                <div class="meta-item"><div class="meta-label">Scenario</div><div class="meta-value">{data['scenario']}</div></div>
                <div class="meta-item"><div class="meta-label">Target</div><div class="meta-value">{data['target']}</div></div>
                <div class="meta-item"><div class="meta-label">Status</div><div class="meta-value">{data['status'].upper()}</div></div>
            </div>
        </div>

        <h2>Summary</h2>
        <div class="summary-box">
            <div class="stat"><div class="stat-value">{data['total_findings']}</div><div class="stat-label">Total Findings</div></div>
            <div class="stat"><div class="stat-value" style="color:#dc2626">{data['severity_breakdown'].get('critical', 0)}</div><div class="stat-label">Critical</div></div>
            <div class="stat"><div class="stat-value" style="color:#ea580c">{data['severity_breakdown'].get('high', 0)}</div><div class="stat-label">High</div></div>
            <div class="stat"><div class="stat-value" style="color:#d97706">{data['severity_breakdown'].get('medium', 0)}</div><div class="stat-label">Medium</div></div>
            <div class="stat"><div class="stat-value" style="color:#2563eb">{data['severity_breakdown'].get('low', 0)}</div><div class="stat-label">Low</div></div>
        </div>

        <h2>Findings</h2>
        {findings_html if findings_html else '<p style="color:#64748b">No findings recorded for this run.</p>'}

        <div class="footer">
            Generated by SentinelForge v1.0.0 • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        </div>
    </div>
</body>
</html>"""


def _generate_jsonl_report(run: AttackRun, findings: list) -> str:
    """Generate JSONL report."""
    data = _generate_report_data(run, findings)
    lines = []
    lines.append(json.dumps({"type": "header", "run_id": data["run_id"], "scenario": data["scenario"], "target": data["target"]}))
    for f in data["findings"]:
        lines.append(json.dumps({"type": "finding", **f}))
    lines.append(json.dumps({"type": "summary", **data["severity_breakdown"], "total": data["total_findings"]}))
    return "\n".join(lines)
