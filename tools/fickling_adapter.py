"""
Fickling Adapter — maps SentinelForge target/args to fickling CLI for pickle file scanning.

fickling CLI: fickling <pickle_file> [--json] [--trace] [--check-safety]
SentinelForge: target="path/to/model.pkl", args={"checks": ["safety", "trace"]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.fickling_adapter")

ALLOWED_ARGS = {"json_output", "trace", "check_safety", "scan_directory"}


def parse_target(target: str) -> Dict[str, str]:
    """Parse target as a file path or URL to a pickle/model artifact.

    Formats:
        "/path/to/model.pkl"         → {"path": "/path/to/model.pkl", "type": "file"}
        "s3://bucket/model.pkl"      → {"path": "s3://bucket/model.pkl", "type": "s3"}
        "hf:user/model"              → {"path": "user/model", "type": "huggingface"}
    """
    if target.startswith("s3://"):
        return {"path": target, "type": "s3"}
    if target.startswith("hf:"):
        return {"path": target[3:], "type": "huggingface"}
    return {"path": target, "type": "file"}


def build_fickling_args(
    target: str,
    args: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Build fickling CLI argument list."""
    parsed = parse_target(target)
    args = args or {}

    cli_args = [parsed["path"]]

    if args.get("check_safety", True):
        cli_args.append("--check-safety")
    if args.get("trace", False):
        cli_args.append("--trace")
    if args.get("json_output", True):
        cli_args.append("--json")

    return cli_args


def parse_fickling_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Parse fickling output into SentinelForge findings."""
    data = None
    if output_path:
        try:
            data = json.loads(Path(output_path).read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    if not data:
        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, TypeError):
            data = None

    if data:
        return _parse_json_results(data)

    return _parse_text_output(stdout)


def _parse_json_results(data: dict) -> List[Dict[str, Any]]:
    """Parse fickling JSON output."""
    findings = []

    if isinstance(data, list):
        issues = data
    else:
        issues = data.get("issues", data.get("findings", []))

    for issue in issues:
        severity = _classify_severity(issue)
        findings.append(
            {
                "tool": "fickling",
                "title": f"fickling: {issue.get('type', 'Suspicious pickle operation')}",
                "severity": severity,
                "description": issue.get(
                    "description", issue.get("message", str(issue))
                ),
                "mitre_technique": "AML.T0010.000",
                "remediation": (
                    "Do not load untrusted pickle files. Use safetensors or ONNX formats. "
                    "Scan all model artifacts before deployment."
                ),
                "raw": issue,
            }
        )

    # If the scan found no issues, no findings to report
    if not findings and data.get("safe", False) is False:
        findings.append(
            {
                "tool": "fickling",
                "title": "fickling: Potentially unsafe pickle file",
                "severity": "high",
                "description": "File contains operations that could execute arbitrary code.",
                "mitre_technique": "AML.T0010.000",
                "remediation": "Migrate to a safe serialization format (safetensors, ONNX).",
                "raw": data,
            }
        )

    return findings


def _parse_text_output(stdout: str) -> List[Dict[str, Any]]:
    """Parse fickling text output for security issues."""
    findings = []
    dangerous_keywords = [
        "__reduce__",
        "exec",
        "eval",
        "os.system",
        "subprocess",
        "import",
    ]

    for line in stdout.strip().splitlines():
        line_lower = line.lower()
        if any(kw in line_lower for kw in dangerous_keywords):
            findings.append(
                {
                    "tool": "fickling",
                    "title": "fickling: Dangerous operation detected",
                    "severity": "critical",
                    "description": line.strip(),
                    "mitre_technique": "AML.T0010.000",
                    "remediation": "This pickle file contains code execution operations. Do not load.",
                    "raw": {"line": line.strip()},
                }
            )
        elif "unsafe" in line_lower or "warning" in line_lower:
            findings.append(
                {
                    "tool": "fickling",
                    "title": f"fickling: {line.strip()[:100]}",
                    "severity": "high",
                    "description": line.strip(),
                    "mitre_technique": "AML.T0010.000",
                    "remediation": "Review pickle file contents and migrate to safe format.",
                    "raw": {"line": line.strip()},
                }
            )
    return findings


def _classify_severity(issue: dict) -> str:
    """Classify severity based on fickling issue type."""
    issue_type = str(issue.get("type", "")).lower()
    if any(kw in issue_type for kw in ["exec", "eval", "system", "code_execution"]):
        return "critical"
    if any(kw in issue_type for kw in ["import", "reduce", "suspicious"]):
        return "high"
    return "medium"
