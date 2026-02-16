"""
TextAttack Adapter — maps SentinelForge generic target/args to textattack CLI interface.

textattack CLI: textattack attack --recipe textfooler --model bert-base-uncased
SentinelForge: target="huggingface:bert-base-uncased", args={"recipe": "textfooler"}
"""

import csv
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.textattack_adapter")

SUPPORTED_RECIPES = {
    "textfooler",
    "deepwordbug",
    "bae",
    "pwws",
    "textbugger",
    "pso",
    "checklist",
    "clare",
    "a2t",
    "iga",
}

ALLOWED_ARGS = {
    "recipe",
    "model",
    "dataset",
    "num_examples",
    "query_budget",
    "shuffle",
    "log_to_csv",
}


def parse_target(target: str) -> Dict[str, str]:
    """Parse a SentinelForge target string into textattack model config.

    Formats:
        "huggingface:bert-base-uncased" → {"model": "bert-base-uncased", "model_source": "huggingface"}
        "lstm-mr"                       → {"model": "lstm-mr", "model_source": "textattack"}
        "openai:gpt-4"                 → {"model": "gpt-4", "model_source": "openai"}
    """
    if ":" in target and not target.startswith("http"):
        source, _, model = target.partition(":")
        source = source.strip().lower()
        model = model.strip()
    else:
        source = "textattack"
        model = target.strip()

    if not model:
        raise ValueError("Model name cannot be empty.")

    return {"model": model, "model_source": source}


def build_textattack_args(
    target: str,
    args: Optional[Dict[str, Any]] = None,
    default_recipe: str = "textfooler",
) -> List[str]:
    """Build textattack CLI argument list from SentinelForge target/args.

    Returns a list of CLI arguments (without the 'textattack' command itself).
    """
    parsed = parse_target(target)
    recipe = (args or {}).get("recipe", default_recipe)

    if recipe not in SUPPORTED_RECIPES:
        logger.warning(f"Unknown recipe '{recipe}', proceeding anyway")

    cli_args = ["attack", "--recipe", recipe]

    # Model specification
    if parsed["model_source"] == "huggingface":
        cli_args.extend(["--model-from-huggingface", parsed["model"]])
    else:
        cli_args.extend(["--model", parsed["model"]])

    args = args or {}
    for key, value in args.items():
        if key in ("recipe", "model"):
            continue
        if key not in ALLOWED_ARGS:
            logger.warning(f"Skipping unknown textattack arg: {key}")
            continue

        if isinstance(value, bool):
            if value:
                cli_args.append(f"--{key.replace('_', '-')}")
        else:
            cli_args.extend([f"--{key.replace('_', '-')}", str(value)])

    # Default: limit examples for CI speed
    if "num_examples" not in args:
        cli_args.extend(["--num-examples", "20"])

    # Always log to CSV for parsing
    if "log_to_csv" not in args:
        cli_args.extend(["--log-to-csv", "/tmp/sf_textattack_results.csv"])

    return cli_args


def parse_textattack_output(
    stdout: str, csv_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Parse textattack output into SentinelForge findings.

    TextAttack outputs a summary table and optionally CSV results.
    """
    findings = []

    # Try CSV output first
    if csv_path:
        try:
            findings = _parse_csv_results(csv_path)
            if findings:
                return findings
        except Exception as e:
            logger.warning(f"CSV parse failed: {e}")

    # Fall back to stdout parsing
    return _parse_stdout_results(stdout)


def _parse_csv_results(csv_path: str) -> List[Dict[str, Any]]:
    """Parse textattack CSV results file."""
    findings = []
    try:
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result_type = row.get("result_type", "").lower()
                if result_type in ("successful", "skipped"):
                    if result_type == "successful":
                        findings.append(
                            {
                                "tool": "textattack",
                                "title": "textattack: Successful adversarial attack",
                                "severity": _classify_severity(row),
                                "description": (
                                    f"Original: {row.get('original_text', '')[:200]}\n"
                                    f"Perturbed: {row.get('perturbed_text', '')[:200]}"
                                ),
                                "mitre_technique": "AML.T0043.000",
                                "remediation": (
                                    "Improve model robustness against adversarial text perturbations. "
                                    "Consider adversarial training or input preprocessing."
                                ),
                                "raw": dict(row),
                            }
                        )
    except FileNotFoundError:
        pass
    return findings


def _parse_stdout_results(stdout: str) -> List[Dict[str, Any]]:
    """Parse textattack stdout summary for attack results."""
    findings = []
    lines = stdout.strip().splitlines()

    success_count = 0
    total_count = 0

    for line in lines:
        line_lower = line.lower()

        # Parse summary line: "Successful: X/Y (Z%)"
        if "successful" in line_lower and "/" in line:
            try:
                parts = line.split(":")[-1].strip()
                fraction = parts.split("(")[0].strip()
                nums = fraction.split("/")
                success_count = int(nums[0].strip())
                total_count = int(nums[1].strip())
            except (IndexError, ValueError):
                pass

    if success_count > 0:
        attack_rate = (success_count / total_count * 100) if total_count > 0 else 0
        severity = (
            "critical" if attack_rate > 50 else "high" if attack_rate > 25 else "medium"
        )

        findings.append(
            {
                "tool": "textattack",
                "title": f"textattack: {success_count}/{total_count} attacks successful ({attack_rate:.0f}%)",
                "severity": severity,
                "description": (
                    f"Adversarial attack success rate: {attack_rate:.1f}%\n"
                    f"Successful attacks: {success_count}, Total: {total_count}"
                ),
                "mitre_technique": "AML.T0043.000",
                "remediation": (
                    "Model is vulnerable to adversarial text perturbations. "
                    "Implement adversarial training, input sanitization, or ensemble defenses."
                ),
                "raw": {"success_count": success_count, "total_count": total_count},
            }
        )

    return findings


def _classify_severity(row: dict) -> str:
    """Classify finding severity based on attack result details."""
    # Number of word modifications — fewer modifications = easier attack = higher severity
    num_queries = int(row.get("num_queries", 999))
    if num_queries <= 5:
        return "critical"
    if num_queries <= 20:
        return "high"
    return "medium"
