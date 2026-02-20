# SentinelForge - CHANGELOG

## [2.3.0] - 2026-02-20

### Real End-to-End Scan Execution
- **Non-blocking scan launch**: `POST /attacks/run` now returns immediately with run ID and `queued` status
- Execution runs asynchronously via `asyncio.create_task()` with its own DB session
- **Live progress tracking**: Progress updates committed to DB after each prompt, streamed via SSE
- Progress scale fixed to 0.0–1.0 (was 100.0), matching frontend `liveProgress * 100` display
- Dashboard progress bar fills smoothly in real-time as each prompt is tested
- Verified: 48-prompt scan completes in ~30s against Ollama llama3.2:3b with live progress 2%→12%→50%→98%→100%

### Per-Prompt Progress Callbacks
- `direct_test_service.run_direct_tests()` — new `on_prompt_done` callback fires after each prompt
- `multi_turn_service.run_multi_turn_attack()` — new `on_prompt_done` callback fires after each turn
- `_execute_scenario()` — counts total prompts upfront (direct + multi-turn), computes progress fraction
- Background execution writes intermediate `progress` to DB via `AsyncSessionLocal` (separate transaction)

### Pipeline Architecture
- Scan flow: Dashboard → POST /attacks/run → DB commit → asyncio.create_task → SSE progress → findings
- No more HTTP timeout on large scans — response is instant, execution is background
- Error handling: failed runs get proper status, error_message, audit log, and webhook notification
- Worker `progress` scale updated from 100.0 to 1.0 for consistency

---

## [2.2.0] - 2026-02-18

### SSE Live Progress in Dashboard
- Attack detail page (`/attacks/[id]`) now uses `useAttackRunSSE` hook to consume the SSE endpoint
- Live progress bar with percentage driven by SSE events (replaces polling)
- Pulsing green "LIVE" indicator when SSE connection is active
- Auto-refreshes findings via `mutate()` when SSE signals completion
- NEW / RECURRING badges on findings from dedup system

### Alembic Migration 005
- `005_v2_1_dedup_and_audit.py` — adds `fingerprint` (String(64), indexed) and `is_new` (Boolean) columns to `findings` table
- Creates `audit_logs` table with `user_id`, `action`, `resource_type`, `resource_id`, `details` (JSONB), `ip_address`, `created_at`
- Proper `downgrade()` for rollback

### E2E Auth Tests
- New `tests/e2e/auth.spec.ts` with 5 Playwright tests:
  - Login page renders correctly (form fields, branding, submit button)
  - Invalid credentials show error message (skipped in CI — requires API)
  - Successful login redirects to dashboard (skipped in CI — requires API)
  - Unauthenticated user sees login form
  - Sidebar navigation visible after login (skipped in CI — requires API)

### Error Boundaries
- New `ErrorBoundary` React class component (`dashboard/src/components/layout/error-boundary.tsx`)
- Styled fallback UI with error message, "Try Again" and "Go to Dashboard" buttons
- Wired into `client-shell.tsx` wrapping page content inside the authenticated layout

### Webhook Management Page
- Full CRUD page at `/settings/webhooks` replacing the previous redirect stub
- Webhook list with URL, event badges, active/disabled status, created timestamp
- URL copy-to-clipboard with visual feedback
- Test ping and delete actions per webhook
- Create modal with URL input, optional HMAC secret, event checkbox selector
- Events synced with API's `VALID_WEBHOOK_EVENTS`: `attack.completed`, `attack.failed`, `scan.completed`, `report.generated`, `agent.test.completed`

