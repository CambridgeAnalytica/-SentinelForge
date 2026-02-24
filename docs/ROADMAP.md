# SentinelForge Roadmap

> Last updated: 2026-02-24 (v2.7.0)

## Current State

SentinelForge v2.7.0 — model fingerprinting added:

- **24 API routers**, **21 dashboard pages**, **18 attack scenarios** (115 test cases, 555 prompts)
- **6 compliance frameworks** (58 categories): OWASP LLM Top 10, OWASP ML Top 10, NIST AI RMF, EU AI Act, Arcanum PI, MITRE ATLAS
- **14 tool adapters**, **5 model adapters** (OpenAI, Anthropic, Azure, Bedrock, Custom Gateway)
- **Model fingerprinting**: 22 probes, 16 model signatures, weighted scoring, radar chart UI
- **224+ Python tests** + **15 Playwright E2E**
- Demo mode with seed data, executive PDF reports, Docker Compose full-stack deployment

---

## v2.7 — LLM-as-Judge Scoring

**Goal**: Replace regex pattern matching with a second LLM call to judge whether target model responses are actually harmful. Dramatically improves scoring accuracy.

### What Changes
- New `LLMJudgeService` that sends the target's response to a judge model with a rubric prompt
- Judge returns structured verdict: `{harmful: bool, confidence: float, reasoning: str}`
- Falls back to current regex scoring if judge call fails or is disabled
- Config: `SCORING_MODE=pattern|llm_judge|hybrid` in `.env`
- Hybrid mode: regex first pass, LLM judge for borderline scores (0.3-0.7 range)

### Why It Matters
- Current regex matching has ~70% accuracy on edge cases (polite refusals, partial compliance)
- The v2.5 calibration pipeline already provides ground truth data to validate judge accuracy
- Industry standard (Anthropic, OpenAI, NVIDIA) for safety eval is LLM-as-judge

### Files to Create/Modify
- `services/api/services/llm_judge_service.py` — new service
- `services/api/services/scoring_service.py` — add hybrid mode
- `services/api/config.py` — `SCORING_MODE`, `JUDGE_MODEL` settings
- `adapters/models/` — reuse existing adapters for judge calls
- Dashboard: scoring calibration page shows judge vs pattern accuracy comparison

---

## v2.8 — Agentic Red Teaming

**Goal**: AI agent that autonomously adapts attack strategy based on target responses, instead of running static prompt lists.

### What Changes
- New `AgenticAttacker` class that uses an LLM to generate follow-up prompts based on target responses
- Attack strategies: escalation (start mild, escalate), pivoting (switch technique on refusal), persona chaining
- Builds on existing multi-turn infrastructure (v1.3) and agent testing framework
- New scenario type: `agentic` with configurable budget (max turns, max tokens, max cost)
- Real-time strategy visualization in dashboard (attack tree / decision graph)

### Why It Matters
- Static prompt lists test known vulnerabilities; agentic testing finds unknown ones
- Mirrors real attacker behavior (adaptive, context-aware)
- Differentiator vs. garak/promptfoo which are static

### Files to Create/Modify
- `services/api/services/agentic_attacker.py` — new orchestrator
- `services/api/services/attack_strategies.py` — strategy implementations
- `scenarios/agentic_*.yaml` — agentic scenario configs
- Dashboard: new `/agentic` page with attack tree visualization

---

## v2.9 — Integration Connectors

**Goal**: Push findings into the tools security teams actually use — ticketing, SIEM, and messaging platforms.

### Connectors

| Integration | Type | What It Does |
|-------------|------|-------------|
| **Jira** | Ticketing | Create issues from critical/high findings, link to run, attach evidence |
| **Linear** | Ticketing | Same as Jira for Linear-first teams |
| **Splunk** | SIEM | Export findings as CIM-compliant events |
| **Elastic/OpenSearch** | SIEM | Index findings for Kibana dashboards |
| **Microsoft Sentinel** | SIEM | Push to Log Analytics workspace |
| **Slack** | Messaging | Rich Block Kit messages (not just webhook text) with finding cards |
| **Teams** | Messaging | Adaptive Cards with severity badges and action buttons |
| **SARIF** | Standard | Export findings in SARIF 2.1 for GitHub Advanced Security / IDE integration |

### Architecture
- New `integrations/` directory with pluggable connector interface
- `BaseConnector` abstract class: `push_finding()`, `push_report()`, `test_connection()`
- Config via dashboard Settings page (OAuth flows for Jira/Slack, API keys for SIEM)
- Webhook events trigger connectors automatically (existing webhook infrastructure)

---

## v3.0 — Multi-Tenancy / SaaS Mode

**Goal**: Organization isolation for hosting SentinelForge as a service.

