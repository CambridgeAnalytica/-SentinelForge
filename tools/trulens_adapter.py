"""
TruLens Adapter — LLM evaluation with feedback functions, groundedness, RAG evaluation.

SentinelForge: target="openai:gpt-4", args={"feedbacks": ["groundedness", "relevance"]}
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.trulens_adapter")

SUPPORTED_FEEDBACKS = {
    "groundedness",
    "relevance",
    "coherence",
    "harmfulness",
    "stereotypes",
    "criminality",
}
ALLOWED_ARGS = {"feedbacks", "app_id", "num_queries", "verbose"}


def parse_target(target: str) -> Dict[str, str]:
    if ":" in target and not target.startswith("http"):
        provider, _, model = target.partition(":")
        return {"provider": provider.strip().lower(), "model": model.strip()}
    return {"provider": "openai", "model": target.strip()}


def build_trulens_args(target: str, args: Optional[Dict[str, Any]] = None) -> List[str]:
    parsed = parse_target(target)
    args = args or {}
    cli_args = ["evaluate", "--model", parsed["model"]]
    feedbacks = args.get("feedbacks", ["groundedness", "relevance"])
    for f in feedbacks:
        cli_args.extend(["--feedback", f])
    if "num_queries" in args:
        cli_args.extend(["--num-queries", str(args["num_queries"])])
    return cli_args


def parse_trulens_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    findings = []
    data = _try_parse_json(stdout, output_path)
    if data:
        results = (
            data if isinstance(data, list) else data.get("feedback_results", [data])
        )
        for r in results:
            score = r.get("score", 1.0)
            if score < r.get("threshold", 0.5):
                findings.append(
                    {
                        "tool": "trulens",
                        "title": f"trulens: {r.get('feedback', 'unknown')} below threshold (score={score:.2f})",
                        "severity": "high" if score < 0.3 else "medium",
                        "description": f"Feedback: {r.get('feedback', 'unknown')}, Score: {score:.2f}",
                        "mitre_technique": "AML.T0056.000",
                        "remediation": f"Improve model {r.get('feedback', 'output quality')}.",
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