### Scenario Library Expansion (14 scenarios, 82 test cases, 394 prompts)
- **Expanded `prompt_injection.yaml`**: 8 test cases, 48 prompts (was 5/11) — added payload splitting, nested/recursive injection, virtualization/simulation attacks
- **Expanded `jailbreak.yaml`**: 8 test cases, 39 prompts (was 6/2) — added full DAN/STAN/dev_mode prompts, token smuggling/obfuscation, ethical/philosophical override
- **Expanded `data_leakage.yaml`**: 5 test cases, 30 prompts (was 4/9) — added side-channel extraction techniques
- **Fixed `toxicity_bias.yaml`**: 4 test cases, 22 prompts (was 0 prompts) — added real inline prompts for all test cases
- **Fixed `hallucination.yaml`**: 4 test cases, 21 prompts (was 0 prompts) — added real inline prompts for all test cases
- **New `system_prompt_defense.yaml`**: 6 test cases, 29 prompts across 6 techniques (repeat-above, translation tricks, few-shot priming, formatting exploits, delimiter manipulation, role confusion)
- **New `multi_turn_social_engineering.yaml`**: 6 multi-turn test cases, 28 prompts with 3 strategies (context_manipulation, role_persistence, authority_impersonation), max 15 turns
- **New `rag_poisoning.yaml`**: 6 test cases, 18 prompts targeting RAG pipelines (instruction injection, conflicting context, citation fabrication, priority confusion, data exfiltration, recursive manipulation)
- **New `tool_abuse.yaml`**: 6 test cases, 28 prompts — SQL injection in tool params, path traversal, SSRF, privilege escalation, argument injection, tool hallucination
- **New `multimodal_injection.yaml`**: 5 test cases, 20 prompts — OCR injection, alt-text/metadata injection, cross-modal confusion, steganographic payloads, adversarial visual
- **New `code_execution_safety.yaml`**: 6 test cases, 24 prompts — reverse shells, data exfiltration, credential harvesting, supply chain attacks, privilege escalation, obfuscated malicious code
- **New `pii_handling.yaml`**: 6 test cases, 27 prompts — GDPR/CCPA compliance, synthetic PII generation, PII retention, right to deletion, cross-border data, indirect extraction
- **New `content_policy_boundary.yaml`**: 6 test cases, 30 prompts — dual-use chemistry, weapons knowledge, cybersecurity dual-use, surveillance, medical gray areas, legal-but-sensitive topics
- **New `language_crossover.yaml`**: 6 test cases, 30 prompts — CJK injection, RTL scripts, European languages, mixed-script attacks, Unicode homoglyphs, bidirectional text overrides

### Enriched Scenario API
- `GET /attacks/scenarios` now returns `severity`, `category`, `owasp_llm`, `test_cases_count`, `prompt_count`, and `multi_turn` fields
- Dashboard scenarios page shows severity badges, category tags, OWASP mappings, test case/prompt counts, multi-turn indicators, and summary stat cards

### Tests
- **138 Python tests** (63 unit + 57 integration + 18 RBAC)
- **15 Playwright E2E tests** (10 dashboard + 5 auth)

---

## [2.1.0] - 2026-02-18

### Admin User Management
- New admin-only endpoints: `POST /auth/register`, `GET /auth/users`, `PATCH /auth/users/{id}/role`
- `require_admin` dependency now wired to auth router (previously defined but unused)
- `create_user()` service function with password strength validation and duplicate check

### Audit Log UI
- New dashboard page (`/audit`) with paginated table, action/user/date filters, and detail expansion
- Admin-only `GET /audit` API endpoint with filtering and pagination
- Sidebar nav item added

### Live Progress via SSE
- New `GET /attacks/runs/{run_id}/stream` endpoint — Server-Sent Events for real-time attack progress
- `useAttackRunSSE` React hook replaces 5-second SWR polling for running/queued attack runs
- Auto-closes when run completes or client disconnects

### Findings Deduplication
- SHA-256 fingerprint column on `Finding` model (hash of title+tool+severity+mitre)
- `is_new` boolean column — `True` if first occurrence of fingerprint across all runs
- `compute_fingerprint()` and `classify_findings()` in `services/deduplication.py`
- "NEW" / "RECURRING" badges displayed in attack run detail view

### Custom Scenario Builder
- New dashboard page (`/scenarios`) with visual editor for attack scenarios
- Tool multi-select, MITRE technique tags, JSON config editor, YAML preview pane
- `POST/PUT/DELETE /attacks/scenarios` CRUD endpoints (operator-only)
- Sidebar nav item added

### CI/CD
- Playwright E2E test job added to `.github/workflows/ci.yml`
- Uploads test-results as GitHub artifact on failure

