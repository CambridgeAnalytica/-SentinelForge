# SentinelForge

**Enterprise-Grade AI Security Testing & Red Teaming Platform**

> [!CAUTION]
> **AUTHORIZED USE ONLY**: This toolkit is designed EXCLUSIVELY for authorized, defensive security testing of AI systems. Use only in controlled environments with proper authorization. Misuse may violate laws and regulations.

## Overview

SentinelForge is a unified AI red teaming platform that combines the best features from several tools

Plus 6 innovative capability areas for comprehensive AI security testing.

## Features

### Core Capabilities
- **Multi-Service Architecture**: FastAPI orchestration + Python async worker pool (asyncio + asyncpg)
- **14 Integrated Tools**: All with dedicated adapters, running in isolated virtual environments
- **Provider-Agnostic**: Supports OpenAI, Anthropic, Azure OpenAI, and AWS Bedrock (4 built-in adapters)
- **Modular Probe System**: Extensible SDK for custom evaluations
- **Complete Observability**: OpenTelemetry tracing, Prometheus metrics, Grafana dashboards
- **Enterprise Security**: JWT + API key dual authentication, rate limiting, RBAC, SBOM, signed images
- **Rich Reporting**: HTML, PDF, and JSONL reports with MITRE ATLAS + OWASP LLM Top 10 mapping
- **Compliance Mapping**: Auto-tag findings with OWASP ML Top 10, NIST AI RMF, EU AI Act
- **Scheduled Scans**: Cron-based recurring scans with notification channels (Slack, email, Teams)
- **CI/CD Integration**: GitHub Actions action and GitLab CI template for pipeline security scanning
- **Dashboard UI**: Next.js web dashboard with scan overview, findings explorer, drift timeline, compliance heatmaps, and settings management (port 3001)

### Innovative Capabilities

1. **AI Agent Testing Framework**: Test multi-agent systems, detect tool misuse, identify tool hallucinations
2. **Multi-Turn Adversarial Conversations**: Automated jailbreak attempts across conversation chains
3. **Synthetic Attack Dataset Generator**: Use LLMs to generate edge case adversarial inputs
4. **Model Drift Detection**: Track safety degradation over time with baseline comparisons across 8 safety categories
5. **Adversarial Fine-Tuning Detection**: Identify backdoored or poisoned models via behavioral triggers, pickle scanning, and weight analysis
6. **Supply Chain Security Scanner**: Scan model dependencies, licenses, model cards, data provenance, and file signatures

> **All 6 capabilities are fully implemented** with API endpoints, DB models, CLI commands, and service layers. Capabilities 4-6 make real model provider calls (OpenAI, Anthropic, Azure, Bedrock). The platform includes 14/14 tool adapters, compliance auto-tagging (3 frameworks), scheduled scans with cron, API key auth, rate limiting, notification channels (Slack/email/Teams), CI/CD integration (GitHub Actions + GitLab CI), a full Next.js Dashboard UI (port 3001), and 91 tests (63 unit + 28 integration).

## Dashboard UI (v2.0)

SentinelForge includes a full-featured web dashboard at **http://localhost:3001**, built with Next.js, Tailwind CSS, Recharts, and SWR.

### Pages

| Page | Path | What It Does |
|------|------|-------------|
| **Scan Dashboard** | `/` | Stat cards (total scans, findings, critical count), severity donut chart, 14-day findings trend line, recent scans table |
| **Findings Explorer** | `/findings` | Filter by severity, tool, MITRE technique, or free-text search; sortable table; detail slide-over with raw evidence JSON |
| **Drift Timeline** | `/drift` | Select a baseline, view safety score over time as a line chart, category breakdown bars for 8 safety dimensions |
| **Schedule Manager** | `/schedules` | CRUD table for cron-based recurring scans, visual cron expression builder, manual trigger button |
| **Compliance View** | `/compliance` | Framework tabs (OWASP ML Top 10, NIST AI RMF, EU AI Act), coverage heatmap grid, summary stats, PDF download |
| **Report Viewer** | `/reports` | Report list with download links, in-browser preview (iframe), generate dialog with format toggles (HTML/PDF/JSONL) |
| **Notifications & Webhooks** | `/settings/notifications` | Channel management (Slack, email, Teams, webhook) with type icons, test/delete actions, create channel modal |
| **API Key Management** | `/settings/api-keys` | Key table with scopes and expiry, create modal, one-time copy-to-clipboard for new keys |

### Technical Details