### What Changes
- `Organization` model with tenant isolation (all queries scoped by org_id)
- Per-org API keys, usage quotas, and billing counters
- Org admin role (separate from system admin)
- Shared scenario library + org-private custom scenarios
- Subdomain routing or org header-based isolation
- Usage dashboard: API calls, scans run, findings generated, storage used

### Why It Matters
- Path to recurring revenue (SaaS pricing)
- Enterprise customers need tenant isolation for compliance
- Enables offering managed security testing as a service

---

## Quick Wins (any version)

These are smaller features that can be added independently:

| Feature | Effort | Impact | Description |
|---------|--------|--------|-------------|
| **Scan diff** | Medium | High | Compare two runs of the same scenario — show regression/improvement, new/resolved findings |
| **Scheduled report emails** | Low | Medium | Auto-generate and email executive PDFs on a cron schedule (extends existing schedule + notification infra) |
| **SARIF export** | Low | High | Standard format for GitHub Advanced Security / VS Code / IDE integration |
| **OpenAPI client gen** | Low | Medium | Auto-generate TypeScript SDK from FastAPI spec for dashboard type safety |
| **Bulk finding actions** | Low | Medium | Multi-select findings in dashboard for bulk acknowledge/suppress/export |
| **Finding annotations** | Low | Medium | Add analyst notes/tags to findings, mark as false positive |
| **Dark/light theme toggle** | Low | Low | Dashboard theme switcher (currently dark-only) |
| **Scan templates** | Medium | Medium | Save scan configs (scenario + model + settings) as reusable templates |
| **Ollama adapter** | Low | High | Dedicated adapter for Ollama (currently works via OpenAI-compatible `OPENAI_BASE_URL`) |
| **Microsoft Copilot adapter** | Medium | High | Adapter for testing Microsoft 365 Copilot (`m365.cloud.microsoft/chat`). Auth via Entra ID OAuth2 + Graph API. Enables red teaming enterprise Copilot deployments with all 18 scenarios. |
| ~~**Model fingerprinting**~~ | ~~Medium~~ | ~~High~~ | ~~Detect which model is behind an endpoint~~ — **Done in v2.7.0** |

---

## Real-World Validation

Before any new features, the highest-impact activity is running the full scenario library against real models and publishing results:

1. **Run all 18 scenarios** against GPT-4o, Claude 3.5 Sonnet, Llama 3.1 70B, Mistral Large
2. **Validate scoring accuracy** using the calibration pipeline (v2.5)
3. **Publish benchmark report** — comparison table, pass rates, notable findings
4. **Use results to tune** scoring thresholds and identify false positive/negative patterns

This validates the platform end-to-end and produces strong portfolio material.

---

## Version History

| Version | Date | Highlights |
|---------|------|-----------|
| v1.0 | 2026-02-09 | MVP: 14 tools, FastAPI, CLI, SDK |
| v1.1 | 2026-02-10 | Drift/backdoor/supply-chain, Redis, CI/CD, Terraform, Helm |
| v1.2 | 2026-02-11 | Alembic, 4 model adapters, PDF reports, evidence hashing |
| v1.3 | 2026-02-12 | Agent testing, multi-turn adversarial, synthetic data |
| v1.4 | 2026-02-14 | Webhooks, garak+promptfoo adapters, dry-run, 91 tests |
| v1.5 | 2026-02-15 | Scheduled scans, API keys, rate limiting, notifications, OTel |
| v1.6 | 2026-02-16 | Compliance mapping (3 frameworks), 14/14 adapters, CI/CD package |
| v2.0 | 2026-02-16 | Next.js Dashboard (8 pages), Docker dashboard service |
| v2.1 | 2026-02-18 | Admin endpoints, audit log, SSE, findings dedup, RBAC, E2E tests |
| v2.2 | 2026-02-18 | SSE live progress, Alembic 005, error boundaries, webhook page |
| v2.3 | 2026-02-20 | Real end-to-end scan execution, non-blocking launch, live progress |
| v2.3.1 | 2026-02-20 | 2 new scenarios, encoding transforms, Arcanum PI Taxonomy |
| v2.4 | 2026-02-20 | Model comparison, batch audit, hardening advisor, trends, scoring rubrics |
| v2.4.1 | 2026-02-20 | OWASP LLM Top 10, 2 new scenarios, scoring improvements |
| v2.5 | 2026-02-20 | RAG eval, tool-use eval, multimodal eval, scoring calibration |
| v2.6 | 2026-02-22 | Demo mode, seed data, executive PDF, Docker fixes, screenshots |
| v2.7 | 2026-02-24 | Model fingerprinting: 22 probes, 16 signatures, radar chart, behavioral profiles |