### Documentation
- Test count corrected: **138 total tests** (was incorrectly listed as 120)
- CHANGELOG updated with v2.0.1 and v2.1.0 enhancements

---

## [2.0.1] - 2026-02-17

### SDK Gap Closure
- 22 new methods added to `sentinelforge_sdk/__init__.py`: webhooks CRUD + test, schedules CRUD + trigger, API keys CRUD, compliance (frameworks, summary, report), notifications CRUD + test

### Alembic Migration 004
- New migration `004_v1_5_schedules_apikeys_notifications.py` adding tables for `schedules`, `api_keys`, `notification_channels`, `compliance_mappings`
- `ComplianceMapping` model added to `models.py`

### RBAC Enforcement Tests
- `tests/test_rbac.py` with VIEWER/OPERATOR/ADMIN fixtures and role-based 403 verification

### Dashboard Detail Pages
- Attack run detail (`/attacks/[id]`) with real-time polling, progress bar, findings drilldown, evidence chain
- Compliance page enhanced with coverage progress bar and findings-per-category bar chart
- Main dashboard scan rows now clickable → navigate to detail page

### Infrastructure
- Helm chart: `dashboard-deployment.yaml`, `dashboard-service.yaml` templates; dashboard config in `values.yaml`
- Terraform: Dashboard ECR repo, ECS Fargate task/service, ALB target group + listener rule, CloudWatch logs
- Grafana: `api-performance.json` and `security-posture.json` dashboards with `provisioning.yaml`

### E2E Tests
- Playwright test suite (`tests/e2e/dashboard.spec.ts`) covering smoke, navigation, and drill-down flows
- `playwright.config.ts` with auto-start dev server

### OpenAPI Export
- `scripts/export_openapi.py` — extracts schema from FastAPI app or running server, generates `openapi.json` + optional Redoc HTML

### Tests
- **138 total tests** (63 unit + 57 integration + 18 RBAC)

---

## [2.0.0] - 2026-02-16


### Dashboard UI (Next.js)
- Full-featured web dashboard at `http://localhost:3001`
- **Scan Dashboard** (`/`): stat cards, severity donut chart, 14-day findings trend, recent scans table
- **Findings Explorer** (`/findings`): filter bar (severity, tool, MITRE technique, search), sortable table, detail slide-over with evidence JSON
- **Drift Timeline** (`/drift`): baseline selector, safety score line chart, category breakdown bars
- **Schedule Manager** (`/schedules`): CRUD table, visual cron expression builder, manual trigger
- **Compliance View** (`/compliance`): framework tabs, coverage heatmap grid, summary stats, PDF download
- **Report Viewer** (`/reports`): report list with download, in-browser preview (iframe), generate dialog with format toggles
- **Notifications & Webhooks** (`/settings/notifications`): channel management with type icons, test/delete actions, create channel modal
- **API Key Management** (`/settings/api-keys`): key table with scopes, create modal, one-time copy-to-clipboard

### Dashboard Infrastructure
- Tech stack: Next.js 16, Tailwind CSS, Recharts, SWR, Lucide icons
- Collapsible sidebar navigation + top bar with health status and user menu
- JWT authentication flow with login page and auth context
- SWR-based data fetching hooks for all API endpoints with TypeScript interfaces
- Dark-first design system with severity color palette (critical/high/medium/low/info)
- Docker integration: `Dockerfile.dashboard` (multi-stage node:20-alpine), `docker-compose.yml` service
- `.env.example` updated with `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` for port 3001

### CLI Commands (v1.5/v1.6 gap closure)
- `sf schedule create/list/trigger/delete` — cron-based recurring scan management
- `sf api-key create/list/revoke` — API key management for CI/CD and automation
- `sf compliance frameworks/summary/report` — compliance framework listing, summary aggregation, PDF/HTML report download

### Tests
- 29 new integration tests: schedules CRUD + trigger, API keys CRUD, notification channels CRUD + validation, compliance frameworks/summary/report
- 3 new error case tests for 404 handling across new endpoints
- **138 total tests** (63 unit + 57 integration + 18 RBAC), all passing