- **Auth**: JWT login page with auth context; tokens stored client-side
- **Data Fetching**: SWR hooks with TypeScript interfaces for all API endpoints
- **Design**: Dark-first theme with severity color palette (critical/high/medium/low/info)
- **Sidebar**: Collapsible navigation + top bar with API health indicator and user menu
- **Docker**: Multi-stage build (`node:20-alpine`), served on port 3001, included in `docker compose up -d`

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development and the CLI)
- Make (optional, for convenience commands)

### Local Development

**Bash (Linux / macOS / Git Bash on Windows):**

```bash
# Clone the repository
git clone https://github.com/CambridgeAnalytica/-SentinelForge.git
cd SentinelForge

# Bootstrap local dev environment (creates Python venvs, installs deps)
make bootstrap

# REQUIRED: Create and configure your .env file
cp .env.example .env
# Edit .env and set these REQUIRED values:
#   JWT_SECRET_KEY       - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
#   DEFAULT_ADMIN_USERNAME - Your admin username
#   DEFAULT_ADMIN_PASSWORD - Must be 12+ chars with uppercase, lowercase, numbers, and symbols

# Start full stack (API, Worker, Postgres, MinIO, Prometheus, Jaeger, Grafana)
docker compose up -d

# Verify health
curl http://localhost:8000/health

# Install CLI
cd cli && pip install -e .

# Log in with the admin credentials you set in .env
sf auth login

# Run an example attack
sf attack run prompt_injection --target gpt-3.5-turbo
```

**PowerShell (Windows):**

```powershell
# Clone the repository
git clone https://github.com/CambridgeAnalytica/-SentinelForge.git
cd SentinelForge

# REQUIRED: Create and configure your .env file
Copy-Item .env.example .env
# Edit .env and set JWT_SECRET_KEY, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

# Start full stack
docker compose up -d

# Verify health
Invoke-RestMethod http://localhost:8000/health

# Install CLI
cd cli; pip install -e .

# Log in with the admin credentials you set in .env
sf auth login

# Run an example attack
sf attack run prompt_injection --target gpt-3.5-turbo
```

> **Important**: The startup will fail if `JWT_SECRET_KEY`, `DEFAULT_ADMIN_USERNAME`, and `DEFAULT_ADMIN_PASSWORD` are not set in `.env`. The admin password must be 12+ characters with complexity (mixed case, numbers, symbols). There are no default credentials -- you must set your own.

## Architecture

```
+--------------+      +---------------+      +--------------+
|   CLI        |----->|  API Service  |----->|   Postgres   |
+--------------+      |   (FastAPI)   |      +--------------+
                      +-------+-------+
+--------------+              | Queue
|  Dashboard   |              v
| (Next.js     |      +---------------+      +--------------+
|  Port 3001)  |      | Worker Pool   |----->|    MinIO      |
+--------------+      | (Python async,|--+   |  (Artifacts)  |
                      |  2 replicas)  |  |   +--------------+
                      +-------+-------+  |
                              |          |
                  +-----------+--+       |
                  v              v       v
           +-----------+  +--------------+
           | BlackICE  |  |   Model      |
           |  Tools    |  |  Adapters    |
           +-----------+  +--------------+
```

## Project Structure

```
sentinelforge/
├── dashboard/            # Next.js web dashboard (v2.0, port 3001)
├── services/
│   ├── api/              # FastAPI orchestration service
│   └── worker/           # Python async worker (asyncio + asyncpg)
├── sdk/python/           # Python SDK for probe authoring
├── cli/                  # Typer-based CLI ('sf' command)
├── adapters/
│   └── models/           # LLM provider adapters (OpenAI, Anthropic, Azure, Bedrock)
├── tools/
│   ├── registry.yaml     # BlackICE tool registry (14 tools)
│   └── executor.py       # Tool execution wrapper
├── scenarios/            # Pre-built attack scenarios (YAML)
├── playbooks/            # IR playbooks (YAML)
├── infra/
│   ├── docker/           # Dockerfiles (API, Worker, Tools, Dashboard)
│   ├── terraform/aws/    # AWS ECS/Fargate Terraform modules
│   ├── helm/             # Kubernetes Helm charts
│   ├── observability/    # Prometheus + Grafana config
│   └── security/         # SBOM, signing, scanning scripts
├── tests/                # Unit, integration, e2e tests
├── docs/                 # Full documentation suite
└── templates/            # Jinja2 report templates (HTML/PDF)
```

## CLI Usage

