"""
Compliance Framework Mappings — OWASP ML Top 10, NIST AI RMF, EU AI Act, Arcanum PI.

Maps MITRE ATLAS technique IDs to compliance framework categories
so findings can be auto-tagged for auditor-friendly reporting.
"""

from typing import Any, Dict, List

# ===========================================================================
# OWASP Machine Learning Top 10 (2023)
# https://owasp.org/www-project-machine-learning-security-top-10/
# ===========================================================================

OWASP_ML_TOP_10: Dict[str, Dict[str, Any]] = {
    "ML01": {
        "id": "ML01",
        "name": "Input Manipulation",
        "description": "Adversarial inputs designed to fool ML models into making incorrect predictions.",
        "mitre_atlas": ["AML.T0043.000", "AML.T0043.001", "AML.T0043.002"],
    },
    "ML02": {
        "id": "ML02",
        "name": "Data Poisoning",
        "description": "Corrupting training data to manipulate model behavior at inference time.",
        "mitre_atlas": ["AML.T0020.000", "AML.T0020.001"],
    },
    "ML03": {
        "id": "ML03",
        "name": "Model Inversion",
        "description": "Extracting sensitive training data or model internals through queries.",
        "mitre_atlas": ["AML.T0024.000", "AML.T0024.001"],
    },
    "ML04": {
        "id": "ML04",
        "name": "Membership Inference",
        "description": "Determining whether specific data points were in the training dataset.",
        "mitre_atlas": ["AML.T0025.000"],
    },
    "ML05": {
        "id": "ML05",
        "name": "Model Theft",
        "description": "Stealing or replicating a model through API interactions.",
        "mitre_atlas": ["AML.T0044.000", "AML.T0044.001"],
    },
    "ML06": {
        "id": "ML06",
        "name": "AI Supply Chain Attacks",
        "description": "Compromising ML components, libraries, or pre-trained models.",
        "mitre_atlas": ["AML.T0010.000", "AML.T0010.001"],
    },
    "ML07": {
        "id": "ML07",
        "name": "Transfer Learning Attack",
        "description": "Exploiting shared layers or pre-trained weights across models.",
        "mitre_atlas": ["AML.T0040.000"],
    },
    "ML08": {
        "id": "ML08",
        "name": "Model Skewing",
        "description": "Causing model drift or bias through targeted retraining pressure.",
        "mitre_atlas": ["AML.T0019.000"],
    },
    "ML09": {
        "id": "ML09",
        "name": "Output Integrity Attack",
        "description": "Manipulating model outputs after inference but before delivery.",
        "mitre_atlas": ["AML.T0015.000"],
    },
    "ML10": {
        "id": "ML10",
        "name": "Model Poisoning (Backdoor)",
        "description": "Embedding hidden triggers in models that activate on specific inputs.",
        "mitre_atlas": ["AML.T0040.000", "AML.T0040.001"],
    },
}

# ===========================================================================
# NIST AI Risk Management Framework (AI RMF 1.0)
# https://www.nist.gov/artificial-intelligence/ai-risk-management-framework
# ===========================================================================

NIST_AI_RMF: Dict[str, Dict[str, Any]] = {
    "GOVERN-1": {
        "id": "GOVERN-1",
        "function": "GOVERN",
        "name": "Policies and Procedures",
        "description": "Policies, processes, and procedures are in place for AI risk management.",
        "finding_types": ["policy_violation", "configuration_error"],
    },
    "GOVERN-2": {
        "id": "GOVERN-2",
        "function": "GOVERN",
        "name": "Accountability Structures",
        "description": "Accountability structures are in place for AI systems.",
        "finding_types": ["access_control", "authorization"],
    },
    "MAP-1": {
        "id": "MAP-1",
        "function": "MAP",
        "name": "Context Established",
        "description": "Context of the AI system is understood and documented.",
        "finding_types": ["documentation_gap"],
    },
    "MAP-2": {
        "id": "MAP-2",
        "function": "MAP",
        "name": "Categorization",
        "description": "AI system is categorized based on risk and impact.",
        "mitre_atlas": ["AML.T0056.000"],
    },
    "MEASURE-1": {
        "id": "MEASURE-1",
        "function": "MEASURE",
        "name": "Risk Assessment",
        "description": "Appropriate methods and metrics are used to assess AI risks.",
        "mitre_atlas": [
            "AML.T0043.000",
            "AML.T0051.000",
            "AML.T0040.000",
            "AML.T0010.000",
            "AML.T0056.000",
        ],
    },
    "MEASURE-2": {
        "id": "MEASURE-2",
        "function": "MEASURE",
        "name": "Evaluation and Testing",
        "description": "AI systems are evaluated for trustworthy characteristics.",
        "mitre_atlas": ["AML.T0056.000", "AML.T0043.000"],
    },
    "MANAGE-1": {
        "id": "MANAGE-1",
        "function": "MANAGE",
        "name": "Risk Treatment",
        "description": "AI risks are prioritized and treated based on impact.",
        "finding_types": ["unmitigated_risk"],
    },
    "MANAGE-2": {
        "id": "MANAGE-2",
        "function": "MANAGE",
        "name": "Monitoring and Response",
        "description": "AI risks are continuously monitored with response plans.",
        "mitre_atlas": ["AML.T0051.000", "AML.T0054.000"],
    },
}