### CI/CD
- New `dashboard-build` CI job: Node 20, `npm ci` + `npm run build`
- Added `slowapi>=0.1.9` to `requirements-test.txt`
- COMMAND_REFERENCE.md audit: v2.0 tool list, API endpoint sections, environment variables

---

## [1.6.0] - 2026-02-16

### Compliance Mapping & Reporting
- Auto-tagging of findings with 3 compliance frameworks: OWASP ML Top 10, NIST AI RMF, EU AI Act
- Reverse MITRE ATLAS index for automatic framework category mapping
- New endpoints: `GET /compliance/frameworks`, `GET /compliance/summary`, `GET /compliance/report`
- Auditor-friendly PDF report generation via WeasyPrint with executive summary
- New module: `services/api/data/compliance_frameworks.py` (framework data), `services/compliance_service.py` (engine)

### Remaining Tool Adapters (9 new — 14/14 complete)
- `fickling_adapter.py` — pickle file supply chain scanning (JSON + text output parsing)
- `art_adapter.py` — Adversarial Robustness Toolbox (FGSM, PGD, backdoor, extraction)
- `rebuff_adapter.py` — prompt injection detection (heuristic, canary, similarity modes)
- `guardrails_adapter.py` — LLM output validation (PII, toxicity, schema enforcement)
- `trulens_adapter.py` — feedback functions (groundedness, relevance, RAG evaluation)
- `langkit_adapter.py` — prompt/response monitoring (toxicity, sentiment, PII)
- `cyberseceval_adapter.py` — Meta's LLM security evaluation (insecure code, cyberattack helpfulness)
- `easyedit_adapter.py` — knowledge editing vulnerability testing (ROME, MEMIT)
- `rigging_adapter.py` — multi-step red teaming conversation workflows
- All 14 tools in `registry.yaml` now have `adapter:` field

### CI/CD Integration Package
- GitHub Actions composite action (`ci/github/action.yml`) — `uses: sentinelforge/scan@v1`
- Entrypoint script with scan launcher, completion poller, severity gate enforcement
- Formatted PR comments with severity badges (🔴/🟠/🟡/✅), findings table, and top-5 detail
- GitLab CI template (`ci/gitlab/.gitlab-ci-template.yml`) — `extends: .sentinelforge-scan`
- Comprehensive usage docs (`ci/README.md`) with examples for both platforms
- Configurable `fail_on_severity` gate: `critical`, `high`, `medium`, `low`, `none`

### Tests
- All 91 tests pass (63 unit + 28 integration) with 0 errors

---

## [1.5.0] - 2026-02-16

### Scheduled / Recurring Scans
- New `Schedule` SQLAlchemy model with cron expression, next_run_at tracking
- CRUD endpoints: `POST /schedules`, `GET /schedules`, `PUT /schedules/{id}`, `DELETE /schedules/{id}`
- Manual trigger endpoint: `POST /schedules/{id}/trigger`
- Worker-side DB polling with `croniter` for schedule evaluation
- Pydantic schemas: `ScheduleCreate`, `ScheduleUpdate`, `ScheduleResponse`

### More Tool Adapters (3 new)
- `deepeval_adapter.py` — hallucination, bias, and toxicity evaluation
- `textattack_adapter.py` — NLP adversarial attacks (TextFooler, DeepWordBug, BAE)
- `pyrit_adapter.py` — automated red teaming with jailbreak templates

### Rate Limiting + API Keys
- `slowapi` middleware with smart key function: API key → JWT → IP fallback
- `ApiKey` SQLAlchemy model (SHA-256 hashed keys, expiry, scopes, last_used_at)
- Dual authentication in `middleware/auth.py`: `X-API-Key` header + JWT Bearer
- CRUD endpoints: `POST /api-keys`, `GET /api-keys`, `DELETE /api-keys/{id}`
- Configurable rate limits via `RATE_LIMIT_DEFAULT` and `RATE_LIMIT_ENABLED`

