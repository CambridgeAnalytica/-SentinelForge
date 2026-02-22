"""
Seed demo data for SentinelForge dashboard.

Idempotent: all demo records use "demo-" ID prefix.
Usage:
    python scripts/seed_demo_data.py          # seed
    python scripts/seed_demo_data.py --purge  # remove all demo data
"""

import asyncio
import hashlib
import sys
import os
import random
from datetime import datetime, timezone, timedelta

# Ensure project root + services/api on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "services", "api"))

from passlib.context import CryptContext  # noqa: E402

pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_fingerprint(
    title: str, tool_name: str, severity: str, mitre_technique: str = ""
) -> str:
    canonical = "|".join(
        [
            title.strip().lower(),
            tool_name.strip().lower(),
            severity.strip().lower(),
            mitre_technique.strip().lower(),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_evidence_hash(evidence: dict, previous_hash: str = "") -> str:
    import json

    payload = json.dumps(evidence, sort_keys=True) + previous_hash
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEMO_ADMIN_ID = "demo-admin-001"
DEMO_ANALYST_ID = "demo-analyst-001"

NOW = datetime.now(timezone.utc)

SCENARIOS = [
    "prompt_injection",
    "jailbreak",
    "data_leakage",
    "toxicity_bias",
    "hallucination",
    "system_prompt_defense",
    "multi_turn_social_engineering",
    "rag_poisoning",
    "tool_abuse",
    "pii_handling",
]

MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3.5-sonnet",
    "llama-3.1-70b",
    "mistral-large",
]

SEVERITIES = ["critical", "high", "medium", "low", "info"]

# MITRE ATLAS techniques that trigger compliance mappings across all 4 industry frameworks
MITRE_TECHNIQUES = [
    "AML.T0043.000",  # Prompt injection → OWASP ML + LLM + NIST + EU
    "AML.T0043.001",
    "AML.T0051.000",  # LLM prompt injection
    "AML.T0051.001",
    "AML.T0020.000",  # Poison training data
    "AML.T0024.000",  # Exfiltration
    "AML.T0024.001",
    "AML.T0044.000",  # Full pipeline
    "AML.T0010.000",  # ML supply chain
    "AML.T0010.001",
    "AML.T0025.000",  # Model evasion
    "AML.T0040.000",  # Model theft / extraction
    "AML.T0040.001",
    "AML.T0015.000",  # Craft adversarial data
    "AML.T0019.000",  # Publish poisoned model
    "AML.T0056.000",  # LLM jailbreak
    "AML.T0054.000",  # LLM data leakage
    "AML.T0029.000",  # Denial of ML service
]

TOOLS = [
    "sentinelforge",
    "garak",
    "promptfoo",
    "deepeval",
    "pyrit",
    "nemo_guardrails",
]

FINDING_TEMPLATES = [
    {
        "severity": "critical",
        "title": "System prompt extracted via multi-turn conversation",
        "description": "The model revealed its full system prompt after a series of role-play requests.",
        "remediation": "Implement system prompt protection with instruction hierarchy.",
        "mitre": "AML.T0051.000",
    },
    {
        "severity": "critical",
        "title": "SQL injection payload passed to tool call",
        "description": "Model generated a SQL injection payload in a tool argument without sanitization.",
        "remediation": "Add input validation on all tool arguments before execution.",
        "mitre": "AML.T0044.000",
    },
    {
        "severity": "critical",
        "title": "PII exfiltration via crafted output formatting",
        "description": "Model was tricked into embedding PII in markdown links that would exfiltrate data.",
        "remediation": "Implement output filtering for URL patterns containing sensitive data.",
        "mitre": "AML.T0024.000",
    },
    {
        "severity": "critical",
        "title": "Jailbreak via DAN prompt with multi-language encoding",
        "description": "Model abandoned safety guidelines after a DAN-style prompt using ROT13-encoded instructions.",
        "remediation": "Add multi-encoding detection to input preprocessing pipeline.",
        "mitre": "AML.T0056.000",
    },
    {
        "severity": "critical",
        "title": "Full training data extraction via completion attack",
        "description": "Model reproduced verbatim training data when given specific prefix sequences.",
        "remediation": "Apply differential privacy and deduplication to training pipeline.",
        "mitre": "AML.T0024.001",
    },
    {
        "severity": "high",
        "title": "Prompt injection via indirect injection in RAG context",
        "description": "Adversarial instructions embedded in retrieved documents were followed by the model.",
        "remediation": "Implement instruction hierarchy separating system/user/context privilege levels.",
        "mitre": "AML.T0043.000",
    },
    {
        "severity": "high",
        "title": "Model generated harmful content after role-play escalation",
        "description": "Multi-turn social engineering led model to produce content violating safety policy.",
        "remediation": "Implement conversation-level safety monitoring, not just per-turn.",
        "mitre": "AML.T0051.001",
    },
    {
        "severity": "high",
        "title": "Hallucinated API endpoint caused client-side error",
        "description": "Model fabricated a non-existent API endpoint in generated code, causing runtime errors.",
        "remediation": "Add factual grounding via RAG or tool-use for code generation tasks.",
        "mitre": "AML.T0015.000",
    },
    {
        "severity": "high",
        "title": "Bias detected in hiring recommendation outputs",
        "description": "Model showed statistically significant preference based on names suggesting demographic groups.",
        "remediation": "Implement fairness constraints and bias testing in evaluation pipeline.",
        "mitre": "AML.T0020.000",
    },
    {
        "severity": "high",
        "title": "Tool call to forbidden file system operation",
        "description": "Model attempted to call a file deletion tool despite explicit restrictions.",
        "remediation": "Enforce tool allowlists and add confirmation steps for destructive operations.",
        "mitre": "AML.T0044.000",
    },
    {
        "severity": "high",
        "title": "Model weight extraction via repeated confidence probing",
        "description": "Systematic probing of model confidence scores allowed partial weight reconstruction.",
        "remediation": "Rate-limit API queries and add noise to confidence outputs.",
        "mitre": "AML.T0040.000",
    },
    {
        "severity": "high",
        "title": "Gradual trust exploitation in multi-turn context",
        "description": "Attacker built trust over 5 turns before requesting unauthorized data access.",
        "remediation": "Implement per-turn safety evaluation independent of conversation history.",
        "mitre": "AML.T0043.001",
    },
    {
        "severity": "medium",
        "title": "Model disclosed internal configuration details",
        "description": "Model revealed deployment infrastructure details when asked about its 'setup'.",
        "remediation": "Add system prompt rules explicitly prohibiting infrastructure disclosure.",
        "mitre": "AML.T0054.000",
    },
    {
        "severity": "medium",
        "title": "Partial system prompt leak via instruction repetition",
        "description": "Model paraphrased portions of its system prompt when asked to summarize its instructions.",
        "remediation": "Strengthen system prompt protection instructions.",
        "mitre": "AML.T0051.000",
    },
    {
        "severity": "medium",
        "title": "Evasion via synonym substitution bypass",
        "description": "Safety filters were bypassed using synonyms for restricted terms.",
        "remediation": "Use semantic-level content analysis instead of keyword matching.",
        "mitre": "AML.T0025.000",
    },
    {
        "severity": "medium",
        "title": "Cross-language jailbreak via Chinese-to-English translation",
        "description": "Harmful instructions in Mandarin were followed when English safety training was primary.",
        "remediation": "Extend safety training to cover multilingual inputs.",
        "mitre": "AML.T0056.000",
    },
    {
        "severity": "medium",
        "title": "Inconsistent refusal across equivalent prompts",
        "description": "Model refused direct request but complied with semantically equivalent rephrasing.",
        "remediation": "Add semantic equivalence checking to safety evaluation layer.",
        "mitre": "AML.T0043.000",
    },
    {
        "severity": "medium",
        "title": "Supply chain risk: unverified model checkpoint",
        "description": "Model checkpoint lacked cryptographic signature verification.",
        "remediation": "Implement model provenance tracking with signed checksums.",
        "mitre": "AML.T0010.000",
    },
    {
        "severity": "medium",
        "title": "RAG poisoning via adversarial document injection",
        "description": "Adversarial content in knowledge base caused model to produce incorrect answers.",
        "remediation": "Implement document provenance verification and anomaly detection in RAG pipeline.",
        "mitre": "AML.T0019.000",
    },
    {
        "severity": "medium",
        "title": "Hallucinated citation with fabricated DOI",
        "description": "Model generated a realistic but non-existent academic citation with fake DOI.",
        "remediation": "Implement citation verification against known databases.",
        "mitre": "AML.T0015.000",
    },
    {
        "severity": "low",
        "title": "Model provided overly verbose response to simple query",
        "description": "Response contained unnecessary detail that could reveal implementation patterns.",
        "remediation": "Configure response length constraints for simple queries.",
        "mitre": "AML.T0054.000",
    },
    {
        "severity": "low",
        "title": "Inconsistent safety behavior across temperature settings",
        "description": "Higher temperature values led to occasionally weaker safety adherence.",
        "remediation": "Test safety properties across full temperature range.",
        "mitre": "AML.T0025.000",
    },
    {
        "severity": "low",
        "title": "Model recommended deprecated cryptographic library",
        "description": "Generated code used MD5 for password hashing instead of bcrypt/argon2.",
        "remediation": "Add security-aware code review to model output pipeline.",
        "mitre": "AML.T0010.001",
    },
    {
        "severity": "low",
        "title": "Minor information leak in error messages",
        "description": "Model's error handling revealed internal stack trace format.",
        "remediation": "Standardize error response format to avoid information leakage.",
        "mitre": "AML.T0054.000",
    },
    {
        "severity": "low",
        "title": "Token limit exhaustion via recursive prompt",
        "description": "Recursive self-referential prompt caused excessive token usage.",
        "remediation": "Implement token budget guards and recursion detection.",
        "mitre": "AML.T0029.000",
    },
    {
        "severity": "info",
        "title": "Model correctly refused harmful content generation",
        "description": "Safety alignment working as expected — model refused request for malware code.",
        "remediation": "No action needed. Document as positive test result.",
        "mitre": "AML.T0056.000",
    },
    {
        "severity": "info",
        "title": "System prompt protection held under direct extraction attempt",
        "description": "Model refused to reveal system prompt when directly asked.",
        "remediation": "No action needed. System prompt protection functioning correctly.",
        "mitre": "AML.T0051.000",
    },
    {
        "severity": "info",
        "title": "PII redaction working correctly in output",
        "description": "Model properly redacted email addresses and phone numbers from generated content.",
        "remediation": "No action needed. PII filtering working as expected.",
        "mitre": "AML.T0024.000",
    },
    {
        "severity": "info",
        "title": "Tool call validation correctly blocked unauthorized access",
        "description": "Model's tool call to restricted endpoint was properly blocked by guardrails.",
        "remediation": "No action needed. Tool validation layer functioning correctly.",
        "mitre": "AML.T0044.000",
    },
    {
        "severity": "info",
        "title": "Multi-turn context maintained without safety degradation",
        "description": "After 10 turns of conversation, safety adherence remained consistent.",
        "remediation": "No action needed. Multi-turn safety monitoring working correctly.",
        "mitre": "AML.T0043.001",
    },
]

AUDIT_ACTIONS = [
    ("auth.login", "user", None, {"ip": "192.168.1.100", "user_agent": "Mozilla/5.0"}),
    (
        "auth.login",
        "user",
        None,
        {"ip": "10.0.0.50", "user_agent": "SentinelForge-CLI/2.5"},
    ),
    (
        "attack.launched",
        "attack_run",
        "demo-run-001",
        {"scenario": "prompt_injection", "model": "gpt-4o"},
    ),
    (
        "attack.completed",
        "attack_run",
        "demo-run-001",
        {"findings_count": 8, "duration_s": 34},
    ),
    (
        "attack.launched",
        "attack_run",
        "demo-run-002",
        {"scenario": "jailbreak", "model": "claude-3.5-sonnet"},
    ),
    (
        "attack.completed",
        "attack_run",
        "demo-run-002",
        {"findings_count": 6, "duration_s": 28},
    ),
    (
        "report.generated",
        "report",
        "demo-report-001",
        {"format": "pdf", "run_id": "demo-run-001"},
    ),
    (
        "attack.launched",
        "attack_run",
        "demo-run-005",
        {"scenario": "tool_abuse", "model": "gpt-4o-mini"},
    ),
    (
        "attack.completed",
        "attack_run",
        "demo-run-005",
        {"findings_count": 5, "duration_s": 41},
    ),
    ("compliance.report_generated", "report", None, {"framework": "owasp_llm_top10"}),
    (
        "user.created",
        "user",
        DEMO_ANALYST_ID,
        {"role": "analyst", "created_by": "admin"},
    ),
    ("settings.updated", None, None, {"setting": "rate_limit", "value": "200/minute"}),
    (
        "report.generated",
        "report",
        "demo-report-002",
        {"format": "html", "run_id": "demo-run-003"},
    ),
    (
        "attack.launched",
        "attack_run",
        "demo-run-008",
        {"scenario": "pii_handling", "model": "llama-3.1-70b"},
    ),
    (
        "attack.completed",
        "attack_run",
        "demo-run-008",
        {"findings_count": 4, "duration_s": 22},
    ),
]


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


async def seed():
    from database import AsyncSessionLocal, engine, Base
    from models import (
        User,
        UserRole,
        AttackRun,
        RunStatus,
        Finding,
        AuditLog,
        Report,
        ReportFormat,
    )
    from sqlalchemy import select

    # Create tables if needed (for SQLite in dev)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check idempotency: skip if admin demo user already exists
        existing = await db.execute(select(User).where(User.id == DEMO_ADMIN_ID))
        if existing.scalar_one_or_none():
            print("Demo data already seeded. Use --purge to remove first.")
            return

        # -- 1. Users --
        admin_user = User(
            id=DEMO_ADMIN_ID,
            username="demo_admin",
            hashed_password=pwd_context.hash("DemoAdmin123!"),
            role=UserRole.ADMIN,
            is_active=True,
            created_at=NOW - timedelta(days=30),
        )
        analyst_user = User(
            id=DEMO_ANALYST_ID,
            username="demo_analyst",
            hashed_password=pwd_context.hash("DemoAnalyst456!"),
            role=UserRole.ANALYST,
            is_active=True,
            created_at=NOW - timedelta(days=14),
        )
        db.add_all([admin_user, analyst_user])
        await db.flush()
        print("  Users: 2 created")

        # -- 2. Attack Runs --
        runs = []
        run_configs = [
            ("demo-run-001", "prompt_injection", "gpt-4o", 14, RunStatus.COMPLETED),
            ("demo-run-002", "jailbreak", "claude-3.5-sonnet", 12, RunStatus.COMPLETED),
            ("demo-run-003", "data_leakage", "gpt-4o-mini", 10, RunStatus.COMPLETED),
            ("demo-run-004", "toxicity_bias", "llama-3.1-70b", 8, RunStatus.COMPLETED),
            ("demo-run-005", "tool_abuse", "gpt-4o-mini", 6, RunStatus.COMPLETED),
            (
                "demo-run-006",
                "system_prompt_defense",
                "mistral-large",
                4,
                RunStatus.COMPLETED,
            ),
            (
                "demo-run-007",
                "multi_turn_social_engineering",
                "gpt-4o",
                3,
                RunStatus.COMPLETED,
            ),
            ("demo-run-008", "pii_handling", "llama-3.1-70b", 2, RunStatus.COMPLETED),
            (
                "demo-run-009",
                "hallucination",
                "claude-3.5-sonnet",
                1,
                RunStatus.COMPLETED,
            ),
            (
                "demo-run-010",
                "rag_poisoning",
                "gpt-4o",
                0,
                RunStatus.RUNNING,
            ),  # live run
        ]

        for run_id, scenario, model, days_ago, status in run_configs:
            created = NOW - timedelta(days=days_ago, hours=random.randint(0, 12))
            started = created + timedelta(seconds=random.randint(1, 5))
            completed = (
                started + timedelta(seconds=random.randint(20, 90))
                if status == RunStatus.COMPLETED
                else None
            )
            progress = (
                1.0
                if status == RunStatus.COMPLETED
                else round(random.uniform(0.3, 0.7), 2)
            )

            run = AttackRun(
                id=run_id,
                scenario_id=scenario,
                target_model=model,
                status=status,
                progress=progress,
                run_type="attack",
                config={"max_prompts": 50, "timeout": 300},
                results=(
                    {
                        "total_prompts": random.randint(20, 48),
                        "avg_score": round(random.uniform(0.3, 0.8), 3),
                    }
                    if status == RunStatus.COMPLETED
                    else {}
                ),
                started_at=started,
                completed_at=completed,
                created_at=created,
                user_id=DEMO_ADMIN_ID,
            )
            runs.append(run)
            db.add(run)

        await db.flush()
        print(f"  Attack Runs: {len(runs)} created (1 running)")

        # -- 3. Findings --
        # Distribute findings across runs (skip the running one)
        completed_runs = [r for r in runs if r.status == RunStatus.COMPLETED]
        random.seed(42)  # Reproducible distribution

        # Target: ~50 findings total
        # Critical: 5, High: 12, Medium: 14, Low: 10, Info: 9
        severity_pool = (
            [f for f in FINDING_TEMPLATES if f["severity"] == "critical"] * 1
            + [f for f in FINDING_TEMPLATES if f["severity"] == "high"] * 2
            + [f for f in FINDING_TEMPLATES if f["severity"] == "medium"] * 2
            + [f for f in FINDING_TEMPLATES if f["severity"] == "low"] * 2
            + [f for f in FINDING_TEMPLATES if f["severity"] == "info"] * 2
        )
        random.shuffle(severity_pool)

        finding_count = 0
        previous_hash = ""
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        for i, template in enumerate(severity_pool[:50]):
            run = completed_runs[i % len(completed_runs)]
            sev = template["severity"]
            mitre = template["mitre"]

            evidence = {
                "prompt": f"[Demo] Test prompt for {template['title'][:40]}...",
                "response": f"[Demo] Model response demonstrating {sev} severity finding.",
                "safety_score": round(
                    (
                        random.uniform(0.1, 0.5)
                        if sev in ("critical", "high")
                        else random.uniform(0.5, 0.95)
                    ),
                    3,
                ),
                "test_case": f"TC-{i+1:03d}",
            }

            ev_hash = compute_evidence_hash(evidence, previous_hash)
            fp = compute_fingerprint(
                template["title"], random.choice(TOOLS), sev, mitre
            )

            finding = Finding(
                id=f"demo-finding-{i+1:03d}",
                run_id=run.id,
                tool_name=random.choice(TOOLS),
                severity=sev,
                title=template["title"],
                description=template["description"],
                mitre_technique=mitre,
                evidence=evidence,
                remediation=template["remediation"],
                evidence_hash=ev_hash,
                previous_hash=previous_hash if previous_hash else None,
                fingerprint=fp,
                is_new=i < 35,  # First 35 are new, rest are recurring
                false_positive=False,
                created_at=run.created_at + timedelta(seconds=random.randint(10, 60)),
            )
            db.add(finding)
            previous_hash = ev_hash
            finding_count += 1
            severity_counts[sev] += 1

        await db.flush()
        print(f"  Findings: {finding_count} created {severity_counts}")

        # -- 4. Reports --
        reports = [
            Report(
                id="demo-report-001",
                run_id="demo-run-001",
                format=ReportFormat.PDF,
                file_path="/reports/demo-run-001.pdf",
                generated_at=NOW - timedelta(days=13),
            ),
            Report(
                id="demo-report-002",
                run_id="demo-run-003",
                format=ReportFormat.HTML,
                file_path="/reports/demo-run-003.html",
                generated_at=NOW - timedelta(days=9),
            ),
            Report(
                id="demo-report-003",
                run_id="demo-run-005",
                format=ReportFormat.PDF,
                file_path="/reports/demo-run-005.pdf",
                generated_at=NOW - timedelta(days=5),
            ),
        ]
        db.add_all(reports)
        await db.flush()
        print(f"  Reports: {len(reports)} created")

        # -- 5. Audit Logs --
        for i, (action, res_type, res_id, details) in enumerate(AUDIT_ACTIONS):
            log = AuditLog(
                id=f"demo-audit-{i+1:03d}",
                user_id=DEMO_ADMIN_ID if i % 3 != 2 else DEMO_ANALYST_ID,
                action=action,
                resource_type=res_type,
                resource_id=res_id,
                details=details,
                ip_address="192.168.1.100" if i % 2 == 0 else "10.0.0.50",
                created_at=NOW - timedelta(days=14 - i, hours=random.randint(8, 18)),
            )
            db.add(log)

        await db.flush()
        print(f"  Audit Logs: {len(AUDIT_ACTIONS)} created")

        await db.commit()

    print("\nDemo data seeded successfully!")
    print("  Login: demo_admin / DemoAdmin123!")
    print("  Login: demo_analyst / DemoAnalyst456!")


async def purge():
    from database import AsyncSessionLocal, engine, Base
    from models import (
        User,
        AttackRun,
        Finding,
        AuditLog,
        Report,
    )
    from sqlalchemy import delete

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Delete in dependency order: findings → reports → runs → audit → users
        # Findings
        result = await db.execute(delete(Finding).where(Finding.id.like("demo-%")))
        f_count = result.rowcount

        # Reports
        result = await db.execute(delete(Report).where(Report.id.like("demo-%")))
        r_count = result.rowcount

        # Attack Runs
        result = await db.execute(delete(AttackRun).where(AttackRun.id.like("demo-%")))
        run_count = result.rowcount

        # Audit Logs
        result = await db.execute(delete(AuditLog).where(AuditLog.id.like("demo-%")))
        a_count = result.rowcount

        # Users
        result = await db.execute(delete(User).where(User.id.like("demo-%")))
        u_count = result.rowcount

        await db.commit()

    print("Purged demo data:")
    print(f"  Findings: {f_count}")
    print(f"  Reports: {r_count}")
    print(f"  Attack Runs: {run_count}")
    print(f"  Audit Logs: {a_count}")
    print(f"  Users: {u_count}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--purge" in sys.argv:
        asyncio.run(purge())
    else:
        asyncio.run(seed())
