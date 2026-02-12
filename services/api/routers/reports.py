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

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Report, AttackRun, Finding, ReportFormat, User
from schemas import ReportRequest, ReportResponse
from middleware.auth import get_current_user
from services.evidence_hashing import verify_evidence_chain

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
    result = await db.execute(select(Report).order_by(Report.generated_at.desc()).limit(50))
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate report(s) for an attack run.

    Supports formats: html, pdf, jsonl.
    Reports are uploaded to S3 if storage is configured.
    """
    # Verify run exists
    run_result = await db.execute(select(AttackRun).where(AttackRun.id == request.run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Attack run not found")

    # Load findings
    findings_result = await db.execute(
        select(Finding).where(Finding.run_id == request.run_id).order_by(Finding.created_at.asc())
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

        reports.append(ReportResponse(
            id=report.id,
            run_id=report.run_id,
            format=report.format.value,
            file_path=report.file_path,
            s3_key=report.s3_key,
            generated_at=report.generated_at,
        ))

    await db.commit()
    return reports


@router.get("/{report_id}/view")
async def view_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View a generated report inline."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    run_result = await db.execute(select(AttackRun).where(AttackRun.id == report.run_id))
    run = run_result.scalar_one_or_none()

    findings_result = await db.execute(
        select(Finding).where(Finding.run_id == report.run_id).order_by(Finding.created_at.asc())
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
            headers={"Content-Disposition": f'inline; filename="report-{report.run_id[:12]}.pdf"'},
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a report from S3 or regenerate it."""
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
    run_result = await db.execute(select(AttackRun).where(AttackRun.id == report.run_id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Associated attack run not found")

    findings_result = await db.execute(
        select(Finding).where(Finding.run_id == report.run_id).order_by(Finding.created_at.asc())
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
        sev = f.severity.value
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
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "mitre_technique": f.mitre_technique,
                "remediation": f.remediation,
                "evidence_hash": f.evidence_hash,
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

    from config import settings
    version = getattr(settings, "_version", "1.2.0")

    return template.render(
        **data,
        severity_colors=_SEVERITY_COLORS,
        version="1.2.0",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def _render_html_inline(data: dict) -> str:
    """Fallback inline HTML generation (no Jinja2 template)."""
    findings_html = ""
    for f in data["findings"]:
        color = _SEVERITY_COLORS.get(f["severity"], "#6b7280")
        findings_html += f"""
        <div class="finding" style="border-left: 4px solid {color};">
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
<html lang="en"><head><meta charset="UTF-8"><title>SentinelForge Report</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
h1 {{ color: #38bdf8; }} h2 {{ color: #7dd3fc; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; margin: 1.5rem 0 0.75rem; }}
.finding {{ background: #1e293b; border-radius: 8px; padding: 1rem 1.5rem; margin: 0.75rem 0; }}
.finding-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap; }}
.severity {{ padding: 0.15rem 0.5rem; border-radius: 4px; color: white; font-size: 0.75rem; font-weight: 700; }}
.tool {{ background: #334155; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; }}
.footer {{ margin-top: 2rem; border-top: 1px solid #334155; padding-top: 1rem; color: #64748b; text-align: center; font-size: 0.85rem; }}
</style></head><body><div class="container">
<h1>SentinelForge Security Report</h1>
<p style="color:#94a3b8">Run: {data['run_id'][:12]} | Scenario: {data['scenario']} | Target: {data['target']}</p>
<h2>Findings ({data['total_findings']})</h2>
{findings_html if findings_html else '<p style="color:#64748b">No findings.</p>'}
<div class="footer">Generated by SentinelForge v1.2.0 &bull; {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>
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
    lines.append(json.dumps({
        "type": "header",
        "run_id": data["run_id"],
        "scenario": data["scenario"],
        "target": data["target"],
    }))
    for f in data["findings"]:
        lines.append(json.dumps({"type": "finding", **f}))
    lines.append(json.dumps({
        "type": "summary",
        **data["severity_breakdown"],
        "total": data["total_findings"],
    }))
    return "\n".join(lines)


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