### Notification Channels
- Generic dispatcher in `services/notification_service.py`
- 4 channel types: webhook, Slack, email (SMTP), Microsoft Teams (Adaptive Cards)
- `NotificationChannel` model with per-channel configuration
- CRUD endpoints: `POST /notifications/channels`, `GET /notifications/channels`, etc.
- Test endpoint: `POST /notifications/channels/{id}/test`

### OpenTelemetry Wiring
- `telemetry.py` with OTLP trace exporter (Jaeger) and Prometheus metrics exporter
- API instrumented via `FastAPIInstrumentor`, worker instrumented for job tracing
- Prometheus `/metrics` endpoint for scraping
- Updated worker `requirements.txt` with OTel packages

### Configuration
- New settings in `config.py`:
  - `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_ENABLED`
  - `ENABLE_SCHEDULED_SCANS`
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`

### Tests
- All 91 tests pass (63 unit + 28 integration) with 0 errors

---

## [1.4.0] - 2026-02-14

### Webhook Notifications
- New API endpoints: `POST /webhooks`, `GET /webhooks`, `GET /webhooks/{id}`, `PUT /webhooks/{id}`, `DELETE /webhooks/{id}`, `POST /webhooks/{id}/test`
- HMAC-SHA256 payload signing (`X-SentinelForge-Signature` header)
- Exponential backoff retry (3 attempts: 1s, 2s, 4s)
- Auto-disable after 10 consecutive delivery failures
- 5 event types: `attack.completed`, `attack.failed`, `scan.completed`, `report.generated`, `agent.test.completed`
- Events wired into attacks, reports, agent tests, backdoor scans, and supply chain scans
- CLI commands: `sf webhook create`, `sf webhook list`, `sf webhook delete`, `sf webhook test`
- DB model: `WebhookEndpoint` with user_id, events, secret, failure_count
- Alembic migration `003_v1_4_webhook_endpoints.py`

### Real Tool Wiring
- `tools/garak_adapter.py` — maps SentinelForge target format (`openai:gpt-4`) to garak CLI args (`--model_type openai --model_name gpt-4`)
- `tools/promptfoo_adapter.py` — generates temp YAML config, maps to `promptfoo eval --config <file>`
- garak: target parsing, output (JSONL) → findings, severity classification
- promptfoo: provider mapping, red-team plugin config, JSON output → findings
- Dry-run mode (`SENTINELFORGE_DRY_RUN=1`) — returns stub output without subprocess execution
- `target_arg` override per tool in `registry.yaml`
- `default_args` merge from registry (user args take precedence)
- `allowed_args` whitelist enforced per tool

### Integration Tests
- New `tests/conftest.py` — shared fixtures: in-memory SQLite, mock auth, async HTTP client
- New `tests/test_integration.py` — 25+ async tests across 11 test classes
- Endpoint coverage: health, tools, attacks, reports, drift, agent, synthetic, webhooks, supply-chain, backdoor, error cases
- `asyncio_mode = auto` in `pytest.ini` for pytest-asyncio

### Unit Tests
- `TestGarakAdapter` (9 tests) — target parsing, arg building, output parsing
- `TestPromptfooAdapter` (6 tests) — target mapping, config generation, arg building
- `TestToolExecutorDryRun` (2 tests) — dry-run returns stub, no subprocess
- `TestWebhookSchemas` (6 tests) — create/update/response schemas, event validation
- Total: 91 tests across 20+ test classes

---

## [1.3.0] - 2026-02-12

### Agent Testing Framework (Capability 1)
- ✅ New API endpoints: `POST /agent/test`, `GET /agent/tests`, `GET /agent/tests/{id}`
- ✅ Service layer with 3 test scenarios: tool misuse, hallucination, unauthorized access
- ✅ Prompt libraries for each scenario (8 tool misuse, 5 hallucination, 7 unauthorized)
- ✅ Risk scoring: low/medium/high/critical based on finding severity
- ✅ Uses httpx.AsyncClient to test agent endpoints with adversarial prompts
- ✅ CLI commands wired to real API: `sf agent test`, `sf agent tests`, `sf agent show`
- ✅ DB model: `AgentTest` with status, config, results, risk_level

### Multi-Turn Adversarial Conversations (Capability 2)
- ✅ Multi-turn conversation engine in `services/multi_turn_service.py`
- ✅ Three attack strategies: `gradual_trust`, `context_manipulation`, `role_persistence`
- ✅ Per-turn safety scoring (0.0 = compliant/unsafe → 1.0 = refused/safe)
- ✅ Escalation detection: compares first-half vs second-half safety score averages
- ✅ Uses model adapters for real LLM calls (falls back to simulated when no API key)
- ✅ Wired into `_execute_scenario()`: scenarios with `multi_turn: true` now run multi-turn attacks
- ✅ Findings from multi-turn attacks merge into attack run results with evidence hashing

### Synthetic Data Generator (Capability 3)
- ✅ New API endpoints: `POST /synthetic/generate`, `GET /synthetic/datasets`, `GET /synthetic/datasets/{id}`
- ✅ Mutation engine with 6 mutation types:
  - `encoding` (Base64, ROT13, hex, URL)
  - `translation` (Spanish, French, German word substitution)
  - `synonym` (euphemism and synonym replacement)
  - `leetspeak` (character substitution: a→4, e→3, etc.)
  - `whitespace` (zero-width spaces, Unicode homoglyphs)
  - `fragmentation` (split/reverse recombination)
- ✅ Each mutation includes difficulty score (0.0–1.0)
- ✅ Default seed prompts for testing without user-supplied seeds
- ✅ CLI commands wired to real API: `sf synthetic generate`, `sf synthetic datasets`, `sf synthetic show`
- ✅ DB model: `SyntheticDataset` with mutations_applied, total_generated, stats

### Backdoor CLI Commands
- ✅ `sf backdoor scan <model>` → `POST /backdoor/scan`
- ✅ `sf backdoor scans` → `GET /backdoor/scans`
- ✅ `sf backdoor show <id>` → `GET /backdoor/scans/{id}`
- ✅ Rich output with risk-level color coding

### Database
- ✅ Alembic migration `002_v1_3_agent_and_synthetic.py` creates `agent_tests` and `synthetic_datasets` tables

### Tests
- ✅ 17 new tests across 5 test classes:
  - `TestAgentTestSchema` (3 tests)
  - `TestSyntheticGenSchema` (3 tests)
  - `TestMultiTurnSchema` (1 test)
  - `TestSyntheticMutations` (6 tests)
  - `TestMultiTurnService` (4 tests)
- ✅ Total test count: 40 tests across 13 test classes

---

## [1.2.0] - 2026-02-11

### Database Migrations
- ✅ Alembic migration framework configured (`alembic.ini`, `env.py`, `script.py.mako`)
- ✅ Initial migration `001_initial_schema.py` creates all 10 tables with proper indexes and constraints
- ✅ `create_all` now conditional on `DEBUG` mode; production uses `alembic upgrade head`

### Evidence Hashing (Tamper-Proof Findings)
- ✅ SHA-256 hash chain: each finding's hash includes the previous finding's hash
- ✅ `compute_evidence_hash()` and `verify_evidence_chain()` in `services/evidence_hashing.py`
- ✅ `evidence_hash` and `previous_hash` columns added to Finding model
- ✅ New endpoint: `GET /attacks/runs/{id}/verify` — verifies chain integrity
- ✅ Evidence chain status included in generated reports

### Model Provider Adapters
- ✅ AWS Bedrock adapter (boto3 bedrock-runtime, async via `asyncio.to_thread`)
- ✅ Four providers now supported: OpenAI, Anthropic, Azure OpenAI, AWS Bedrock
- ✅ Factory function `get_adapter()` with auto-detection from model name prefix

### Real Model Evaluation Calls
- ✅ **Drift detection**: 80 safety prompts across 8 categories sent via LLM adapters, rule-based refusal scoring
- ✅ **Backdoor behavioral scan**: baseline vs trigger-injected prompts with anomaly detection (length ratio, phrase matching, content divergence)
- ✅ **Backdoor pickle scan**: fickling integration via ToolExecutor for serialized model analysis
- ✅ **Backdoor weight analysis**: HuggingFace API config-level checks against known architecture defaults
- ✅ **Supply chain dependencies**: `pip-audit` subprocess for CVE scanning
- ✅ **Supply chain model card**: HuggingFace API validation of 6 required fields with completeness scoring
- ✅ **Supply chain license**: RISKY_LICENSES matching via fnmatch, commercial use determination
- ✅ **Supply chain data provenance**: dataset card verification via HuggingFace datasets API
- ✅ **Supply chain signatures**: file tree analysis for .sha256/cosign files, safetensors vs pickle detection
- ✅ All services fall back gracefully to simulated results when no API key is configured

### Report Template Rendering
- ✅ Jinja2 HTML template (`templates/report.html.j2`) with dark-theme styling and print/PDF overrides
- ✅ PDF generation via WeasyPrint (`POST /reports/generate` with `formats: ["pdf"]`)
- ✅ S3/MinIO upload service (`services/s3_service.py`) — reports auto-uploaded on generation
- ✅ New endpoint: `GET /reports/{id}/download` — download from S3 with regeneration fallback
- ✅ Inline fallback HTML renderer when Jinja2 template is unavailable
- ✅ `s3_key` field added to Report model and ReportResponse schema

### Dependencies
- Added `pip-audit>=2.7.0` for supply chain dependency scanning

---

## [1.1.0] - 2026-02-10

### Capabilities 4-6 Implemented

#### Model Drift Detection (Capability 4)
- ✅ API endpoints: `POST /drift/baseline`, `POST /drift/compare`, `GET /drift/baselines`, `GET /drift/history/{id}`
- ✅ DB models: `DriftBaseline`, `DriftResult`
- ✅ Service layer with 8 safety evaluation categories
- ✅ CLI commands wired to real API (baseline, compare, baselines)
- ✅ Configurable drift threshold (default 10%)

#### Backdoor Detection (Capability 5)
- ✅ API endpoints: `POST /backdoor/scan`, `GET /backdoor/scans`, `GET /backdoor/scans/{id}`
- ✅ DB model: `BackdoorScan`
- ✅ Three scan types: behavioral triggers, pickle analysis (via fickling), weight analysis
- ✅ Known trigger pattern library (5 patterns)
- ✅ Risk assessment (low/medium/high/critical)

#### Supply Chain Scanner (Capability 6)
- ✅ API endpoints: `POST /supply-chain/scan`, `GET /supply-chain/scans`, `GET /supply-chain/scans/{id}`
- ✅ DB model: `SupplyChainScan`
- ✅ Five check types: dependencies, model_card, license, data_provenance, signature
- ✅ CLI commands wired to real API (scan, scans)

#### Redis-Backed Token Blocklist
- ✅ Redis integration with in-memory fallback
- ✅ Token revocation via `SETEX` with automatic TTL
- ✅ Graceful degradation if Redis unavailable
- ✅ Added Redis service to Docker Compose

#### Infrastructure
- ✅ GitHub Actions CI pipeline (lint, test, typecheck, security-scan, docker-build)
- ✅ Terraform modules for AWS ECS/Fargate (VPC, RDS, ElastiCache, S3, ECR, ALB, ECS)
- ✅ Helm charts for Kubernetes deployment
- ✅ MIT LICENSE file added

#### Bug Fixes
- Fixed CHANGELOG.md: removed Go worker references, corrected tool count to 14, added missing 4 tools

---

## [1.0.0] - 2026-02-09

### 🎉 Initial Release

#### Core Infrastructure
- ✅ Complete FastAPI orchestration service
- ✅ Python async worker pool (asyncio + asyncpg) for concurrent job execution
- ✅ Docker Compose stack (API, Worker, Postgres, MinIO, Jaeger, Prometheus, Grafana)
- ✅ Multi-stage Dockerfiles for optimized builds
- ✅ Complete observability stack with OpenTelemetry tracing

#### BlackICE Tool Integration
- ✅ Tool registry with 14 AI security tools
- ✅ Isolated virtual environments per tool
- ✅ Unified tool executor with timeout and sandboxing
- ✅ MITRE ATLAS technique mapping
- ✅ Tools included:
  - garak (prompt injection)
  - promptfoo (evaluation)
  - pyrit (red teaming)
  - rebuff (injection detection)
  - textattack (adversarial ML)
  - art (adversarial robustness )
  - deepeval (LLM evaluation)
  - trulens (observability)
  - guardrails (validation)
  - langkit (monitoring)
  - fickling (pickle security)
  - cyberseceval (Meta security eval)
  - easyedit (knowledge editing)
  - rigging (LLM interaction framework)

#### Red Team Features
- ✅ FastAPI routers for attacks, probes, reports, tools
- ✅ JWT authentication with RBAC (OIDC/OAuth2 optional, not enabled by default)
- ✅ Health checks and liveness/readiness probes
- ✅ Comprehensive CLI with Typer and Rich output

#### Attack Scenarios
- ✅ Prompt injection scenario
- ✅ Jailbreak testing scenario
- ✅ Multi-tool orchestration framework
- ✅ YAML-based scenario definitions

#### Incident Response
- ✅ IR playbook for jailbreak detection
- ✅ Automated response steps
- ✅ Evidence collection and compliance

#### 🚀 NEW Innovative Capabilities

##### 1. AI Agent Tester (fully implemented in v1.3)
- Test tool-using AI agents
- Detect unauthorized tool calls
- Identify tool hallucinations

##### 2. Multi-Turn Adversarial Attacks (fully implemented in v1.3)
- Gradual trust exploitation
- Context manipulation strategies
- Role persistence / persona switching

##### 3. Synthetic Attack Data Generator (fully implemented in v1.3)
- 6 mutation strategies (encoding, translation, synonyms, leetspeak, whitespace, fragmentation)
- Automated variant generation with difficulty scoring
- Export to JSON

##### 4-6. Foundation (fully implemented in v1.1)
- Model drift detection
- Backdoor/adversarial fine-tuning detection
- Supply chain security scanner

#### Documentation
- ✅ Comprehensive README
- ✅ Getting Started guide
- ✅ Architecture overview (in implementation plan)
- ✅ Complete API documentation (via FastAPI /docs)

#### Developer Experience
- ✅ Makefile with common commands
- ✅ Environment configuration template
- ✅ Git ignore configuration
- ✅ Project structure scaffolding

### Known Limitations (resolved in v1.2)

- ~~Database migrations not yet implemented~~ → Alembic configured in v1.2
- ~~Model adapters for providers not yet implemented~~ → 4 providers in v1.2
- ~~Evidence hashing system not yet implemented~~ → SHA-256 chain in v1.2
- ~~Report generation templates not yet created~~ → Jinja2 + PDF + S3 in v1.2
- ~~Some modules (drift detection, supply chain) are stubs~~ → Real implementations in v1.2

---

**Note**: v1.0 was a functional MVP. v1.1 implements capabilities 4-6, Redis blocklist, CI/CD, and cloud deployment infrastructure. v1.2 completes all core features with real LLM evaluation, evidence integrity, and professional report rendering. v1.3 implements capabilities 1-3 (agent testing, multi-turn adversarial, synthetic data) and fills the remaining CLI gaps. v1.4 adds webhook notifications, real tool wiring (garak + promptfoo adapters with dry-run mode), and comprehensive integration tests (91 total). v1.5 adds scheduled/recurring scans, 3 more tool adapters, rate limiting with API key auth, notification channels (Slack/email/Teams), and OpenTelemetry wiring. v1.6 adds compliance mapping (OWASP ML Top 10 / NIST AI RMF / EU AI Act), completes all 14 tool adapters, and ships the CI/CD integration package (GitHub Actions + GitLab CI). v2.0 adds the full-featured Next.js Dashboard UI with 8 pages, JWT auth flow, real-time data visualization, and Docker integration. v2.1 adds admin user management, audit log, SSE streaming, findings dedup, scenario builder, RBAC tests, and Playwright E2E. v2.2 wires SSE live progress into the dashboard, adds Alembic migration 005, E2E auth tests, error boundaries, and a full webhook management page.
