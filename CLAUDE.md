# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is SentinelForge

Enterprise-grade AI security testing & red teaming platform. Combines 14+ containerized security tools (garak, pyrit, promptfoo, deepeval, etc.) behind a FastAPI orchestration layer with async workers, a Typer CLI, and a Python SDK. Purpose: authorized, defensive security testing of AI/LLM systems.

## Build & Run Commands

```bash
# Bootstrap (creates venvs for api, sdk, cli; installs deps; copies .env)
make bootstrap

# Start full stack (Postgres, MinIO, Jaeger, Prometheus, Grafana, API, Worker x2)
make up                # docker compose up -d
make down              # stop all
make logs              # tail all service logs

# Build Docker images
make build             # builds api, worker, tools images

# Testing
make test              # runs all Python tests (unit + integration + RBAC) + 15 Playwright E2E
make test-python       # pytest across services/api, sdk/python, cli (each in own venv)

# Run tests for a single component (activate its venv first):
cd services/api && .\venv\Scripts\activate && pytest tests/ -v --cov=. --cov-report=term-missing
cd sdk/python && .\venv\Scripts\activate && pytest tests/ -v --cov=sentinelforge_sdk
cd cli && .\venv\Scripts\activate && pytest tests/ -v

# Run a single test file or test class
pytest tests/test_sentinelforge.py::TestToolExecutor -v

# Linting & formatting
make lint              # ruff check + black --check across all Python
make format            # black + ruff --fix across all Python
make typecheck         # mypy on services/api and sdk/python

# Security
make security-scan     # SBOM (syft) + vulnerability scan (grype)
make sign              # cosign image signing

# Database
make db-migrate        # alembic upgrade head
make db-reset          # destroys and recreates postgres (destructive)
```

Pytest config is in `pytest.ini` — test discovery: `tests/` dir, `test_*.py` files, `Test*` classes, `test_*` functions. Default addopts: `-v --tb=short`.

## Architecture

```
Dashboard (Next.js :3001)  ──→  API (FastAPI :8000)  ──→  PostgreSQL 16
CLI (Typer)  ──────────────→       │                     MinIO (S3-compat)
SDK (httpx)  ──────────────→       │ queue
                                   ▼
                              Worker (async Python, 2+ replicas)
                                   │
                          ┌────────┴────────┐
                          ▼                 ▼
                     Tool Executor     Model Adapters
                     (14 tools, all      (OpenAI, Anthropic,
                      with adapters)      Azure, Bedrock, Custom)
```

### Key services

| Component | Location | Framework | Purpose |
|-----------|----------|-----------|---------|
| Dashboard | `dashboard/` | Next.js 16 + Tailwind + SWR | Web UI with 21 pages, charts, auth flow, error boundaries |
| API | `services/api/` | FastAPI + SQLAlchemy async (asyncpg) | HTTP orchestration, auth, job queuing |
| Worker | `services/worker/` | Python asyncio + asyncpg | Polls DB for queued attacks, executes tools |
| CLI | `cli/sf/main.py` | Typer + Rich | `sf` command with auth/tools/attack/report subcommands |
| SDK | `sdk/python/sentinelforge_sdk/` | httpx | Client library for programmatic access |
| Tool Executor | `tools/executor.py` | subprocess | Runs security tools in isolated venvs with input sanitization |
| Model Adapters | `adapters/models/` | httpx / boto3 | LLM provider abstraction (OpenAI, Anthropic, Azure, Bedrock, Custom Gateway) |

### API router structure

All routers in `services/api/routers/`:
- `/health`, `/ready`, `/live` — health checks (health.py)
- `/auth` — JWT login + token management (auth.py)
- `/tools` — list/execute BlackICE tools (tools.py)
- `/attacks` — launch attack scenarios, model comparison, batch audit, CSV export, hardening advisor, trends (attacks.py)
- `/reports` — generate HTML/PDF/JSONL reports (reports.py)
- `/probes` — custom probe modules (probes.py)
- `/playbooks` — incident response playbook execution (playbooks.py)
- `/drift` — model drift detection baselines + comparison (drift.py)
- `/backdoor` — backdoor detection scans (backdoor.py)
- `/supply-chain` — supply chain vulnerability scanning (supply_chain.py)
- `/agent` — AI agent safety testing (agent.py)
- `/synthetic` — synthetic adversarial data generation (synthetic.py)
- `/webhooks` — webhook notification management CRUD + test ping (webhooks.py)
- `/schedules` — scheduled/recurring scans with cron expressions (schedules.py)
- `/api-keys` — API key management for CI/CD and automation (api_keys.py)
- `/notifications` — notification channel management: Slack, email, Teams (notifications.py)
- `/compliance` — compliance framework mapping and reporting (compliance.py)
- `/audit` — admin-only audit log with filtering and pagination (audit.py)
- `/attacks/runs/{id}/stream` — SSE real-time attack progress streaming (sse.py)
- `/scoring` — custom scoring rubric CRUD + calibration endpoints (scoring.py)
- `/rag-eval` — RAG evaluation pipeline: document ingestion, TF-IDF retrieval, poison testing (rag_eval.py)
- `/tool-eval` — tool-use evaluation: forbidden tools, hallucination, arg injection (tool_eval.py)
- `/multimodal-eval` — multimodal evaluation: adversarial images + vision LLM testing (multimodal_eval.py)
- `/fingerprint` — model fingerprinting: identify unknown LLMs via behavioral probes (fingerprinting.py)

