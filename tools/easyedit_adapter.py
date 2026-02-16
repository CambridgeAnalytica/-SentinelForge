"""
EasyEdit Adapter — knowledge editing for LLMs to test model update robustness.

SentinelForge: target="openai:gpt-4", args={"method": "ROME", "edits": [{"subject": "...", "target": "..."}]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.easyedit_adapter")

SUPPORTED_METHODS = {"ROME", "MEMIT", "KN", "FT", "MEND", "SERAC"}
ALLOWED_ARGS = {"method", "edits", "num_edits", "verbose"}


def parse_target(target: str) -> Dict[str, str]:
    if ":" in target and not target.startswith("http"):
        provider, _, model = target.partition(":")
        return {"provider": provider.strip().lower(), "model": model.strip()}
    return {"provider": "local", "model": target.strip()}


def build_easyedit_args(
    target: str, args: Optional[Dict[str, Any]] = None
) -> List[str]:
    parsed = parse_target(target)
    args = args or {}
    method = args.get("method", "ROME")
    cli_args = ["edit", "--model", parsed["model"], "--method", method]
    if "num_edits" in args:
        cli_args.extend(["--num-edits", str(args["num_edits"])])
    return cli_args


def parse_easyedit_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    findings = []
    data = _try_parse_json(stdout, output_path)
    if data:
        results = data if isinstance(data, list) else data.get("results", [data])
        for r in results:
            success = r.get("edit_success", r.get("success", False))
            method = r.get("method", "unknown")
            if success:
                findings.append(
                    {
                        "tool": "easyedit",
                        "title": f"easyedit: Knowledge edit succeeded via {method}",
                        "severity": _classify_severity(r),
                        "description": f"Model knowledge was modified using {method}. Edit: {r.get('edit', {}).get('subject', 'unknown')}",
                        "mitre_technique": "AML.T0040.000",
                        "remediation": "Model is susceptible to knowledge editing. Monitor for unauthorized updates.",
                        "raw": r,
                    }
                )
    return findings


def _classify_severity(result: dict) -> str:
    generalization = result.get("generalization_score", 0)
    if generalization > 0.8:
        return "critical"
    if generalization > 0.5:
        return "high"
    return "medium"


def _try_parse_json(stdout, output_path):
    for src in [output_path, None]:
        try:
            if src:
                return json.loads(Path(src).read_text())
            return json.loads(stdout)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            continue
    return None
