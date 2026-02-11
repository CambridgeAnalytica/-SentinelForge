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
- **14 Integrated Tools**: tools in isolated virtual environments
- **Provider-Agnostic**: Supports OpenAI, Anthropic, Azure, Databricks, AWS Bedrock, Google Vertex AI, and more
- **Modular Probe System**: Extensible SDK for custom evaluations
- **Complete Observability**: OpenTelemetry tracing, Prometheus metrics, Grafana dashboards
- **Enterprise Security**: JWT authentication with RBAC (OIDC/OAuth2 optional, not enabled by default), SBOM, signed images, vulnerability scanning
- **Rich Reporting**: HTML, PDF, and JSONL reports with MITRE ATLAS + OWASP LLM Top 10 mapping

### Innovative Capabilities

1. **AI Agent Testing Framework**: Test multi-agent systems, detect tool misuse, identify tool hallucinations
2. **Multi-Turn Adversarial Conversations**: Automated jailbreak attempts across conversation chains
3. **Synthetic Attack Dataset Generator**: Use LLMs to generate edge case adversarial inputs
4. **Model Drift Detection**: Track safety degradation over time with baseline comparisons across 8 safety categories
5. **Adversarial Fine-Tuning Detection**: Identify backdoored or poisoned models via behavioral triggers, pickle scanning, and weight analysis
6. **Supply Chain Security Scanner**: Scan model dependencies, licenses, model cards, data provenance, and file signatures

> **Note**: Capabilities 1-3 have foundation code in place. Capabilities 4-6 have full API endpoints, DB models, CLI integration, and service layers (model adapter calls are simulated in v1.1, real provider integration in v1.2).

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
|   CLI/UI     |----->|  API Service  |----->|   Postgres   |
+--------------+      |   (FastAPI)   |      +--------------+
                      +-------+-------+
                              | Queue
                              v
                      +---------------+      +--------------+
                      | Worker Pool   |----->|    MinIO      |
                      | (Python async,|--+   |  (Artifacts)  |
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
├── services/
│   ├── api/              # FastAPI orchestration service
│   └── worker/           # Python async worker (asyncio + asyncpg)
├── sdk/python/           # Python SDK for probe authoring
├── cli/                  # Typer-based CLI ('sf' command)
├── adapters/
│   └── models/           # LLM provider adapters (stub)
├── tools/
│   ├── registry.yaml     # BlackICE tool registry (14 tools)
│   └── executor.py       # Tool execution wrapper
├── scenarios/            # Pre-built attack scenarios (YAML)
├── playbooks/            # IR playbooks (YAML)
├── infra/
│   ├── docker/           # Dockerfiles (API, Worker, Tools)
│   ├── terraform/aws/    # AWS ECS/Fargate Terraform modules
│   ├── helm/             # Kubernetes Helm charts
│   ├── observability/    # Prometheus + Grafana config
│   └── security/         # SBOM, signing, scanning scripts
├── tests/                # Unit, integration, e2e tests
├── docs/                 # Full documentation suite
└── templates/            # Report templates (planned)
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

# Model Drift (stub in v1.0)
sf drift baseline gpt-4 --save baseline.json
sf drift compare gpt-4 --baseline baseline.json

# Supply Chain Scanning (stub in v1.0)
sf supply-chain scan huggingface:org/model-name

# Reports
sf report generate --run-id abc123 --format html,pdf,jsonl
sf report list
sf report show abc123

# Playbooks
sf playbook list
sf playbook run jailbreak_detected --context findings.json
```

## Security & Compliance

- **SBOM Generation**: All images include Software Bill of Materials
- **Image Signing**: Containers signed with cosign
- **Vulnerability Scanning**: Automated grype scans in CI
- **Audit Logging**: Complete audit trail of all runs and access
- **RBAC**: Role-based access control (Admin/Operator/Viewer)
- **JWT Authentication**: Token-based auth with configurable expiration
- **Secrets Management**: Environment-based configuration (`.env`)
- **Evidence Redaction**: Configurable patterns for sensitive data

## Documentation

- [Documentation Index](docs/INDEX.md) -- Start here for a map of all docs
- [Getting Started Guide](docs/GETTING_STARTED.md) -- Local setup walkthrough
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) -- Local, AWS, and on-premises deployment
- [Command Reference](docs/COMMAND_REFERENCE.md) -- All CLI, Make, Docker, and API commands
- [Tools Reference](docs/TOOLS_REFERENCE.md) -- All 14 integrated AI security tools
- [Executive Summary](docs/EXECUTIVE_SUMMARY.md) -- C-Suite overview and ROI analysis
- [Security Risk Assessment](docs/SECURITY_RISK_ASSESSMENT.md) -- Comprehensive cyber risk assessment
- [Test Results](docs/TEST_RESULTS.md) -- Platform test report
- [Leadership Action Plan](docs/LEADERSHIP_ACTION_PLAN.md) -- Action items with ownership and timelines

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
