"""
LangKit Adapter — prompt/response monitoring with toxicity, sentiment, PII detection.

SentinelForge: target="openai:gpt-4", args={"metrics": ["toxicity", "sentiment", "pii"]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.langkit_adapter")

SUPPORTED_METRICS = {
    "toxicity",
    "sentiment",
    "pii",
    "text_quality",
    "relevance",
    "jailbreak",
}
ALLOWED_ARGS = {"metrics", "num_samples", "threshold", "verbose"}


def parse_target(target: str) -> Dict[str, str]:
    if ":" in target and not target.startswith("http"):
        provider, _, model = target.partition(":")
        return {"provider": provider.strip().lower(), "model": model.strip()}
    return {"provider": "openai", "model": target.strip()}


def build_langkit_args(target: str, args: Optional[Dict[str, Any]] = None) -> List[str]:
    parsed = parse_target(target)
    args = args or {}
    cli_args = ["monitor", "--model", parsed["model"]]
    metrics = args.get("metrics", ["toxicity", "sentiment", "pii"])
    for m in metrics:
        cli_args.extend(["--metric", m])
    if "num_samples" in args:
        cli_args.extend(["--num-samples", str(args["num_samples"])])
    return cli_args


def parse_langkit_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    findings = []
    data = _try_parse_json(stdout, output_path)
    if data:
        results = data if isinstance(data, list) else data.get("metrics", [data])
        for r in results:
            metric = r.get("metric", "unknown")
            score = r.get("score", 0)
            threshold = r.get("threshold", 0.5)
            flagged = r.get(
                "flagged",
                (
                    score > threshold
                    if metric in ("toxicity", "pii")
                    else score < threshold
                ),
            )
            if flagged:
                findings.append(
                    {
                        "tool": "langkit",
                        "title": f"langkit: {metric} alert (score={score:.2f})",
                        "severity": _classify_severity(metric, score),
                        "description": f"Metric: {metric}, Score: {score:.2f}, Threshold: {threshold}",
                        "mitre_technique": "AML.T0056.000",
                        "remediation": f"Investigate {metric} issues in model responses.",
                        "raw": r,
                    }
                )
    return findings


def _classify_severity(metric: str, score: float) -> str:
    if metric == "pii":
        return "critical"
    if metric == "toxicity" and score > 0.8:
        return "critical"
    if metric in ("toxicity", "jailbreak"):
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
