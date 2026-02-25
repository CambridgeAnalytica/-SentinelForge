"""
Arcanum Prompt Injection Taxonomy — classification system for AI security findings.

Based on Arcanum Security's prompt injection taxonomy (arc_pi_taxonomy)
which provides systematic attack classification beyond MITRE ATLAS.

This module adds a specialized AI-attack-focused classification layer
that maps scenario test types and MITRE techniques to Arcanum categories.
Integrated into the compliance/reporting pipeline alongside OWASP/NIST/EU AI Act.

Reference: https://github.com/Arcanum-Sec/arc_pi_taxonomy
"""

from typing import Any, Dict, List, Optional

# ===========================================================================
# Arcanum Prompt Injection Taxonomy Categories
# ===========================================================================

ARCANUM_PI_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "ARC-PI-001": {
        "id": "ARC-PI-001",
        "name": "Direct Prompt Injection",
        "description": (
            "Attacker directly includes malicious instructions in the user "
            "message to override the system prompt or safety guidelines."
        ),
        "subcategories": [
            "instruction_override",
            "system_prompt_extraction",
            "role_assumption",
        ],
        "mitre_atlas": ["AML.T0051.001"],
        "test_types": ["direct_injection", "meta_prompt"],
        "severity_baseline": "high",
    },
    "ARC-PI-002": {
        "id": "ARC-PI-002",
        "name": "Indirect Prompt Injection",
        "description": (
            "Malicious instructions embedded in external data sources "
            "(documents, web pages, tool outputs) that the model processes."
        ),
        "subcategories": [
            "document_injection",
            "web_content_injection",
            "tool_output_injection",
            "email_injection",
        ],
        "mitre_atlas": ["AML.T0051.002"],
        "test_types": ["indirect", "indirect_injection", "tool_result_poisoning"],
        "severity_baseline": "high",
    },
    "ARC-PI-003": {
        "id": "ARC-PI-003",
        "name": "Encoding & Obfuscation",
        "description": (
            "Injection payloads disguised through encoding schemes (base64, "
            "ROT13, hex, unicode, leetspeak, morse, binary) to bypass filters."
        ),
        "subcategories": [
            "base64_encoding",
            "rot13_encoding",
            "hex_encoding",
            "unicode_obfuscation",
            "leetspeak",
            "morse_code",
            "binary_ascii",
            "nato_phonetic",
            "pig_latin",
            "reversed_text",
        ],
        "mitre_atlas": ["AML.T0051.000", "AML.T0051.001"],
        "test_types": [
            "encoding",
            "rot13_encoding",
            "leetspeak",
            "morse_code",
            "nato_phonetic",
            "reversed_piglatin",
            "binary_ascii",
            "obfuscation",
            "homoglyph",
            "bidi_override",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-004": {
        "id": "ARC-PI-004",
        "name": "Context Manipulation",
        "description": (
            "Attacks that exploit context boundaries, chat template formatting, "
            "or conversation structure to inject instructions."
        ),
        "subcategories": [
            "boundary_injection",
            "template_injection",
            "delimiter_confusion",
            "context_overflow",
        ],
        "mitre_atlas": ["AML.T0051.000"],
        "test_types": [
            "context",
            "overflow",
            "virtualization",
            "split_payload",
            "structured_output_injection",
            "html_xss_injection",
            "csv_formula_injection",
            "template_injection",
            "log_injection",
            "serialization_injection",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-005": {
        "id": "ARC-PI-005",
        "name": "Jailbreak & Persona Adoption",
        "description": (
            "Attacks that attempt to make the model adopt an unrestricted "
            "persona (DAN, STAN, etc.) or enter a fictional 'developer mode'."
        ),
        "subcategories": [
            "dan_variants",
            "developer_mode",
            "character_roleplay",
            "persona_hijack",
            "philosophical_override",
            "defense_aware",
        ],
        "mitre_atlas": ["AML.T0051.000", "AML.T0054.000"],
        "test_types": ["jailbreak", "roleplay", "philosophical", "defense_aware"],
        "severity_baseline": "critical",
    },
    "ARC-PI-006": {
        "id": "ARC-PI-006",
        "name": "Data Exfiltration",
        "description": (
            "Attacks designed to extract sensitive data including system "
            "prompts, PII, API keys, training data, or cross-session information."
        ),
        "subcategories": [
            "system_prompt_extraction",
            "pii_extraction",
            "credential_leakage",
            "training_data_extraction",
            "side_channel_extraction",
            "cross_session_leakage",
        ],
        "mitre_atlas": ["AML.T0024.000", "AML.T0054.000", "AML.T0044.000"],
        "test_types": [
            "meta_prompt",
            "pii",
            "credentials",
            "memorization",
            "side_channel",
            "access_code_extraction",
            "cross_agent_leakage",
            "config_leakage",
            "auth_token_exposure",
            "response_traversal",
            "request_template_exploit",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-007": {
        "id": "ARC-PI-007",
        "name": "Agent & Tool Manipulation",
        "description": (
            "Attacks targeting function-calling, tool use, and plugin "
            "systems — including SQL injection in parameters, SSRF, "
            "path traversal, and privilege escalation through tool chaining."
        ),
        "subcategories": [
            "sql_injection_in_tools",
            "path_traversal",
            "ssrf",
            "argument_injection",
            "tool_hallucination",
            "privilege_escalation",
        ],
        "mitre_atlas": ["AML.T0051.000", "AML.T0051.002", "AML.T0040.000"],
        "test_types": [
            "sql_injection",
            "path_traversal",
            "ssrf",
            "argument_injection",
            "tool_hallucination",
            "privilege_escalation",
            "plugin_auth_bypass",
            "cross_plugin_chain",
            "permission_escalation",
            "callback_injection",
            "schema_poisoning",
            "plugin_output_trust",
        ],
        "severity_baseline": "critical",
    },
    "ARC-PI-008": {
        "id": "ARC-PI-008",
        "name": "Goal & Task Hijacking",
        "description": (
            "Attacks that redirect an agent's intended objective — making it "
            "approve unauthorized transactions, bypass workflows, or perform "
            "actions outside its designed purpose."
        ),
        "subcategories": [
            "financial_fraud",
            "approval_bypass",
            "business_logic_abuse",
            "objective_redirection",
            "reward_hacking",
        ],
        "mitre_atlas": ["AML.T0051.000", "AML.T0051.001", "AML.T0040.000"],
        "test_types": [
            "financial_goal_hijack",
            "business_logic_bypass",
            "approval_bypass",
            "objective_redirection",
            "reward_hacking",
            "workflow_manipulation",
        ],
        "severity_baseline": "critical",
    },
    "ARC-PI-009": {
        "id": "ARC-PI-009",
        "name": "Constraint Relaxation",
        "description": (
            "Attacks that convince the model to weaken or remove its safety "
            "constraints, rate limits, access controls, or content filters."
        ),
        "subcategories": [
            "safety_filter_bypass",
            "rate_limit_removal",
            "access_control_weakening",
            "content_filter_disable",
        ],
        "mitre_atlas": ["AML.T0051.000"],
        "test_types": [
            "constraint_relaxation",
            "instruction_hijacking",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-010": {
        "id": "ARC-PI-010",
        "name": "Multi-Step Chain Attack",
        "description": (
            "Attacks that use multiple turns or steps to gradually escalate "
            "from benign requests to harmful ones, including crescendo "
            "attacks and multi-agent chain exploitation."
        ),
        "subcategories": [
            "gradual_trust_escalation",
            "context_manipulation_escalation",
            "role_persistence",
            "inter_agent_chain",
            "delegation_abuse",
        ],
        "mitre_atlas": ["AML.T0051.000"],
        "test_types": [
            "multi_turn",
            "inter_agent_injection",
            "delegation_abuse",
            "agent_impersonation",
            "memory_poisoning",
            "selective_amnesia",
            "long_context_degradation",
        ],
        "severity_baseline": "critical",
    },
    "ARC-PI-011": {
        "id": "ARC-PI-011",
        "name": "Multilingual & Cross-Script",
        "description": (
            "Injection attacks using non-English languages, mixed scripts, "
            "Unicode homoglyphs, bidirectional text overrides, and "
            "language-switching to bypass safety filters."
        ),
        "subcategories": [
            "cjk_injection",
            "rtl_injection",
            "mixed_script",
            "homoglyph_spoofing",
            "bidi_override",
        ],
        "mitre_atlas": ["AML.T0051.000", "AML.T0051.001"],
        "test_types": [
            "multilingual",
            "cjk_injection",
            "rtl_injection",
            "european_injection",
            "mixed_script",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-012": {
        "id": "ARC-PI-012",
        "name": "RAG & Retrieval Poisoning",
        "description": (
            "Attacks targeting Retrieval-Augmented Generation systems — "
            "injecting instructions via retrieved documents, conflicting "
            "context, citation fabrication, and priority confusion."
        ),
        "subcategories": [
            "document_instruction_injection",
            "conflicting_context",
            "citation_fabrication",
            "retrieval_priority_confusion",
            "data_exfiltration_via_retrieval",
        ],
        "mitre_atlas": ["AML.T0051.002", "AML.T0043.000"],
        "test_types": [
            "indirect_injection",
            "conflicting_context",
            "citation_fabrication",
            "priority_confusion",
            "exfiltration",
            "recursive",
            "source_hallucination",
            "contradictory_synthesis",
            "retrieval_false_positive",
            "attribution_failure",
            "context_boundary_confusion",
        ],
        "severity_baseline": "high",
    },
    "ARC-PI-013": {
        "id": "ARC-PI-013",
        "name": "Content Safety Bypass",
        "description": (
            "Attacks that attempt to generate harmful, toxic, biased, or "
            "policy-violating content by circumventing content safety filters."
        ),
        "subcategories": [
            "toxicity_generation",
            "bias_amplification",
            "harmful_content_generation",
            "policy_boundary_testing",
        ],
        "mitre_atlas": ["AML.T0051.000"],
        "test_types": [
            "toxicity",
            "bias",
            "harmful_content",
            "content_policy",
            "boundary_testing",
            "trojan_trigger",
            "knowledge_injection",
            "demographic_poisoning",
            "finetuning_extraction",
            "label_flipping",
        ],
        "severity_baseline": "medium",
    },
}


# ===========================================================================
# Reverse index: test_type → Arcanum category
# ===========================================================================

_TEST_TYPE_INDEX: Dict[str, List[str]] = {}
_MITRE_INDEX: Dict[str, List[str]] = {}


def _build_indexes():
    """Build reverse lookups."""
    global _TEST_TYPE_INDEX, _MITRE_INDEX
    if _TEST_TYPE_INDEX:
        return

    for cat_id, cat in ARCANUM_PI_TAXONOMY.items():
        for tt in cat.get("test_types", []):
            _TEST_TYPE_INDEX.setdefault(tt, []).append(cat_id)
        for mt in cat.get("mitre_atlas", []):
            _MITRE_INDEX.setdefault(mt, []).append(cat_id)


def classify_by_test_type(test_type: str) -> List[Dict[str, Any]]:
    """Classify a finding by its test_type into Arcanum taxonomy categories."""
    _build_indexes()
    cat_ids = _TEST_TYPE_INDEX.get(test_type, [])
    return [
        {
            "taxonomy_id": cid,
            "name": ARCANUM_PI_TAXONOMY[cid]["name"],
            "severity_baseline": ARCANUM_PI_TAXONOMY[cid]["severity_baseline"],
        }
        for cid in cat_ids
    ]


def classify_by_mitre(mitre_technique: str) -> List[Dict[str, Any]]:
    """Classify a finding by its MITRE ATLAS technique into Arcanum categories."""
    _build_indexes()
    cat_ids = _MITRE_INDEX.get(mitre_technique, [])
    return [
        {
            "taxonomy_id": cid,
            "name": ARCANUM_PI_TAXONOMY[cid]["name"],
            "severity_baseline": ARCANUM_PI_TAXONOMY[cid]["severity_baseline"],
        }
        for cid in cat_ids
    ]


def classify_finding(
    test_type: Optional[str] = None,
    mitre_technique: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Classify a finding using both test_type and MITRE technique.

    Returns deduplicated list of matching Arcanum taxonomy categories.
    """
    seen = set()
    results = []

    if test_type:
        for item in classify_by_test_type(test_type):
            if item["taxonomy_id"] not in seen:
                seen.add(item["taxonomy_id"])
                results.append(item)

    if mitre_technique:
        for item in classify_by_mitre(mitre_technique):
            if item["taxonomy_id"] not in seen:
                seen.add(item["taxonomy_id"])
                results.append(item)

    return results


def get_all_categories() -> Dict[str, Dict[str, Any]]:
    """Return the full Arcanum taxonomy."""
    return ARCANUM_PI_TAXONOMY