```bash
# Authentication
sf auth login
sf auth status

# Tool Management (BlackICE tools)
sf tools list
sf tools info garak
sf tools run garak gpt-3.5-turbo

# Attack Scenarios
sf attack list
sf attack run prompt_injection --target gpt-4
sf attack run jailbreak --target claude-3-opus

# Probes
sf probe list
sf probe run policy_compliance --target gpt-4

# AI Agent Testing
sf agent test https://my-agent.ai --tools web_search,calculator
sf agent test https://my-agent.ai --forbidden file_write,execute_code

# Multi-Turn Attacks
sf attack run multi-turn --model gpt-4 --strategy gradual_trust --turns 10

# Synthetic Data Generation
sf synthetic generate --seed prompts.txt --mutations encoding,translation --count 100

# Model Drift Detection
sf drift baseline gpt-4 --save baseline.json
sf drift compare gpt-4 --baseline baseline.json

# Supply Chain Scanning
sf supply-chain scan huggingface:org/model-name

# Backdoor Detection
sf backdoor scan huggingface:gpt2 --type behavioral
sf backdoor scans
sf backdoor show <scan_id>

# Webhook Notifications
sf webhook create https://my-server.com/hook --events attack.completed,scan.completed
sf webhook list
sf webhook delete <webhook_id>
sf webhook test <webhook_id>

# Reports
sf report generate --run-id abc123 --format html,pdf,jsonl
sf report list
sf report show abc123

# Playbooks
sf playbook list
sf playbook run jailbreak_detected --context findings.json

# Scheduled Scans (v1.5)
sf schedule create --scenario prompt_injection --cron "0 6 * * 1" --target gpt-4
sf schedule list
sf schedule trigger <schedule_id>

# API Keys (v1.5)
sf api-key create --name ci-pipeline --scopes read,write
sf api-key list

# Compliance (v1.6)
sf compliance frameworks
sf compliance summary --run-id abc123
sf compliance report --run-id abc123 --format pdf
```

## Security & Compliance

- **SBOM Generation**: All images include Software Bill of Materials
- **Image Signing**: Containers signed with cosign
- **Vulnerability Scanning**: Automated grype scans in CI
- **Audit Logging**: Complete audit trail of all runs and access
- **RBAC**: Role-based access control (Admin/Operator/Viewer)
- **Dual Authentication**: JWT Bearer tokens + API key (`X-API-Key` header)
- **Rate Limiting**: Configurable per-endpoint throttling via slowapi
- **Secrets Management**: Environment-based configuration (`.env`)
- **Evidence Redaction**: Configurable patterns for sensitive data
- **Evidence Chain**: SHA-256 hash chain for tamper-proof finding integrity
- **Compliance Frameworks**: OWASP ML Top 10, NIST AI RMF, EU AI Act auto-tagging
- **Database Migrations**: Alembic-managed schema versioning

## Documentation

- [Documentation Index](docs/INDEX.md) -- Start here for a map of all docs
- [Getting Started Guide](docs/GETTING_STARTED.md) -- Local setup walkthrough
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) -- Local, AWS, and on-premises deployment
- [Command Reference](docs/COMMAND_REFERENCE.md) -- All CLI, Make, Docker, and API commands
- [Tools Reference](docs/TOOLS_REFERENCE.md) -- All 14 integrated AI security tools
- [CI/CD Integration](ci/README.md) -- GitHub Actions + GitLab CI setup
- [Changelog](CHANGELOG.md) -- Version history and release notes

## Development

```bash
# Run tests
make test

# Lint code
make lint

# Type checking
make typecheck

# Security scan
make security-scan

# Build Docker images
make build

# Clean up
make clean
```

## Deployment

### Local (Docker Compose) -- Recommended for Getting Started
```bash
docker compose up -d
```

### AWS (ECS/Fargate)
```bash
cd infra/terraform/aws
terraform init
terraform plan -var-file=production.tfvars
terraform apply
```
> See `infra/terraform/aws/` for VPC, RDS, ElastiCache, S3, ECR, ALB, and ECS Fargate configuration.

### Kubernetes (Helm)
```bash
helm install sentinelforge infra/helm/sentinelforge \
  --set secrets.jwtSecretKey="your-256-bit-key" \
  --set secrets.adminUsername="sf_admin" \
  --set secrets.adminPassword="YourStr0ng!Pass"
```
> See `infra/helm/sentinelforge/values.yaml` for all configurable values.

## License

MIT

## Ethical Use Policy

This toolkit must be used in accordance with:
1. Applicable laws and regulations
2. Target system Terms of Service
3. Organizational security policies
4. Responsible disclosure practices

**Never use this toolkit for:**
- Unauthorized access or testing
- Real user data exposure
- Malicious intent or harm
- Evasion of monitoring or controls

---

**Built for ethical AI security testing**
