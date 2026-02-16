"""
ART Adapter — Adversarial Robustness Toolbox.

Covers evasion, poisoning, backdoor detection, and adversarial training.
ART uses Python API rather than CLI, so this adapter generates a config
that the executor runs as a Python script.

SentinelForge: target="keras:my_model.h5", args={"attack": "fgsm", "eps": 0.3}
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.art_adapter")

SUPPORTED_ATTACKS = {
    # Evasion
    "fgsm",
    "pgd",
    "deepfool",
    "carlini_wagner",
    "boundary",
    "hopskipjump",
    "shadow",
    "square",
    # Poisoning
    "backdoor",
    "clean_label",
    "bullseye",
    # Extraction
    "copycat",
    "knockoff",
}

ALLOWED_ARGS = {
    "attack",
    "eps",
    "eps_step",
    "max_iter",
    "batch_size",
    "targeted",
    "norm",
    "num_classes",
    "verbose",
}


def parse_target(target: str) -> Dict[str, str]:
    """Parse target as a model path or framework reference.

    Formats:
        "keras:model.h5"           → {"framework": "keras", "model_path": "model.h5"}
        "pytorch:model.pt"         → {"framework": "pytorch", "model_path": "model.pt"}
        "sklearn:pipeline.pkl"     → {"framework": "sklearn", "model_path": "pipeline.pkl"}
        "/path/to/model.h5"        → {"framework": "auto", "model_path": "/path/to/model.h5"}
    """
    if ":" in target and not target.startswith(("/", "C:", "D:")):
        framework, _, model_path = target.partition(":")
        return {
            "framework": framework.strip().lower(),
            "model_path": model_path.strip(),
        }
    return {"framework": "auto", "model_path": target.strip()}


def build_art_config(
    target: str,
    args: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate ART attack configuration file.

    Returns path to a JSON config used by the ART executor script.
    """
    args = args or {}
    parsed = parse_target(target)

    attack = args.get("attack", "fgsm")
    if attack not in SUPPORTED_ATTACKS:
        logger.warning(f"Unknown ART attack '{attack}', proceeding anyway")

    config = {
        "target": parsed,
        "attack": {
            "name": attack,
            "eps": args.get("eps", 0.3),
            "eps_step": args.get("eps_step", 0.01),
            "max_iter": args.get("max_iter", 100),
            "batch_size": args.get("batch_size", 32),
            "targeted": args.get("targeted", False),
            "norm": args.get("norm", "inf"),
        },
        "output": {"format": "json", "save_adversarial_examples": True},
    }

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="sf_art_", delete=False
    )
    json.dump(config, tmp, indent=2)
    tmp.close()
    logger.info(f"ART config written to {tmp.name}")
    return tmp.name


def build_art_args(config_path: str) -> List[str]:
    """Build ART CLI argument list.

    ART is primarily a library, so we invoke it as a script.
    """
    return ["run", "--config", config_path, "--output-format", "json"]


def parse_art_output(
    stdout: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Parse ART output into SentinelForge findings."""
    findings = []

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
            return _parse_text_output(stdout)

    results = data if isinstance(data, list) else data.get("results", [data])

    for result in results:
        attack_name = result.get("attack", "unknown")
        success_rate = result.get("success_rate", result.get("fooling_rate", 0))
        perturbation = result.get("avg_perturbation", result.get("eps", 0))

        if success_rate > 0:
            severity = _classify_severity(attack_name, success_rate)
            findings.append(
                {
                    "tool": "art",
                    "title": f"ART: {attack_name} attack — {success_rate:.0%} success rate",
                    "severity": severity,
                    "description": (
                        f"Attack: {attack_name}\n"
                        f"Success rate: {success_rate:.1%}\n"
                        f"Avg perturbation: {perturbation:.4f}"
                    ),
                    "mitre_technique": _get_mitre_technique(attack_name),
                    "remediation": (
                        f"Model is vulnerable to {attack_name} attacks. "
                        "Consider adversarial training, input preprocessing, "
                        "or certified defense mechanisms."
                    ),
                    "raw": result,
                }
            )

    return findings


def _parse_text_output(stdout: str) -> List[Dict[str, Any]]:
    """Parse text-based ART output."""
    findings = []
    for line in stdout.strip().splitlines():
        line_lower = line.lower()
        if "success" in line_lower and ("rate" in line_lower or "%" in line):
            findings.append(
                {
                    "tool": "art",
                    "title": f"ART: {line.strip()[:100]}",
                    "severity": "high",
                    "description": line.strip(),
                    "mitre_technique": "AML.T0043.000",
                    "remediation": "Model is vulnerable to adversarial attacks.",
                    "raw": {"line": line.strip()},
                }
            )
    return findings


def _classify_severity(attack_name: str, success_rate: float) -> str:
    """Classify severity based on attack type and success rate."""
    if success_rate > 0.8:
        return "critical"
    if success_rate > 0.5:
        return "high"
    if attack_name in ("backdoor", "clean_label", "bullseye"):
        return "critical" if success_rate > 0.3 else "high"
    return "medium"


def _get_mitre_technique(attack_name: str) -> str:
    """Map ART attack to MITRE ATLAS technique ID."""
    mapping = {
        "fgsm": "AML.T0043.000",
        "pgd": "AML.T0043.000",
        "deepfool": "AML.T0043.000",
        "carlini_wagner": "AML.T0043.000",
        "boundary": "AML.T0043.000",
        "hopskipjump": "AML.T0043.000",
        "shadow": "AML.T0043.000",
        "square": "AML.T0043.000",
        "backdoor": "AML.T0040.000",
        "clean_label": "AML.T0020.000",
        "bullseye": "AML.T0020.000",
        "copycat": "AML.T0044.000",
        "knockoff": "AML.T0044.000",
    }
    return mapping.get(attack_name, "AML.T0043.000")
