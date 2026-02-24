"""
Model Fingerprinting Service — identify unknown LLMs via behavioral probes.

Sends 22 crafted probes across 6 categories and matches response patterns
against 16 known model signatures to identify the target model.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinelforge.fingerprinting")


# ── Feature Extraction ──────────────────────────────────────────────────

# Reuse refusal indicators from scoring service
REFUSAL_INDICATORS = [
    "i can't",
    "i cannot",
    "i'm not able",
    "i am not able",
    "i'm unable",
    "i am unable",
    "i won't",
    "i will not",
    "i must decline",
    "i must refuse",
    "not appropriate",
    "not able to help",
    "cannot assist",
    "cannot help with",
    "against my guidelines",
    "against my programming",
    "as an ai",
    "as a language model",
    "as an artificial intelligence",
    "i don't have the ability",
    "i do not have the ability",
    "goes against",
    "not something i can",
    "i'm designed to",
    "i am designed to",
    "potentially harmful",
    "could be harmful",
    "i should not",
    "i shouldn't",
    "that's not something",
    "not in a position to",
    "outside my capabilities",
    "beyond my scope",
]

IDENTITY_PATTERNS = {
    "openai": [r"\bopenai\b", r"\bgpt[-\s]?[34]\b", r"\bchatgpt\b"],
    "anthropic": [r"\banthropic\b", r"\bclaude\b"],
    "meta": [r"\bmeta\b", r"\bllama\b", r"\bmeta ai\b"],
    "google": [r"\bgoogle\b", r"\bgemini\b", r"\bdeepmind\b"],
    "mistral": [r"\bmistral\b", r"\bmixtral\b"],
    "cohere": [r"\bcohere\b", r"\bcommand\b"],
}

MARKDOWN_PATTERNS = [
    r"^#{1,6}\s",  # Headers
    r"^\*\s",  # Bullet lists
    r"^-\s",  # Dash lists
    r"^\d+\.\s",  # Numbered lists
    r"```",  # Code blocks
    r"\*\*[^*]+\*\*",  # Bold text
]

CUTOFF_UNCERTAINTY = [
    "i don't have information",
    "my knowledge cutoff",
    "my training data",
    "i'm not sure about",
    "i don't have access to real-time",
    "as of my last update",
    "i cannot provide current",
    "my information goes up to",
    "after my training cutoff",
    "i was trained on data",
]


def extract_features(probe_id: str, category: str, response: str) -> Dict[str, Any]:
    """Extract behavioral features from a single probe response."""
    text_lower = response.lower()
    words = response.split()
    word_count = len(words)
    char_count = len(response)
    lines = response.strip().split("\n")

    features: Dict[str, Any] = {
        "word_count": word_count,
        "char_count": char_count,
        "line_count": len(lines),
        "sentence_count": len(re.findall(r"[.!?]+", response)),
    }

    # Identity detection
    if category == "identity":
        for family, patterns in IDENTITY_PATTERNS.items():
            features[f"identity_{family}"] = any(
                re.search(p, text_lower) for p in patterns
            )

    # Refusal detection
    if category == "safety":
        refusal_count = sum(1 for ind in REFUSAL_INDICATORS if ind in text_lower)
        features["refusal_count"] = refusal_count
        features["refused"] = refusal_count >= 2
        features["refusal_length"] = word_count if refusal_count >= 2 else 0

    # Knowledge cutoff
    if category == "cutoff":
        features["expresses_uncertainty"] = any(
            p in text_lower for p in CUTOFF_UNCERTAINTY
        )
        features["provides_specific_answer"] = (
            word_count > 20 and not features["expresses_uncertainty"]
        )

    # Instruction compliance
    if category == "compliance":
        if probe_id == "compliance_wordcount":
            features["exact_word_count"] = word_count == 3
            features["word_count_diff"] = abs(word_count - 3)
        elif probe_id == "compliance_json":
            features["valid_json"] = response.strip().startswith(
                "{"
            ) and response.strip().endswith("}")
        elif probe_id == "compliance_counting":
            numbers_found = re.findall(r"^\d+$", response, re.MULTILINE)
            features["number_lines"] = len(numbers_found)
            features["counting_exact"] = len(numbers_found) == 20
        elif probe_id == "compliance_translate":
            features["french_detected"] = any(
                w in text_lower for w in ["le", "la", "sur", "chat", "tapis", "assis"]
            )

    # Markdown usage
    features["uses_markdown"] = any(
        re.search(p, response, re.MULTILINE) for p in MARKDOWN_PATTERNS
    )

    # Code presence
    features["has_code_block"] = "```" in response
    features["has_inline_code"] = bool(re.search(r"`[^`]+`", response))

    return features


# ── Scoring ─────────────────────────────────────────────────────────────


def score_identity(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score identity match based on keyword detection."""
    family = signature["family"]
    total = 0
    matches = 0
    for f in features_list:
        if f.get(f"identity_{family}"):
            matches += 1
        # Negative signal: identifies as a different family
        for neg_kw in signature.get("identity_negative", []):
            if f.get(f"identity_{neg_kw}", False):
                matches -= 0.5
        total += 1
    if total == 0:
        return 0.0
    return max(0.0, min(1.0, matches / total))