### Data flow for attack execution

1. Dashboard/CLI/SDK sends `POST /attacks/run` with scenario ID + target model + config
2. API validates, creates `AttackRun` record (status=queued) in Postgres, **commits immediately**
3. API returns run ID instantly — no blocking. Execution starts via `asyncio.create_task()`
4. Background task sets status=running, invokes `_execute_scenario()` with progress callback
5. `direct_test_service` sends each prompt to the target LLM via model adapter, scores responses
6. After each prompt, progress fraction is committed to DB (0.0–1.0 scale)
7. SSE endpoint (`/attacks/runs/{id}/stream`) polls DB every 1s, streams progress to dashboard
8. On completion: findings written with evidence hashing + dedup, webhook dispatched
9. Dashboard auto-refreshes when SSE signals completion

### Configuration

Settings loaded via pydantic-settings in `services/api/config.py` from `.env`. Security-critical settings (JWT_SECRET_KEY, DEFAULT_ADMIN_PASSWORD) have no defaults and are validated at startup — the API will refuse to start if they're weak or missing (unless DEBUG=true).

### Database models (`services/api/models.py`)

Key entities: `User` (ADMIN/OPERATOR/VIEWER roles), `AttackRun` (with `comparison_id`/`audit_id`/`run_type` for grouping), `Finding` (with MITRE ATLAS + OWASP mapping), `Report`, `ProbeModule`, `AuditLog`, `AgentTest`, `SyntheticDataset`, `WebhookEndpoint`, `Schedule`, `ApiKey`, `NotificationChannel`, `ScoringRubric`, `CalibrationRun`.

## YAML-driven configuration

- **Tool registry**: `tools/registry.yaml` — 14+ tools with capabilities, MITRE ATLAS mappings, CLI commands, default configs
- **Attack scenarios**: `scenarios/*.yaml` — 24 scenarios: prompt injection, jailbreak, data leakage, hallucination, toxicity/bias, system prompt defense, multi-turn social engineering, RAG poisoning, tool abuse, multimodal injection, code execution safety, PII handling, content policy boundary, language crossover, multi-agent chain exploitation, goal hijacking, model denial of service, model theft, insecure output handling, plugin security, training data poisoning, unsafe retrieval, agent memory attacks, adapter security
- **IR playbooks**: `playbooks/*.yaml` — automated response steps for detected incidents

## Docker Compose services

postgres (16-alpine), minio, minio-init (bucket setup), jaeger, prometheus, grafana, api, worker (2 replicas), dashboard (Next.js). All on `sf-network` bridge. Ports bound to 127.0.0.1 except API on 0.0.0.0:8000 and Dashboard on 3001.

## Important patterns

- **Three separate Python venvs**: services/api, sdk/python, and cli each have independent venvs. Always activate the correct one before running commands.
- **Makefile uses `||` fallback**: Each venv activation tries POSIX (`. venv/bin/activate`) then falls back to Windows (`venv/Scripts/activate`).
- **Input sanitization**: `tools/executor.py` blocks shell metacharacters, validates argument keys/values, prevents path traversal. All tool execution goes through this layer.
- **Startup security validation**: `config.py:validate_settings_security()` runs before the API accepts any traffic. Checks JWT secret length (>=32), admin password strength (>=12 chars), CORS wildcard blocking.
- **Tests use direct imports**: `pytest.ini` sets `pythonpath = . services/api` so tests can use `from schemas import X` or `from tools.executor import Y`. Integration tests use in-memory SQLite via conftest.py fixtures.
- **Tool adapters**: All 14 tools have dedicated adapters in `tools/*_adapter.py`. Each maps SentinelForge's generic target/args to the tool's specific CLI. Dry-run mode via `SENTINELFORGE_DRY_RUN=1`.
- **Webhook dispatch**: `services/api/services/webhook_service.py` sends HMAC-SHA256 signed POST requests to registered webhooks with retry and auto-disable.
- **Dual auth**: JWT Bearer tokens + API keys (`X-API-Key` header) with SHA-256 hashing and scopes.
- **Rate limiting**: slowapi middleware with smart key function (API key > JWT > IP fallback).
- **Compliance mapping**: OWASP LLM Top 10, OWASP ML Top 10, NIST AI RMF, EU AI Act, Arcanum PI Taxonomy, MITRE ATLAS (6 frameworks, 58 categories) auto-tagging via MITRE ATLAS reverse index + test_type classification.
- **Findings dedup**: SHA-256 fingerprinting with new/recurring classification via `services/deduplication.py`.
- **SSE streaming**: `StreamingResponse` with `text/event-stream` for real-time attack progress via `/attacks/runs/{id}/stream`. Dashboard consumes via `useAttackRunSSE` hook with live progress bar.
- **Custom scenarios**: In-memory CRUD for user-created attack scenarios via POST/PUT/DELETE `/attacks/scenarios`.
- **Error boundaries**: React `ErrorBoundary` class component in `client-shell.tsx` wrapping page content with styled retry/home fallback.

