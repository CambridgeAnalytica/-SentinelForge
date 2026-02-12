# SentinelForge - CHANGELOG

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

**Note**: v1.0 was a functional MVP. v1.1 implements capabilities 4-6, Redis blocklist, CI/CD, and cloud deployment infrastructure. v1.2 completes all core features with real LLM evaluation, evidence integrity, and professional report rendering. v1.3 implements capabilities 1-3 (agent testing, multi-turn adversarial, synthetic data) and fills the remaining CLI gaps.
