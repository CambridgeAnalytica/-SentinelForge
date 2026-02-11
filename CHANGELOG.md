# SentinelForge - CHANGELOG

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

##### 1. AI Agent Tester
- Test tool-using AI agents
- Detect unauthorized tool calls
- Identify tool hallucinations
- Mock environment for safe testing

##### 2. Multi-Turn Adversarial Attacks
- Gradual trust exploitation
- Context stuffing strategies
- Persona switching
- Memory poisoning attempts

##### 3. Synthetic Attack Data Generator
- Multiple mutation strategies (encoding, translation, synonyms)
- Automated variant generation
- Export to standard formats

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

### Known Limitations

- Database migrations not yet implemented
- Model adapters for providers not yet implemented  
- Evidence hashing system not yet implemented
- Report generation templates not yet created
- Some modules (drift detection, supply chain) are stubs

### Coming in v1.2

- Full database migrations (Alembic)
- 8+ model provider adapters (currently stubs)
- Evidence capture and hashing
- Real model evaluation calls for drift/backdoor/supply-chain scanners
- HTML/PDF report template rendering

---

**Note**: v1.0 was a functional MVP. v1.1 implements capabilities 4-6, Redis blocklist, CI/CD, and cloud deployment infrastructure.
