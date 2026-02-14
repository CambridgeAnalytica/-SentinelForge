"""
Garak Adapter — maps SentinelForge generic target/args to garak CLI interface.

garak CLI expects: garak --model_type openai --model_name gpt-4 --probes encoding.InjectBase64
SentinelForge sends: target="openai:gpt-4", args={"probes": "encoding.InjectBase64"}
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.garak_adapter")

# Supported model types for garak
SUPPORTED_MODEL_TYPES = {
    "openai",
    "huggingface",
    "anthropic",
    "cohere",
    "replicate",
    "ggml",
    "rest",
}

# Garak CLI flags we allow
ALLOWED_ARGS = {
    "probes",
    "detectors",
    "generations",
    "seed",
    "report_prefix",
    "parallel_requests",
    "verbose",
}


def parse_target(target: str) -> Dict[str, str]:
    """Parse a SentinelForge target string into garak model_type + model_name.

    Formats:
        "openai:gpt-4"          → {"model_type": "openai", "model_name": "gpt-4"}
        "huggingface:meta-llama/Llama-2-7b" → {"model_type": "huggingface", "model_name": "meta-llama/Llama-2-7b"}
        "rest:https://api.example.com/v1" → {"model_type": "rest", "model_name": "https://api.example.com/v1"}

    If no colon separator, assumes 'openai' as the default model_type.
    """
    if ":" in target:
        model_type, _, model_name = target.partition(":")
        model_type = model_type.strip().lower()
        model_name = model_name.strip()
    else:
        model_type = "openai"
        model_name = target.strip()

    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ValueError(
            f"Unsupported garak model type '{model_type}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_MODEL_TYPES))}"
        )

    if not model_name:
        raise ValueError("Model name cannot be empty.")

    return {"model_type": model_type, "model_name": model_name}


def build_garak_args(
    target: str,
    args: Optional[Dict[str, Any]] = None,
    default_probes: Optional[List[str]] = None,
) -> List[str]:
    """Build garak CLI argument list from SentinelForge target/args.

    Returns a list of CLI arguments (without the 'garak' command itself).
    """
    parsed = parse_target(target)
    cli_args = [
        "--model_type", parsed["model_type"],
        "--model_name", parsed["model_name"],
    ]

    args = args or {}

    # Merge default probes if none specified
    if "probes" not in args and default_probes:
        args["probes"] = ",".join(default_probes)

    for key, value in args.items():
        if key not in ALLOWED_ARGS:
            logger.warning(f"Skipping unknown garak arg: {key}")
            continue

        if isinstance(value, bool):
            if value:
                cli_args.append(f"--{key}")
        elif isinstance(value, list):
            cli_args.extend([f"--{key}", ",".join(str(v) for v in value)])
        else:
            cli_args.extend([f"--{key}", str(value)])

    return cli_args


def parse_garak_output(stdout: str) -> List[Dict[str, Any]]:
    """Parse garak JSONL output into SentinelForge findings.

    Garak outputs one JSON object per line. Each result looks like:
    {"probe": "encoding.InjectBase64", "detector": "always.Fail", "passed": false, ...}
    """
    findings = []
    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        passed = record.get("passed", True)
        if passed:
            continue  # Only report failures

        severity = _classify_severity(record)
        probe_name = record.get("probe", "unknown")
        detector = record.get("detector", "unknown")

        findings.append({
            "tool": "garak",
            "title": f"garak: {probe_name} detected by {detector}",
            "severity": severity,
            "description": record.get("output", record.get("prompt", "")),
            "mitre_technique": "AML.T0051.000",
            "remediation": f"Review and harden against {probe_name} attack vector.",
            "raw": record,
        })

    return findings


def _classify_severity(record: dict) -> str:
    """Classify finding severity based on probe category."""
    probe = record.get("probe", "").lower()
    if any(kw in probe for kw in ("malware", "dan", "jailbreak", "injection")):
        return "critical"
    if any(kw in probe for kw in ("slur", "toxicity", "bias")):
        return "high"
    if any(kw in probe for kw in ("encoding", "continuation")):
        return "medium"
    return "low"
