"""
Compliance Framework Mappings — MITRE ATLAS, OWASP ML/LLM Top 10, NIST AI RMF, EU AI Act, Arcanum PI.

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
        "note": "Infrastructure-level risk. Prompt-based testing can detect symptoms (biased/toxic outputs) but not root cause. Use SentinelForge supply-chain scanner for pipeline auditing.",
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
        "note": "Infrastructure-level risk. Requires statistical analysis of model outputs across many queries. Not directly testable via single-prompt injection.",
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
        "note": "Infrastructure-level risk. Requires access to model retraining pipeline. Use SentinelForge drift detection to monitor for unexpected behavior changes.",
    },
    "ML09": {
        "id": "ML09",
        "name": "Output Integrity Attack",
        "description": "Manipulating model outputs after inference but before delivery.",
        "mitre_atlas": ["AML.T0015.000"],
        "note": "Infrastructure-level risk. Targets the serving layer, not the model itself. Requires network/infrastructure security auditing.",
    },
    "ML10": {
        "id": "ML10",
        "name": "Model Poisoning (Backdoor)",
        "description": "Embedding hidden triggers in models that activate on specific inputs.",
        "mitre_atlas": ["AML.T0040.000", "AML.T0040.001"],
    },
}

# ===========================================================================
# OWASP Top 10 for LLM Applications (2025)
# https://owasp.org/www-project-top-10-for-large-language-model-applications/
# ===========================================================================

OWASP_LLM_TOP_10: Dict[str, Dict[str, Any]] = {
    "LLM01": {
        "id": "LLM01",
        "name": "Prompt Injection",
        "description": "Crafted inputs that manipulate LLM behavior by overriding system instructions, injecting via untrusted data sources, or exploiting parsing weaknesses.",
        "mitre_atlas": [
            "AML.T0051.000",
            "AML.T0051.001",
            "AML.T0051.002",
        ],
    },
    "LLM02": {
        "id": "LLM02",
        "name": "Insecure Output Handling",
        "description": "Failure to validate, sanitize, or escape LLM outputs before passing them to downstream systems, enabling XSS, SSRF, code injection, or privilege escalation.",
        "mitre_atlas": ["AML.T0043.000", "AML.T0043.001", "AML.T0015.000"],
    },
    "LLM03": {
        "id": "LLM03",
        "name": "Training Data Poisoning",
        "description": "Manipulation of training data to embed vulnerabilities, biases, or backdoors that affect model outputs at inference time.",
        "mitre_atlas": ["AML.T0020.000", "AML.T0020.001"],
        "note": "Infrastructure-level risk. Prompt-based testing can detect symptoms (biased outputs) but not root cause.",
    },
    "LLM04": {
        "id": "LLM04",
        "name": "Model Denial of Service",
        "description": "Inputs designed to consume excessive computational resources, causing service degradation or outages through token flooding, recursive generation, or combinatorial explosion.",
        "mitre_atlas": ["AML.T0043.000", "AML.T0029.000"],
    },
    "LLM05": {
        "id": "LLM05",
        "name": "Supply Chain Vulnerabilities",
        "description": "Risks from compromised pre-trained models, poisoned training data pipelines, outdated dependencies, or malicious plugins and extensions.",
        "mitre_atlas": ["AML.T0010.000", "AML.T0010.001"],
    },
    "LLM06": {
        "id": "LLM06",
        "name": "Sensitive Information Disclosure",
        "description": "LLM reveals confidential data — PII, credentials, system prompts, proprietary information — through direct queries, inference, or side channels.",
        "mitre_atlas": [
            "AML.T0024.000",
            "AML.T0024.001",
            "AML.T0054.000",
            "AML.T0044.000",
        ],
    },
    "LLM07": {
        "id": "LLM07",
        "name": "Insecure Plugin Design",
        "description": "LLM plugins or tool integrations that lack proper access controls, input validation, or scope restrictions, enabling privilege escalation or data exfiltration.",
        "mitre_atlas": ["AML.T0040.000"],
    },
    "LLM08": {
        "id": "LLM08",
        "name": "Excessive Agency",
        "description": "LLM systems granted excessive permissions, autonomy, or capabilities beyond what is needed, enabling unintended actions on external systems.",
        "mitre_atlas": ["AML.T0040.000", "AML.T0040.001"],
    },
    "LLM09": {
        "id": "LLM09",
        "name": "Overreliance",
        "description": "Users or systems placing undue trust in LLM outputs without verification, leading to misinformation, hallucinated facts, or insecure code being accepted.",
        "mitre_atlas": ["AML.T0056.000"],
    },
    "LLM10": {
        "id": "LLM10",
        "name": "Model Theft",
        "description": "Unauthorized extraction of model weights, parameters, architecture, or proprietary training data through API queries, side channels, or model cloning.",
        "mitre_atlas": ["AML.T0044.000", "AML.T0044.001"],
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
# MITRE ATLAS — Adversarial Threat Landscape for AI Systems
# https://atlas.mitre.org/
# ===========================================================================

MITRE_ATLAS: Dict[str, Dict[str, Any]] = {
    "AML.T0010": {
        "id": "AML.T0010",
        "name": "ML Supply Chain Compromise",
        "description": "Adversaries may compromise ML supply chain components — pre-trained models, training data, or libraries — to gain access or influence model behavior.",
        "mitre_atlas": ["AML.T0010.000", "AML.T0010.001"],
    },
    "AML.T0015": {
        "id": "AML.T0015",
        "name": "Evade ML Model",
        "description": "Adversaries craft inputs that cause an ML model to produce adversary-desired outputs including misclassification or low-confidence results.",
        "mitre_atlas": ["AML.T0015.000"],
    },
    "AML.T0019": {
        "id": "AML.T0019",
        "name": "Publish Poisoned Datasets",
        "description": "Adversaries publish poisoned datasets or models to public repositories to compromise downstream consumers.",
        "mitre_atlas": ["AML.T0019.000"],
    },
    "AML.T0020": {
        "id": "AML.T0020",
        "name": "Poison Training Data",
        "description": "Adversaries manipulate training data to embed vulnerabilities, biases, or backdoor triggers in the resulting model.",
        "mitre_atlas": ["AML.T0020.000", "AML.T0020.001"],
    },
    "AML.T0024": {
        "id": "AML.T0024",
        "name": "Exfiltration via ML Inference API",
        "description": "Adversaries extract sensitive training data or model internals through carefully crafted inference queries.",
        "mitre_atlas": ["AML.T0024.000", "AML.T0024.001"],
    },
    "AML.T0025": {
        "id": "AML.T0025",
        "name": "Exfiltration via Cyber Means",
        "description": "Adversaries use membership inference or side-channel attacks to determine if specific data was used in model training.",
        "mitre_atlas": ["AML.T0025.000"],
    },
    "AML.T0029": {
        "id": "AML.T0029",
        "name": "Denial of ML Service",
        "description": "Adversaries cause denial of service through resource exhaustion, token flooding, recursive generation, or input-triggered computational explosion.",
        "mitre_atlas": ["AML.T0029.000"],
    },
    "AML.T0040": {
        "id": "AML.T0040",
        "name": "ML Model Inference API Access",
        "description": "Adversaries leverage inference API access to probe model behavior, extract weights, or exploit tool/plugin integrations.",
        "mitre_atlas": ["AML.T0040.000", "AML.T0040.001"],
    },
    "AML.T0043": {
        "id": "AML.T0043",
        "name": "Craft Adversarial Data",
        "description": "Adversaries craft adversarial inputs — perturbations, synonym substitutions, or gradient-based attacks — to evade model safety or classification.",
        "mitre_atlas": ["AML.T0043.000", "AML.T0043.001", "AML.T0043.002"],
    },
    "AML.T0044": {
        "id": "AML.T0044",
        "name": "Full ML Model Access",
        "description": "Adversaries gain full access to model weights, architecture, or parameters enabling white-box attacks, model theft, or cloning.",
        "mitre_atlas": ["AML.T0044.000", "AML.T0044.001"],
    },
    "AML.T0051": {
        "id": "AML.T0051",
        "name": "LLM Prompt Injection",
        "description": "Adversaries craft inputs that override system instructions, inject via untrusted data sources, or exploit parsing weaknesses to manipulate LLM behavior.",
        "mitre_atlas": ["AML.T0051.000", "AML.T0051.001", "AML.T0051.002"],
    },
    "AML.T0054": {
        "id": "AML.T0054",
        "name": "LLM Meta Prompt Extraction",
        "description": "Adversaries extract the system prompt, meta prompt, or internal instructions from an LLM through direct or indirect querying techniques.",
        "mitre_atlas": ["AML.T0054.000"],
    },
    "AML.T0056": {
        "id": "AML.T0056",
        "name": "LLM Jailbreak",
        "description": "Adversaries bypass LLM safety alignment through role-play, encoding tricks, multi-turn escalation, or persona-based attacks to elicit restricted outputs.",
        "mitre_atlas": ["AML.T0056.000"],
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

    for cat_id, cat in OWASP_LLM_TOP_10.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "owasp_llm_top10",
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

    for cat_id, cat in MITRE_ATLAS.items():
        for technique in cat.get("mitre_atlas", []):
            _REVERSE_INDEX.setdefault(technique, []).append(
                {
                    "framework": "mitre_atlas",
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
        "owasp_llm_top10": OWASP_LLM_TOP_10,
        "nist_ai_rmf": NIST_AI_RMF,
        "eu_ai_act": EU_AI_ACT,
        "mitre_atlas": MITRE_ATLAS,
    }
    return frameworks.get(framework, {})


SUPPORTED_FRAMEWORKS = [
    "owasp_llm_top10",
    "owasp_ml_top10",
    "nist_ai_rmf",
    "eu_ai_act",
    "arcanum_pi",
    "mitre_atlas",
]