## Version Summary

- **v1.0**: MVP — 14 tools, FastAPI, CLI, SDK, attack scenarios
- **v1.1**: Drift/backdoor/supply-chain, Redis blocklist, CI/CD, Terraform, Helm
- **v1.2**: Alembic, 4 model adapters, PDF reports, S3, evidence hashing
- **v1.3**: Agent testing, multi-turn adversarial, synthetic data
- **v1.4**: Webhooks, garak+promptfoo adapters, dry-run, 91 tests (28 integration)
- **v1.5**: Scheduled scans, API keys, rate limiting, notifications, OTel, 3 more adapters
- **v1.6**: Compliance mapping, 9 more adapters (14/14 complete), CI/CD package
- **v2.0**: Next.js Dashboard UI (8 pages, SWR, Recharts, JWT auth flow)
- **v2.1**: Admin endpoints, audit log, SSE streaming, findings dedup, scenario builder, RBAC tests, Playwright E2E
- **v2.2**: SSE live progress in dashboard, Alembic migration 005, E2E auth tests, error boundaries, webhook CRUD page
- **v2.3**: Real end-to-end scan execution — non-blocking launch, live per-prompt progress via SSE, asyncio background execution
- **v2.3.1**: Scenario expansion Phase 3 — 2 new scenarios (multi-agent chain, goal hijacking), P4RS3LT0NGV3 encoding transforms, TensorTrust attack patterns, Arcanum PI Taxonomy
- **v2.4.0**: Model comparison mode, batch "full audit", system prompt hardening advisor, Arcanum dashboard view, CSV export, historical trend tracking, custom scoring rubrics
- **v2.4.1**: OWASP LLM Top 10 (5th compliance framework), 2 new scenarios (model DoS, model theft), scoring engine improvements (expanded refusal + safe deflection detection), multi-turn fallback fix
- **v2.5.0**: RAG evaluation pipeline, agent tool-use evaluation, multimodal evaluation, scoring calibration (ROC curves, confusion matrix, optimal threshold), adapter extensions (images + send_with_tools), 4 new dashboard pages, Alembic migration 008
- **v2.6.0**: Demo-ready polish — Docker Compose fixes (build-time API URL, worker health check, CORS default), seed data script (`make demo`/`make seed`), README screenshots, executive PDF report (cover page, risk score, 4-framework compliance, hardening recommendations). MITRE ATLAS (6th compliance framework), Custom Gateway adapter (5th model adapter).
- **v2.7.0**: Model fingerprinting — identify unknown LLMs behind black-box endpoints via 22 behavioral probes across 6 categories (identity, safety, cutoff, compliance, style, technical), weighted scoring against 16 model signatures, radar chart visualization, behavioral profile generation
- **v2.8.0**: Insecure Output Handling (LLM02) — XSS, CSV formula, template injection, serialization attacks. Plugin Security (LLM07) — auth bypass, cross-plugin chaining, SSRF, schema poisoning. Training Data Poisoning (LLM03) — trojan triggers, knowledge injection, demographic bias, fine-tuning extraction.
- **v2.9.0**: Unsafe Retrieval — source hallucination, contradictory synthesis, attribution failure. Agent Memory Attacks — memory poisoning, selective amnesia, long-context degradation. Adapter Security — config leakage, token exposure, request template exploits. 17 new output injection scoring indicators.
- **Current**: 243+ Python tests + 15 Playwright E2E — 24 routers, 21 dashboard pages, 24 attack scenarios (147 test cases, 711 prompts), 6 compliance frameworks (58 categories)
