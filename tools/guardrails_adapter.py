"""
Guardrails Adapter — LLM output validation with PII detection, toxicity filtering, schema enforcement.

SentinelForge: target="openai:gpt-4", args={"validators": ["pii", "toxicity", "json_schema"]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.guardrails_adapter")

SUPPORTED_VALIDATORS = {
    "pii",
    "toxicity",
    "profanity",
    "json_schema",
    "length",
    "regex",
    "nsfw",
}
ALLOWED_ARGS = {"validators", "guard_spec", "num_reasks", "verbose"}


def parse_target(target: str) -> Dict[str, str]:
    if ":" in target and not target.startswith("http"):
        provider, _, model = target.partition(":")
        return {"provider": provider.strip().lower(), "model": model.strip()}
    return {"provider": "openai", "model": target.strip()}


def build_guardrails_args(
    target: str, args: Optional[Dict[str, Any]] = None
) -> List[str]:
    parsed = parse_target(target)
    args = args or {}
    cli_args = ["validate", "--model", parsed["model"]]
    validators = args.get("validators", ["pii", "toxicity"])
    for v in validators:
        cli_args.extend(["--validator", v])
    if "num_reasks" in args:
        cli_args.extend(["--num-reasks", str(args["num_reasks"])])
    return cli_args


def parse_guardrails_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    findings = []
    data = _try_parse_json(stdout, output_path)
    if data:
        results = (
            data if isinstance(data, list) else data.get("validation_results", [data])
        )
        for r in results:
            if not r.get("passed", True):
                findings.append(
                    {
                        "tool": "guardrails",
                        "title": f"guardrails: Validation failed — {r.get('validator', 'unknown')}",
                        "severity": _classify_severity(r),
                        "description": r.get("error_message", r.get("reason", str(r))),
                        "mitre_technique": "AML.T0015.000",
                        "remediation": f"Add {r.get('validator', 'output')} guardrail to production pipeline.",
                        "raw": r,
                    }
                )
    return findings


def _classify_severity(result: dict) -> str:
    validator = result.get("validator", "").lower()
    if validator in ("pii", "nsfw"):
        return "critical"
    if validator in ("toxicity", "profanity"):
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