def score_safety(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score safety/refusal behavior match."""
    refusal_style = signature.get("refusal_style", "moderate")
    score = 0.0
    count = 0

    for f in features_list:
        refused = f.get("refused", False)
        refusal_len = f.get("refusal_length", 0)
        count += 1

        if refusal_style == "structured" and refused and refusal_len > 30:
            score += 1.0
        elif refusal_style == "thoughtful" and refused and refusal_len > 50:
            score += 1.0
        elif refusal_style == "philosophical" and refused and refusal_len > 80:
            score += 1.0
        elif refusal_style == "concise" and refused and refusal_len < 50:
            score += 1.0
        elif refusal_style == "brief" and refused and refusal_len < 30:
            score += 1.0
        elif refusal_style == "moderate" and refused:
            score += 0.7
        elif refusal_style in ("permissive", "weak", "inconsistent") and not refused:
            score += 0.8
        elif refusal_style == "inconsistent":
            score += 0.5  # any behavior is somewhat expected
        elif refused:
            score += 0.3
        else:
            score += 0.2

    return score / max(count, 1)


def score_cutoff(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score knowledge cutoff match."""
    knows_2024 = signature.get("cutoff_knows_2024", False)
    score = 0.0
    count = 0

    for f in features_list:
        has_answer = f.get("provides_specific_answer", False)
        uncertain = f.get("expresses_uncertainty", False)
        count += 1

        if knows_2024 and has_answer:
            score += 1.0
        elif not knows_2024 and uncertain:
            score += 1.0
        elif knows_2024 and uncertain:
            score += 0.3
        elif not knows_2024 and has_answer:
            score += 0.3
        else:
            score += 0.5

    return score / max(count, 1)


def score_compliance(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score instruction compliance match."""
    strength = signature.get("compliance_strength", "medium")
    compliant_count = 0
    total = 0

    for f in features_list:
        total += 1
        if (
            f.get("exact_word_count")
            or f.get("valid_json")
            or f.get("counting_exact")
            or f.get("french_detected")
        ):
            compliant_count += 1

    compliance_rate = compliant_count / max(total, 1)

    if strength == "high" and compliance_rate > 0.6:
        return 0.9
    elif strength == "medium" and 0.3 <= compliance_rate <= 0.7:
        return 0.8
    elif strength == "low" and compliance_rate < 0.4:
        return 0.8
    else:
        return max(
            0.2,
            1.0
            - abs(
                compliance_rate
                - {"high": 0.8, "medium": 0.5, "low": 0.2}.get(strength, 0.5)
            ),
        )


def score_style(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score style/formatting match."""
    expected_markdown = signature.get("uses_markdown", False)
    min_len, max_len = signature.get("avg_response_length", (100, 500))
    score = 0.0
    count = 0

    for f in features_list:
        count += 1
        # Markdown match
        has_md = f.get("uses_markdown", False)
        if has_md == expected_markdown:
            score += 0.5
        # Length range match
        wc = f.get("word_count", 0)
        if min_len <= wc <= max_len:
            score += 0.5
        elif wc < min_len:
            score += max(0.0, 0.5 - (min_len - wc) / max(min_len, 1))
        else:
            score += max(0.0, 0.5 - (wc - max_len) / max(max_len, 1))

    return score / max(count, 1)


def score_technical(
    features_list: List[Dict[str, Any]], signature: Dict[str, Any]
) -> float:
    """Score technical response match."""
    code_style = signature.get("code_style", "concise")
    score = 0.0
    count = 0

    for f in features_list:
        count += 1
        has_code = f.get("has_code_block", False)
        wc = f.get("word_count", 0)

        if code_style == "well_commented" and has_code and wc > 50:
            score += 1.0
        elif code_style == "concise" and has_code and wc < 100:
            score += 1.0
        elif code_style == "minimal" and wc < 60:
            score += 1.0
        elif has_code:
            score += 0.5
        else:
            score += 0.3

    return score / max(count, 1)


CATEGORY_SCORERS = {
    "identity": score_identity,
    "safety": score_safety,
    "cutoff": score_cutoff,
    "compliance": score_compliance,
    "style": score_style,
    "technical": score_technical,
}


def score_against_signatures(
    all_features: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Score extracted features against all model signatures.

    Args:
        all_features: {category: [features_per_probe]}

    Returns:
        Sorted list of {model, confidence, category_scores, reasoning}
    """
    from data.model_signatures import CATEGORY_WEIGHTS, MODEL_SIGNATURES

    results = []
    for model_id, sig in MODEL_SIGNATURES.items():
        category_scores: Dict[str, float] = {}
        for category, scorer in CATEGORY_SCORERS.items():
            feats = all_features.get(category, [])
            if feats:
                category_scores[category] = scorer(feats, sig)
            else:
                category_scores[category] = 0.5  # neutral if no probes in category

        # Weighted overall score
        weighted = sum(
            category_scores.get(cat, 0.5) * weight
            for cat, weight in CATEGORY_WEIGHTS.items()
        )

        results.append(
            {
                "model": sig["name"],
                "model_id": model_id,
                "family": sig["family"],
                "confidence": round(weighted, 4),
                "category_scores": {k: round(v, 4) for k, v in category_scores.items()},
            }
        )

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def build_behavioral_profile(
    all_features: Dict[str, List[Dict[str, Any]]],
    top_match: Dict[str, Any],
) -> str:
    """Generate a human-readable behavioral profile summary."""
    parts = []

    # Identity
    identity_feats = all_features.get("identity", [])
    identified_families = []
    for f in identity_feats:
        for family in IDENTITY_PATTERNS:
            if f.get(f"identity_{family}"):
                identified_families.append(family)
    if identified_families:
        parts.append(f"Self-identifies as: {', '.join(set(identified_families))}")
    else:
        parts.append("Does not clearly self-identify")

    # Safety
    safety_feats = all_features.get("safety", [])
    refusals = sum(1 for f in safety_feats if f.get("refused"))
    total_safety = len(safety_feats)
    if total_safety > 0:
        parts.append(f"Refused {refusals}/{total_safety} safety-sensitive prompts")

    # Style
    style_feats = all_features.get("style", [])
    avg_words = sum(f.get("word_count", 0) for f in style_feats) / max(
        len(style_feats), 1
    )
    uses_md = any(f.get("uses_markdown") for f in style_feats)
    parts.append(f"Avg response length: {int(avg_words)} words")
    parts.append(f"Uses markdown: {'Yes' if uses_md else 'No'}")

    # Top match
    parts.append(
        f"Best match: {top_match['model']} ({top_match['family']}) "
        f"with {top_match['confidence']:.1%} confidence"
    )

    return ". ".join(parts) + "."


async def run_fingerprint(
    adapter,
    probes: List[Dict[str, Any]],
    on_progress: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute fingerprint probes and return scored results.

    Args:
        adapter: Model adapter instance with send_prompt() method
        probes: List of probe dicts from FINGERPRINT_PROBES
        on_progress: Optional async callback(float) for progress updates

    Returns:
        {top_matches, category_scores, behavioral_profile, probe_results}
    """
    total = len(probes)
    all_features: Dict[str, List[Dict[str, Any]]] = {}
    probe_results: List[Dict[str, Any]] = []

    for i, probe in enumerate(probes):
        probe_id = probe["id"]
        category = probe["category"]
        prompt = probe["prompt"]

        # Send probe
        try:
            if prompt:
                response = await adapter.send_prompt(prompt)
            else:
                # Empty prompt — some models error, some respond
                try:
                    response = await adapter.send_prompt("")
                except Exception:
                    response = "[ERROR: empty prompt rejected]"
        except Exception as e:
            response = f"[ERROR: {str(e)[:200]}]"
            logger.warning(f"Probe {probe_id} failed: {e}")

        # Extract features
        features = extract_features(probe_id, category, response)
        all_features.setdefault(category, []).append(features)

        probe_results.append(
            {
                "probe_id": probe_id,
                "category": category,
                "prompt": prompt[:200] if prompt else "(empty)",
                "response_excerpt": response[:500],
                "features": features,
            }
        )

        # Progress callback
        if on_progress:
            await on_progress((i + 1) / total)

    # Score against all signatures
    matches = score_against_signatures(all_features)
    top_matches = matches[:3]

    # Category scores from top match
    category_scores = top_matches[0]["category_scores"] if top_matches else {}

    # Build behavioral profile
    profile = (
        build_behavioral_profile(all_features, top_matches[0])
        if top_matches
        else "Insufficient data"
    )

    return {
        "top_matches": top_matches,
        "category_scores": category_scores,
        "behavioral_profile": profile,
        "probe_results": probe_results,
        "total_probes": total,
    }
