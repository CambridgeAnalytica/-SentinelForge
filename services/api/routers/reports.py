"""
Report generation and management endpoints.

Supports HTML (Jinja2), PDF (WeasyPrint), and JSONL output formats.
Reports are optionally uploaded to S3-compatible storage for persistence.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Report, AttackRun, Finding, ReportFormat, User
from schemas import ReportRequest, ReportResponse
from middleware.auth import get_current_user
from models import AuditLog
from services.evidence_hashing import verify_evidence_chain
from services.user_service import decode_token

router = APIRouter()
logger = logging.getLogger("sentinelforge.reports")

# Jinja2 template environment
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)

# Severity color map for templates
_SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#d97706",
    "low": "#2563eb",
    "info": "#6b7280",
}


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all generated reports."""
    result = await db.execute(
        select(Report).order_by(Report.generated_at.desc()).limit(50)
    )
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=r.id,
            run_id=r.run_id,
            format=r.format.value,
            file_path=r.file_path,
            s3_key=r.s3_key,
            generated_at=r.generated_at,
        )
        for r in reports
    ]


@router.post("/generate", response_model=List[ReportResponse])
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate report(s) for an attack run.

    Supports formats: html, pdf, jsonl.
    Reports are uploaded to S3 if storage is configured.
    """
    # Verify run exists
    run_result = await db.execute(
        select(AttackRun).where(AttackRun.id == request.run_id)
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Attack run not found")

    # Load findings
    findings_result = await db.execute(
        select(Finding)
        .where(Finding.run_id == request.run_id)
        .order_by(Finding.created_at.asc())
    )
    findings = list(findings_result.scalars().all())

    reports = []
    for fmt in request.formats:
        report_format = ReportFormat(fmt)
        content_bytes, content_type = _render_report(run, findings, report_format)

        # Upload to S3
        s3_key = _upload_to_s3(content_bytes, run.id, fmt, content_type)

        report = Report(
            run_id=request.run_id,
            format=report_format,
            file_path=f"reports/{run.id}.{fmt}",
            s3_key=s3_key,
            generated_at=datetime.now(timezone.utc),
        )
        db.add(report)
        await db.flush()

        reports.append(
            ReportResponse(
                id=report.id,
                run_id=report.run_id,
                format=report.format.value,
                file_path=report.file_path,
                s3_key=report.s3_key,
                generated_at=report.generated_at,
            )
        )

    # Audit log: report generated
    db.add(AuditLog(
        user_id=user.id,
        action="report.generated",
        resource_type="report",
        resource_id=request.run_id,
        details={
            "formats": request.formats,
            "report_ids": [r.id for r in reports],
        },
    ))
    await db.commit()

    # Dispatch webhook notification
    for r in reports:
        background_tasks.add_task(
            _dispatch_webhook,
            "report.generated",
            {"report_id": r.id, "run_id": r.run_id, "format": r.format},
        )

    return reports


@router.get("/{report_id}/view")
async def view_report(
    report_id: str,
    token: Optional[str] = Query(None, description="JWT token for browser access"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View a generated report inline. Accepts ?token= for browser window.open()."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    run_result = await db.execute(
        select(AttackRun).where(AttackRun.id == report.run_id)
    )
    run = run_result.scalar_one_or_none()

    findings_result = await db.execute(
        select(Finding)
        .where(Finding.run_id == report.run_id)
        .order_by(Finding.created_at.asc())
    )
    findings = list(findings_result.scalars().all())

    if report.format == ReportFormat.HTML:
        content, _ = _render_report(run, findings, ReportFormat.HTML)
        return HTMLResponse(content=content.decode("utf-8"))
    elif report.format == ReportFormat.PDF:
        content, _ = _render_report(run, findings, ReportFormat.PDF)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="report-{report.run_id[:12]}.pdf"'
            },
        )
    else:
        return {
            "report_id": report.id,
            "run_id": report.run_id,
            "format": report.format.value,
            "data": _build_report_data(run, findings),
        }


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    token: Optional[str] = Query(None, description="JWT token for browser access"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a report from S3 or regenerate it. Accepts ?token= for browser access."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Try S3 download first
    if report.s3_key:
        try:
            from services.s3_service import download_report as s3_download

            content = s3_download(report.s3_key)
            if content:
                ext = report.format.value
                media_types = {
                    "html": "text/html",
                    "pdf": "application/pdf",
                    "jsonl": "application/x-ndjson",
                }
                return Response(
                    content=content,
                    media_type=media_types.get(ext, "application/octet-stream"),
                    headers={
                        "Content-Disposition": f'attachment; filename="report-{report.run_id[:12]}.{ext}"',
                    },
                )
        except Exception as e:
            logger.warning(f"S3 download failed, regenerating: {e}")

    # Fallback: regenerate
    run_result = await db.execute(
        select(AttackRun).where(AttackRun.id == report.run_id)
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Associated attack run not found")

    findings_result = await db.execute(
        select(Finding)
        .where(Finding.run_id == report.run_id)
        .order_by(Finding.created_at.asc())
    )
    findings = list(findings_result.scalars().all())

    content, content_type = _render_report(run, findings, report.format)
    ext = report.format.value
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="report-{report.run_id[:12]}.{ext}"',
        },
    )


# ---------- Internal Helpers ----------


def _build_report_data(run: AttackRun, findings: list) -> dict:
    """Build structured report data from run + findings."""
    severity_counts = {}
    for f in findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Evidence chain verification
    chain_result = verify_evidence_chain(findings) if findings else None

    return {
        "run_id": run.id,
        "scenario": run.scenario_id,
        "target": run.target_model,
        "status": run.status.value,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_findings": len(findings),
        "severity_breakdown": severity_counts,
        "evidence_chain": chain_result,
        "findings": [
            {
                "id": f.id,
                "tool": f.tool_name,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "title": f.title,
                "description": f.description,
                "mitre_technique": f.mitre_technique,
                "remediation": f.remediation,
                "evidence_hash": f.evidence_hash,
                "evidence": f.evidence or {},
            }
            for f in findings
        ],
    }


def _render_report(
    run: AttackRun,
    findings: list,
    fmt: ReportFormat,
) -> tuple[bytes, str]:
    """Render a report in the requested format.

    Returns (content_bytes, content_type).
    """
    data = _build_report_data(run, findings)

    if fmt == ReportFormat.HTML:
        html = _render_html(data)
        return html.encode("utf-8"), "text/html"

    elif fmt == ReportFormat.PDF:
        html = _render_html(data)
        pdf_bytes = _html_to_pdf(html)
        return pdf_bytes, "application/pdf"

    elif fmt == ReportFormat.JSONL:
        jsonl = _render_jsonl(data)
        return jsonl.encode("utf-8"), "application/x-ndjson"

    # Fallback
    html = _render_html(data)
    return html.encode("utf-8"), "text/html"


def _render_html(data: dict) -> str:
    """Render HTML report using Jinja2 template."""
    try:
        template = _jinja_env.get_template("report.html.j2")
    except Exception:
        logger.warning("Jinja2 template not found, falling back to inline HTML")
        return _render_html_inline(data)

    return template.render(
        **data,
        severity_colors=_SEVERITY_COLORS,
        version="2.2.0",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _render_html_inline(data: dict) -> str:
    """Executive-quality inline HTML report with evidence sections."""
    import html as html_mod

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sev_breakdown = data.get("severity_breakdown", {})

    # Executive summary stats
    sev_badges = ""
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = sev_breakdown.get(sev, 0)
        if count > 0:
            color = _SEVERITY_COLORS.get(sev, "#6b7280")
            sev_badges += (
                f'<span style="background:{color};color:white;padding:0.25rem 0.75rem;'
                f'border-radius:4px;font-size:0.85rem;font-weight:700;margin-right:0.5rem;">'
                f'{sev.upper()}: {count}</span>'
            )

    # Findings detail sections
    findings_html = ""
    for idx, f in enumerate(data["findings"], 1):
        color = _SEVERITY_COLORS.get(f["severity"], "#6b7280")
        evidence = f.get("evidence", {})
        desc = html_mod.escape(f.get("description") or "No description")

        # Build evidence section if available
        evidence_html = ""
        prompt_text = evidence.get("prompt", "")
        response_text = evidence.get("response") or evidence.get("response_preview", "")
        safety_score = evidence.get("safety_score")
        strategy = evidence.get("strategy", "")
        turn = evidence.get("turn", "")
        total_turns = evidence.get("total_turns", "")

        if prompt_text or response_text:
            evidence_html += '<div class="evidence">'
            evidence_html += '<h4>Evidence</h4>'
            if strategy:
                evidence_html += (
                    f'<p class="meta">Strategy: <strong>{html_mod.escape(strategy)}</strong>'
                )
                if turn:
                    evidence_html += f' | Turn: <strong>{turn}/{total_turns}</strong>'
                evidence_html += '</p>'
            if safety_score is not None:
                score_color = "#ef4444" if safety_score < 0.3 else "#eab308" if safety_score < 0.6 else "#22c55e"
                evidence_html += (
                    f'<p class="meta">Safety Score: '
                    f'<span style="color:{score_color};font-weight:700;">{safety_score:.2f}</span>'
                    f' / 1.00</p>'
                )
            if prompt_text:
                evidence_html += (
                    f'<div class="evidence-block">'
                    f'<div class="evidence-label">Attacker Prompt</div>'
                    f'<pre>{html_mod.escape(prompt_text[:500])}</pre>'
                    f'</div>'
                )
            if response_text:
                evidence_html += (
                    f'<div class="evidence-block">'
                    f'<div class="evidence-label">Model Response</div>'
                    f'<pre>{html_mod.escape(response_text[:600])}</pre>'
                    f'</div>'
                )
            evidence_html += '</div>'

        mitre_html = ""
        if f.get("mitre_technique"):
            mitre_html = (
                f'<span class="tag">MITRE ATLAS: {html_mod.escape(f["mitre_technique"])}</span>'
            )

        remediation_html = ""
        if f.get("remediation"):
            remediation_html = (
                f'<div class="remediation">'
                f'<strong>Recommended Action:</strong> {html_mod.escape(f["remediation"])}'
                f'</div>'
            )

        findings_html += f"""
        <div class="finding" style="border-left: 4px solid {color};">
            <div class="finding-header">
                <span class="finding-num">#{idx}</span>
                <span class="severity" style="background:{color}">{f['severity'].upper()}</span>
                <strong class="finding-title">{html_mod.escape(f['title'])}</strong>
            </div>
            <div class="finding-meta">
                <span class="tag">{html_mod.escape(f['tool'])}</span>
                {mitre_html}
            </div>
            {evidence_html}
            {remediation_html}
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>SentinelForge Security Report — {html_mod.escape(data['scenario'])}</title>
<style>
@page {{ size: A4; margin: 1.5cm; }}
body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; line-height: 1.6; }}
.container {{ max-width: 900px; margin: 0 auto; }}
.header {{ border-bottom: 2px solid #38bdf8; padding-bottom: 1.5rem; margin-bottom: 2rem; }}
.logo {{ font-size: 1.75rem; font-weight: 800; color: #38bdf8; letter-spacing: -0.5px; }}
.logo span {{ color: #7dd3fc; font-weight: 400; }}
.subtitle {{ color: #94a3b8; font-size: 0.95rem; margin-top: 0.25rem; }}
.exec-summary {{ background: #1e293b; border-radius: 12px; padding: 1.5rem 2rem; margin-bottom: 2rem; }}
.exec-summary h2 {{ color: #7dd3fc; margin: 0 0 1rem; font-size: 1.1rem; border: none; padding: 0; }}
.stat-row {{ display: flex; gap: 2rem; flex-wrap: wrap; margin-bottom: 1rem; }}
.stat {{ text-align: center; }}
.stat-value {{ font-size: 2rem; font-weight: 800; color: #f8fafc; }}
.stat-label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
.meta-table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
.meta-table td {{ padding: 0.4rem 0; font-size: 0.85rem; }}
.meta-table td:first-child {{ color: #94a3b8; width: 140px; }}
.meta-table td:last-child {{ color: #e2e8f0; font-weight: 500; }}
h2 {{ color: #7dd3fc; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; margin: 2rem 0 1rem; font-size: 1.1rem; }}
.finding {{ background: #1e293b; border-radius: 10px; padding: 1.25rem 1.5rem; margin: 1rem 0; }}
.finding-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }}
.finding-num {{ color: #64748b; font-size: 0.8rem; font-weight: 600; }}
.finding-title {{ color: #f1f5f9; font-size: 0.95rem; }}
.finding-meta {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem; }}
.severity {{ padding: 0.2rem 0.6rem; border-radius: 4px; color: white; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }}
.tag {{ background: #334155; color: #cbd5e1; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }}
.evidence {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 1rem 1.25rem; margin: 0.75rem 0; }}
.evidence h4 {{ color: #7dd3fc; margin: 0 0 0.75rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }}
.evidence .meta {{ color: #94a3b8; font-size: 0.8rem; margin-bottom: 0.5rem; }}
.evidence-block {{ margin: 0.5rem 0; }}
.evidence-label {{ font-size: 0.7rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem; }}
.evidence pre {{ background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.8rem; color: #e2e8f0; white-space: pre-wrap; word-break: break-word; margin: 0; font-family: 'Cascadia Code', 'Fira Code', monospace; line-height: 1.5; }}
.remediation {{ background: #172554; border: 1px solid #1e3a5f; border-radius: 6px; padding: 0.75rem 1rem; margin-top: 0.75rem; font-size: 0.85rem; color: #93c5fd; }}
.footer {{ margin-top: 3rem; border-top: 1px solid #334155; padding-top: 1rem; color: #64748b; text-align: center; font-size: 0.8rem; }}
</style></head><body><div class="container">

<div class="header">
    <div class="logo">SentinelForge <span>Security Assessment Report</span></div>
    <div class="subtitle">AI/LLM Red Team Testing &mdash; Confidential</div>
</div>

<div class="exec-summary">
    <h2>Executive Summary</h2>
    <div class="stat-row">
        <div class="stat">
            <div class="stat-value">{data['total_findings']}</div>
            <div class="stat-label">Findings</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sev_breakdown.get('critical', 0)}</div>
            <div class="stat-label">Critical</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sev_breakdown.get('high', 0)}</div>
            <div class="stat-label">High</div>
        </div>
        <div class="stat">
            <div class="stat-value">{sev_breakdown.get('medium', 0)}</div>
            <div class="stat-label">Medium</div>
        </div>
    </div>
    <div>{sev_badges}</div>
    <table class="meta-table">
        <tr><td>Scenario</td><td>{html_mod.escape(data['scenario'])}</td></tr>
        <tr><td>Target Model</td><td>{html_mod.escape(data['target'])}</td></tr>
        <tr><td>Status</td><td>{html_mod.escape(data['status'])}</td></tr>
        <tr><td>Started</td><td>{data.get('started_at', 'N/A')}</td></tr>
        <tr><td>Completed</td><td>{data.get('completed_at', 'N/A')}</td></tr>
        <tr><td>Run ID</td><td><code>{data['run_id']}</code></td></tr>
    </table>
</div>

<h2>Detailed Findings ({data['total_findings']})</h2>
{findings_html if findings_html else '<p style="color:#64748b;font-style:italic;">No security findings were identified during this assessment.</p>'}

<div class="footer">
    Generated by SentinelForge v2.2.0 &bull; {generated_at}<br>
    This report is confidential and intended for authorized recipients only.
</div>
</div></body></html>"""


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML

        return HTML(string=html).write_pdf()
    except ImportError:
        logger.error("weasyprint not installed — PDF generation unavailable")
        raise HTTPException(
            status_code=501,
            detail="PDF generation requires weasyprint. Install it with: pip install weasyprint",
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


def _render_jsonl(data: dict) -> str:
    """Generate JSONL report."""
    lines = []
    lines.append(
        json.dumps(
            {
                "type": "header",
                "run_id": data["run_id"],
                "scenario": data["scenario"],
                "target": data["target"],
            }
        )
    )
    for f in data["findings"]:
        lines.append(json.dumps({"type": "finding", **f}))
    lines.append(
        json.dumps(
            {
                "type": "summary",
                **data["severity_breakdown"],
                "total": data["total_findings"],
            }
        )
    )
    return "\n".join(lines)


async def _dispatch_webhook(event_type: str, payload: dict) -> None:
    """Background task: dispatch webhook event."""
    try:
        from services.webhook_service import dispatch_webhook_event

        await dispatch_webhook_event(event_type, payload)
    except Exception as e:
        logger.error(f"Webhook dispatch error: {e}")


def _upload_to_s3(
    content: bytes,
    run_id: str,
    fmt: str,
    content_type: str,
) -> Optional[str]:
    """Upload report to S3. Returns key on success, None on failure."""
    try:
        from services.s3_service import upload_report

        key = f"reports/{run_id}.{fmt}"
        upload_report(content=content, key=key, content_type=content_type)
        return key
    except Exception as e:
        logger.warning(f"S3 upload skipped: {e}")
        return None
