"""
Rebuff Adapter — prompt injection detection with canary tokens and similarity checking.

SentinelForge: target="openai:gpt-4", args={"detection_modes": ["canary", "similarity"]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.rebuff_adapter")

SUPPORTED_MODES = {"heuristic", "canary", "similarity", "llm_judge"}
ALLOWED_ARGS = {"detection_modes", "max_inputs", "threshold", "verbose"}


def parse_target(target: str) -> Dict[str, str]:
    if ":" in target and not target.startswith("http"):
        provider, _, model = target.partition(":")
        return {"provider": provider.strip().lower(), "model": model.strip()}
    return {"provider": "openai", "model": target.strip()}


def build_rebuff_args(target: str, args: Optional[Dict[str, Any]] = None) -> List[str]:
    parsed = parse_target(target)
    args = args or {}
    cli_args = ["detect", "--model", parsed["model"]]
    modes = args.get("detection_modes", ["heuristic", "canary"])
    for mode in modes:
        cli_args.extend(["--mode", mode])
    if "threshold" in args:
        cli_args.extend(["--threshold", str(args["threshold"])])
    return cli_args


def parse_rebuff_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    findings = []
    data = _try_parse_json(stdout, output_path)
    if data:
        results = data if isinstance(data, list) else data.get("results", [data])
        for r in results:
            if r.get("injection_detected", False):
                findings.append(
                    {
                        "tool": "rebuff",
                        "title": f"rebuff: Prompt injection detected ({r.get('mode', 'unknown')})",
                        "severity": (
                            "high" if r.get("confidence", 0) > 0.8 else "medium"
                        ),
                        "description": f"Injection detected via {r.get('mode', 'unknown')} (confidence: {r.get('confidence', 0):.2f})",
                        "mitre_technique": "AML.T0051.000",
                        "remediation": "Add input validation and prompt injection guardrails.",
                        "raw": r,
                    }
                )
    return findings


def _try_parse_json(stdout, output_path):
    for src in [output_path, None]:
        try:
            if src:
                return json.loads(Path(src).read_text())
            return json.loads(stdout)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            continue
    return None