# ===========================================================================
# EU AI Act Risk Categories (Regulation 2024/1689)
# ===========================================================================

EU_AI_ACT: Dict[str, Dict[str, Any]] = {
    "UNACCEPTABLE": {
        "id": "UNACCEPTABLE",
        "name": "Unacceptable Risk",
        "description": "AI systems that pose a clear threat to safety, livelihoods, or rights (banned).",
        "severity_threshold": "critical",
        "mitre_atlas": ["AML.T0051.000", "AML.T0040.000"],
    },
    "HIGH": {
        "id": "HIGH",
        "name": "High Risk",
        "description": "AI systems in critical areas requiring conformity assessment.",
        "severity_threshold": "high",
        "mitre_atlas": [
            "AML.T0043.000",
            "AML.T0010.000",
            "AML.T0020.000",
            "AML.T0024.000",
            "AML.T0044.000",
        ],
    },
    "LIMITED": {
        "id": "LIMITED",
        "name": "Limited Risk",
        "description": "AI systems with transparency obligations.",
        "severity_threshold": "medium",
        "mitre_atlas": ["AML.T0056.000", "AML.T0015.000"],
    },
    "MINIMAL": {
        "id": "MINIMAL",
        "name": "Minimal Risk",
        "description": "AI systems with minimal regulatory requirements.",
        "severity_threshold": "low",
        "mitre_atlas": [],
    },
}

# ===========================================================================
# Reverse index: MITRE ATLAS ID → list of (framework, category_id)
# ===========================================================================

_REVERSE_INDEX: Dict[str, List[Dict[str, str]]] = {}


def _build_reverse_index():
    """Build reverse lookup from MITRE technique → framework categories."""
    global _REVERSE_INDEX
    if _REVERSE_INDEX:
        return

    for cat_id, cat in OWASP_ML_TOP_10.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "owasp_ml_top10",
                    "category_id": cat_id,
                    "category_name": cat["name"],
                }
            )

    for cat_id, cat in NIST_AI_RMF.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "nist_ai_rmf",
                    "category_id": cat_id,
                    "category_name": cat["name"],
                }
            )

    for cat_id, cat in EU_AI_ACT.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "eu_ai_act",
                    "category_id": cat_id,
                    "category_name": cat["name"],
                }
            )

    # Arcanum PI taxonomy
    from data.arcanum_taxonomy import ARCANUM_PI_TAXONOMY

    for cat_id, cat in ARCANUM_PI_TAXONOMY.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "arcanum_pi",
                    "category_id": cat_id,
                    "category_name": cat["name"],
                }
            )


def lookup_compliance_tags(mitre_technique: str) -> List[Dict[str, str]]:
    """Return all compliance framework categories for a MITRE ATLAS technique."""
    _build_reverse_index()
    return _REVERSE_INDEX.get(mitre_technique, [])


def get_framework_categories(framework: str) -> Dict[str, Dict[str, Any]]:
    """Return all categories for a given framework."""
    if framework == "arcanum_pi":
        from data.arcanum_taxonomy import ARCANUM_PI_TAXONOMY

        return ARCANUM_PI_TAXONOMY

    frameworks = {
        "owasp_ml_top10": OWASP_ML_TOP_10,
        "nist_ai_rmf": NIST_AI_RMF,
        "eu_ai_act": EU_AI_ACT,
    }
    return frameworks.get(framework, {})


SUPPORTED_FRAMEWORKS = ["owasp_ml_top10", "nist_ai_rmf", "eu_ai_act", "arcanum_pi"]
