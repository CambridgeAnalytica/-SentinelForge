# SentinelForge Command Reference

**Complete Reference for All Commands with Expected Outputs**

---

## Table of Contents

1. [Makefile Commands](#makefile-commands)
2. [Docker Compose Commands](#docker-compose-commands)
3. [CLI Commands](#cli-commands)
4. [Environment Variables](#environment-variables)
5. [API Endpoints](#api-endpoints)

---

## Makefile Commands

All `make` commands should be run from the project root directory.

### `make help`

**Purpose**: Show all available make targets

**Command**:
```bash
make help
```

**Expected Output**:
```
Usage: make [target]

Available targets:
  bootstrap            Bootstrap local development environment
  build                Build all Docker images
  up                   Start all services
  down                 Stop all services
  logs                 View logs from all services
  test                 Run all tests
  lint                 Run linters
  format               Format code
  security-scan        Run security scans
  clean                Clean up artifacts
```

---

### `make bootstrap`

**Purpose**: Set up local development environment for the first time

**Command**:
```bash
make bootstrap
```

**What it does**:
1. Creates Python virtual environments for the API, SDK, and CLI
2. Installs Python dependencies in each virtual environment
3. Creates `.env` file from `.env.example` if it doesn't exist

**Expected Output**:
```
🔧 Bootstrapping SentinelForge...
Creating Python virtual environments...
Creating .env file...
✅ Bootstrap complete!
⚠️  IMPORTANT: Edit .env and set JWT_SECRET_KEY, DEFAULT_ADMIN_USERNAME, and DEFAULT_ADMIN_PASSWORD before running 'make up'.
```

**Duration**: 2-5 minutes

---

### `make build`

**Purpose**: Build all Docker images

**Command**:
```bash
make build
```

**Expected Output**:
```
🐳 Building Docker images...
[+] Building 45.2s (15/15) FINISHED
 => [internal] load build definition                                  0.1s
 => => transferring dockerfile: 1.23kB                                0.0s
 => [internal] load .dockerignore                                     0.0s
...
=> => naming to docker.io/sentinelforge/api:latest                    0.0s

Building Worker image...
[+] Building 32.1s (12/12) FINISHED
...
=> => naming to docker.io/sentinelforge/worker:latest                 0.0s

Building Tools image...
[+] Building 90.5s (20/20) FINISHED
...
=> => naming to docker.io/sentinelforge/tools:latest                  0.0s

✅ Build complete!
```

> **Note**: The images are tagged as `sentinelforge/api:latest`, `sentinelforge/worker:latest`, and `sentinelforge/tools:latest`.

**Duration**: 3-5 minutes (first build), 30-60 seconds (subsequent)

---

### `make up`

**Purpose**: Start all services in background

**Command**:
```bash
make up
```

**Expected Output**:
```
🚀 Starting services...
[+] Running 10/10
 ✔ Network sf-network          Created                                0.1s
 ✔ Container sf-postgres       Started                                1.2s
 ✔ Container sf-minio          Started                                1.3s
 ✔ Container sf-jaeger         Started                                1.1s
 ✔ Container sf-prometheus     Started                                1.4s
 ✔ Container sf-grafana        Started                                1.5s
 ✔ Container sf-api            Started                                2.1s
 ✔ Container sf-worker         Started                                2.2s
✅ Services started!
API: http://localhost:8000
API Docs: http://localhost:8000/docs
Jaeger UI: http://localhost:16686
Prometheus: http://localhost:9090
MinIO Console: http://localhost:9001
```

**Verification**:
```bash
docker ps
```

**Expected**: All 8+ containers running

---

### `make down`

**Purpose**: Stop all services

**Command**:
```bash
make down
```

**Expected Output**:
```
🛑 Stopping services...
[+] Running 10/10
 ✔ Container sf-worker         Removed                                1.2s
 ✔ Container sf-api            Removed                                1.3s
 ✔ Container sf-grafana        Removed                                0.8s
 ✔ Container sf-prometheus     Removed                                0.7s
 ✔ Container sf-jaeger         Removed                                0.6s
 ✔ Container sf-minio          Removed                                1.1s
 ✔ Container sf-postgres       Removed                                1.0s
 ✔ Network sf-network          Removed                                0.2s
✅ Services stopped!
```

---

### `make logs`

**Purpose**: View logs from all services

**Command**:
```bash
make logs
```

**Expected Output**: Live streaming logs from all containers

**Follow specific service**:
```bash
docker compose logs -f api
```

---

### `make test`

**Purpose**: Run all tests (Python)

**Command**:
```bash
make test
```

**Expected Output**:
```
🧪 Running Python tests...
============================= test session starts ==============================
collected 91 items

tests/test_integration.py::TestHealthEndpoints::test_liveness PASSED
tests/test_integration.py::TestHealthEndpoints::test_readiness PASSED
tests/test_integration.py::TestHealthEndpoints::test_health PASSED
tests/test_integration.py::TestToolsEndpoints::test_list_tools PASSED
...
tests/test_sentinelforge.py::TestSchemas::test_login_request_valid PASSED
tests/test_sentinelforge.py::TestToolRegistry::test_registry_loads PASSED
tests/test_sentinelforge.py::TestToolExecutor::test_executor_init PASSED
tests/test_sentinelforge.py::TestModelAdapters::test_get_openai_adapter PASSED
tests/test_sentinelforge.py::TestEvidenceHashing::test_compute_hash_deterministic PASSED
tests/test_sentinelforge.py::TestGarakAdapter::test_parse_target_with_colon PASSED
tests/test_sentinelforge.py::TestPromptfooAdapter::test_parse_target_openai PASSED
tests/test_sentinelforge.py::TestToolExecutorDryRun::test_dry_run_returns_stub PASSED
tests/test_sentinelforge.py::TestWebhookSchemas::test_webhook_create_request_defaults PASSED
tests/test_sentinelforge.py::TestSDK::test_client_init PASSED
tests/test_sentinelforge.py::TestSDK::test_client_context_manager PASSED
============================== 91 passed in 3.55s ==============================
✅ Python tests complete!

```

> **Note**: Tests are split across two files: `tests/test_integration.py` (28 async integration tests covering all API endpoints) and `tests/test_sentinelforge.py` (63 unit tests across 20+ test classes). Run `make test-python` to run only Python tests.

---

### `make lint`

**Purpose**: Run code linters

**Command**:
```bash
make lint
```

**Expected Output**:
```
🔍 Linting Python code...
Ruff: No issues found
Black: All files are formatted correctly
✅ Python linting complete!
```

---

### `make security-scan`

**Purpose**: Run security vulnerability scans

**Command**:
```bash
make security-scan
```

**Expected Output**:
```
🔒 Running security scans...
Scanning for vulnerabilities with Grype...
✔ Vulnerability DB        [updated]
✔ Loaded image            sentinelforge/api:latest
✔ Parsed image            [45 packages]
✔ Cataloged packages      [45 packages]
✔ Scanned for vulnerabilities [0 vulnerability matches]

No vulnerabilities found

Generating SBOM with Syft...
✔ Cataloged packages      [45 packages]
SBOM saved to: sbom/api-sbom.json
✅ Security scan complete!
```

> **Note**: If `grype` or `syft` are not installed, each step is skipped with a message. Install them separately if needed.

---

## Docker Compose Commands

### `docker compose ps`

**Purpose**: List all containers with status

**Expected Output**:
```
NAME                IMAGE                       STATUS
sf-api              sentinelforge/api          Up 5 minutes (healthy)
sf-grafana          grafana/grafana            Up 5 minutes
sf-jaeger           jaegertracing/all-in-one   Up 5 minutes
sf-minio            minio/minio                Up 5 minutes (healthy)
sf-postgres         postgres:16-alpine         Up 5 minutes (healthy)
sf-prometheus       prom/prometheus            Up 5 minutes
sf-worker           sentinelforge/worker       Up 5 minutes
```

---

### `docker compose logs <service>`

**Purpose**: View logs for specific service

**Examples**:

```bash
# API logs
docker compose logs api

# Worker logs (follow mode)
docker compose logs -f worker

# Last 50 lines
docker compose logs --tail 50 api
```

**Expected Output** (API):
```
sf-api | {"time": "2026-02-09 14:46:00", "level": "INFO", "message": "🚀 SentinelForge API starting up..."}
sf-api | {"time": "2026-02-09 14:46:01", "level": "INFO", "message": "Database connection established"}
sf-api | INFO:     Started server process [1]
sf-api | INFO:     Waiting for application startup.
sf-api | INFO:     Application startup complete.
sf-api | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### `docker compose exec <service> <command>`

**Purpose**: Execute command inside running container

**Examples**:

```bash
# Access API shell
docker compose exec api bash

# Check database
docker compose exec postgres psql -U sentinelforge_user -d sentinelforge

# View environment variables
docker compose exec api printenv
```

---

### `docker compose restart <service>`

**Purpose**: Restart specific service

**Command**:
```bash
docker compose restart api
```

**Expected Output**:
```
[+] Restarting 1/1
 ✔ Container sf-api  Restarted                                       2.3s
```

---

## CLI Commands

All `sf` commands require authentication (except `sf auth login` and `sf version`).

### Authentication Commands

#### `sf auth login`

**Purpose**: Authenticate with SentinelForge API

**Command**:
```bash
sf auth login
```

**Interactive Prompts**:
```
Username: <your_username>
Password: ****
```

**Expected Output**:
```
✓ Login successful!
```

> **Credentials**: Use the username and password you configured in your `.env` file via `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD`. The password must be at least 12 characters with mixed case, numbers, and symbols. There are no hardcoded default credentials -- you must set them yourself.

---

#### `sf auth status`

**Purpose**: Check authentication status

**Command**:
```bash
sf auth status
```

**Expected Output**:
```
✓ Authenticated
User: <your_username>
Role: admin
```

---

#### `sf auth logout`

**Purpose**: Logout from current session

**Command**:
```bash
sf auth logout
```

**Expected Output**:
```
Successfully logged out
```

> **Note**: This command removes the locally stored JWT token from `~/.sentinelforge/config.json`. It does **not** call the API's `/auth/logout` endpoint and does not revoke the token server-side. The token will continue to be valid until it expires (30 minutes). If you need to revoke the token immediately, call the API's `POST /auth/logout` endpoint directly before running `sf auth logout`.

---

### Tools Commands

#### `sf tools list`

**Purpose**: List all available BlackICE tools

**Command**:
```bash
sf tools list
```

**Expected Output**:
```
Available Tools
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Category         ┃ Description                ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ garak      │ prompt_injection │ LLM vulnerability scanner  │
│ promptfoo  │ evaluation       │ LLM evaluation framework   │
│ pyrit      │ red_team         │ Python Risk Identification │
│ rebuff     │ detection        │ Injection detection        │
│ textattack │ adversarial_ml   │ Adversarial NLP attacks    │
│ art        │ adversarial_ml   │ Adversarial Robustness     │
│ deepeval   │ evaluation       │ LLM evaluation framework   │
│ trulens    │ observability    │ LLM observability          │
│ guardrails │ validation       │ Output validation          │
│ langkit    │ monitoring       │ Safety monitoring          │
└────────────┴──────────────────┴────────────────────────────┘
```

---

#### `sf tools info <tool_name>`

**Purpose**: Get detailed information about a specific tool

**Command**:
```bash
sf tools info garak
```

**Expected Output**:
```
Tool: garak
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category: prompt_injection
Version: 0.9
Description: LLM vulnerability scanner - comprehensive prompt injection testing

Capabilities:
  • Prompt injection detection
  • Jailbreak testing
  • Encoding attacks

MITRE ATLAS:
  • AML.T0051.000 (LLM Prompt Injection)

Virtual Environment: /opt/venvs/garak
CLI Command: garak
```

---

#### `sf tools run <tool_name> <target>`

**Purpose**: Execute a specific tool against a target model

**Command**:
```bash
sf tools run garak gpt-3.5-turbo
```

**Expected Output**:
```
Running garak against gpt-3.5-turbo...
⚠ Not yet implemented
```

---

### Attack Commands

#### `sf attack list`

**Purpose**: List all available attack scenarios

**Command**:
```bash
sf attack list
```

**Expected Output**:
```
Attack Scenarios
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID                ┃ Name                          ┃ Tools          ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ prompt_injection  │ Comprehensive Prompt Inject.. │ garak,promptf..│
│ jailbreak         │ Jailbreak Testing             │ garak, pyrit   │
│ multi-turn        │ Multi-Turn Adversarial        │ custom         │
└───────────────────┴───────────────────────────────┴────────────────┘
```

---

#### `sf attack run <scenario> --target <model>`

**Purpose**: Run an attack scenario against a model

**Command**:
```bash
sf attack run prompt_injection --target gpt-3.5-turbo
```

**Expected Output**:
```
Launching attack: prompt_injection → gpt-3.5-turbo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run ID: run_20260209_144800
Status: queued
Started: 2026-02-09 14:48:00 UTC

Track progress: sf attack runs run_20260209_144800
```

---

#### `sf attack runs [run_id ]`

**Purpose**: List all runs or get status of specific run

**Command (all runs)**:
```bash
sf attack runs
```

**Expected Output**:
```
Recent Attack Runs
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Run ID              ┃ Scenario         ┃ Target       ┃ Status   ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ run_20260209_144800 │ prompt_injection │ gpt-3.5-turbo│ running  │
│ run_20260209_143000 │ jailbreak        │ gpt-4        │ completed│
└─────────────────────┴──────────────────┴──────────────┴──────────┘
```

**Command (specific run)**:
```bash
sf attack runs run_20260209_144800
```

**Expected Output**:
```
Run: run_20260209_144800
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scenario: prompt_injection
Target: gpt-3.5-turbo
Status: running
Progress: 65%
Started: 2026-02-09 14:48:00
```

---

### New Capabilities Commands

#### `sf agent test <endpoint>`

**Purpose**: Test an AI agent for tool misuse

**Command**:
```bash
sf agent test https://my-agent-api.com/agent \
  --tools "web_search,calculator" \
  --forbidden "file_write,execute_code"
```

**Expected Output**:
```
Testing AI agent: https://my-agent-api.com/agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Allowed tools: web_search, calculator
Forbidden actions: file_write, execute_code

AI Agent Testing Framework
Tests: tool misuse, hallucination, unauthorized access

Agent testing module ready. Results will be displayed when the run completes.
```

---

#### `sf synthetic generate`

**Purpose**: Generate synthetic adversarial prompts

**Command**:
```bash
sf synthetic generate \
  --seed prompts/seeds.txt \
  --mutations encoding,translation,synonym \
  --count 100 \
  --output synthetic_dataset.json
```

**Expected Output**:
```
Generating 100 synthetic prompts...
Mutations: encoding,translation,synonym

Synthetic data module ready. Results will be displayed when generation completes.
```

---

#### `sf drift baseline <model>`

**Purpose**: Create safety/quality baseline for model

**Command**:
```bash
sf drift baseline gpt-4 --save baselines/gpt4-baseline.json
```

**Expected Output**:
```
Creating baseline for gpt-4...
Running 80 safety prompts across 8 categories...
Baseline saved: baselines/gpt4-baseline.json
```

---

#### `sf drift compare <model> --baseline <file>`

**Purpose**: Compare current model performance to baseline

**Command**:
```bash
sf drift compare gpt-4 --baseline baselines/gpt4-baseline.json
```

**Expected Output**:
```
Comparing gpt-4 to baseline...
Drift detected: 2 of 8 categories exceeded threshold
Details available via API: GET /drift/history/{baseline_id}
```

---

#### `sf supply-chain scan <model_source>`

**Purpose**: Scan model supply chain for vulnerabilities

**Command**:
```bash
sf supply-chain scan huggingface:gpt2
```

**Expected Output**:
```
Scanning: huggingface:gpt2...
Running checks: dependencies, model_card, license, data_provenance, signature
Risk level: low
Issues found: 1
```

---

### Report Commands

#### `sf report list`

**Purpose**: List all generated reports

**Command**:
```bash
sf report list
```

**Expected Output**:
```
Reports
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID           ┃ Run ID        ┃ Format ┃ Generated At         ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ rpt-abc12... │ run-def34...  │ html   │ 2026-02-10 14:00 UTC │
└──────────────┴───────────────┴────────┴──────────────────────┘
```

---

#### `sf report show <run_id>`

**Purpose**: Display report for specific run

**Command**:
```bash
sf report show run_20260209_143000
```

**Expected Output**:
```
Opening report for run: run_20260209_143000...
Format: html
View in browser: http://localhost:8000/reports/{id}/view
```

---

#### `sf report generate <run_id> --format <formats>`

**Purpose**: Generate report in specified formats

**Command**:
```bash
sf report generate run_20260209_143000 --format html,pdf,jsonl
```

**Expected Output**:
```
Generating report for run_20260209_143000...
Formats: html, pdf, jsonl
Generated 3 reports. Upload to S3: success
```

---

### Utility Commands

#### `sf version`

**Purpose**: Show SentinelForge version

**Command**:
```bash
sf version
```

**Expected Output**:
```
SentinelForge CLI v2.0.0
Enterprise AI Security Testing Platform
```

---

#### `sf agent test`

**Purpose**: Test an AI agent for tool misuse, hallucination, and unauthorized access

**Command**:
```bash
sf agent test http://agent.example.com/chat --tools "search,calculator" --forbidden "file_delete,system_exec"
```

**Expected Output**:
```
╭─ Agent Safety Test ──────────────────────────╮
│ Test ID: a1b2c3d4...                         │
│ Endpoint: http://agent.example.com/chat      │
│ Status: completed                            │
│ Risk Level: HIGH                             │
│ Findings: 5                                  │
│                                              │
│ Scenario Results:                            │
│   tool_misuse: completed (findings: 3)       │
│   hallucination: completed (findings: 1)     │
│   unauthorized_access: completed (findings: 1)│
╰──────────────────────────────────────────────╯
```

#### `sf agent tests`

**Purpose**: List previous agent tests

**Command**:
```bash
sf agent tests
```

#### `sf agent show`

**Purpose**: Get details of a specific agent test

**Command**:
```bash
sf agent show <test_id>
```

---

#### `sf synthetic generate`

**Purpose**: Generate synthetic adversarial prompts

**Command**:
```bash
sf synthetic generate --seed prompts.txt --mutations "encoding,synonym,leetspeak" --count 50 --output dataset.json
```

**Expected Output**:
```
Generating 50 synthetic prompts...
Mutations: encoding, synonym, leetspeak
╭─ Synthetic Dataset Generated ────────────────╮
│ Dataset ID: d1e2f3g4...                      │
│ Status: completed                            │
│ Generated: 50 prompts                        │
│ Mutations: encoding, synonym, leetspeak      │
│                                              │
│ Samples (first 5):                           │
│   [encoding_base64] RGVjb2RlIGFuZCBleGVj... │
│   [synonym_v1] Disregard previous inst...    │
│   [leetspeak] 1gnor3 pr3v10u5 1n57ruc7...   │
╰──────────────────────────────────────────────╯
```

#### `sf synthetic datasets`

**Purpose**: List generated synthetic datasets

**Command**:
```bash
sf synthetic datasets
```

#### `sf synthetic show`

**Purpose**: Get details of a specific synthetic dataset

**Command**:
```bash
sf synthetic show <dataset_id>
```

---

#### `sf backdoor scan`

**Purpose**: Run a backdoor detection scan on a model

**Command**:
```bash
sf backdoor scan huggingface:gpt2 --type behavioral
```

**Expected Output**:
```
Scanning: huggingface:gpt2 (type: behavioral)...
╭─ Backdoor Scan ──────────────────────────────╮
│ Scan ID: b1c2d3e4...                         │
│ Model: huggingface:gpt2                      │
│ Scan Type: behavioral                        │
│ Risk Level: LOW                              │
│ Indicators Found: 0                          │
╰──────────────────────────────────────────────╯
```

#### `sf backdoor scans`

**Purpose**: List previous backdoor scans

**Command**:
```bash
sf backdoor scans
```

#### `sf backdoor show`

**Purpose**: Get details of a specific backdoor scan

**Command**:
```bash
sf backdoor show <scan_id>
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `S3_ENDPOINT` | MinIO/S3 endpoint | `http://minio:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |
| `S3_BUCKET` | S3 bucket name | `sentinelforge-artifacts` |
| `JWT_SECRET_KEY` | JWT signing key (at least 32 characters) | `your-random-256-bit-secret` |
| `DEFAULT_ADMIN_USERNAME` | Admin username (must be set, no default) | `sf_admin` |
| `DEFAULT_ADMIN_PASSWORD` | Admin password (12+ chars, mixed case, numbers, symbols) | `MyStr0ng!Pass#99` |

### Model Provider Keys (at least one required)

| Variable | Provider |
|----------|----------|
| `OPENAI_API_KEY` | OpenAI (GPT-3.5, GPT-4) |
| `ANTHROPIC_API_KEY` | Anthropic (Claude 3) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | Azure endpoint URL |
| `AWS_ACCESS_KEY_ID` | AWS Bedrock |
| `AWS_SECRET_ACCESS_KEY` | AWS Bedrock |
| `HUGGINGFACE_API_TOKEN` | HuggingFace (supply chain scanning) |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |
| `WORKER_CONCURRENCY` | `5` | Number of concurrent worker jobs |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://jaeger:4318` | OpenTelemetry endpoint |
| `GRAFANA_PASSWORD` | `admin` | Grafana admin password |
| `CORS_ORIGINS` | `[]` (empty list) | CORS allowed origins (list of URLs). Wildcard `*` is **blocked** in production -- you must set explicit origins. |
| `DEBUG` | `false` | Enable debug mode (relaxes some security checks -- never use in production) |
| `METRICS_ENABLED` | `true` | Enable Prometheus metrics collection |

---

## API Endpoints

Base URL: `http://localhost:8000`

### Health Endpoints

#### `GET /health`

**Purpose**: Health check

**cURL**:
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "database": "healthy"
  },
  "timestamp": "2026-02-12T14:46:00Z"
}
```

> **Response Schema**: `status` (string: "healthy" or "degraded"), `version` (string), `services` (object mapping service names to "healthy"/"unhealthy"), `timestamp` (ISO 8601 datetime). There are no `cpu_percent` or `memory_percent` fields.

---

#### `GET /ready`

**Purpose**: Kubernetes readiness probe

**cURL**:
```bash
curl http://localhost:8000/ready
```

**Response**:
```json
{
  "ready": true
}
```

> **Note**: Returns `{"ready": false}` if the database is unreachable.

---

#### `GET /live`

**Purpose**: Kubernetes liveness probe

**cURL**:
```bash
curl http://localhost:8000/live
```

**Response**:
```json
{
  "alive": true
}
```

---

### Authentication Endpoints

#### `POST /auth/login`

**Purpose**: Authenticate and get JWT token

**cURL**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

> **Important**: This endpoint accepts **JSON** (`application/json`), **not** form-urlencoded data. Send a JSON body with `username` and `password` fields.

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

> **Rate Limiting**: This endpoint is rate-limited to 5 attempts per 60 seconds per IP address. Exceeding this returns HTTP 429.

---

#### `GET /auth/status`

**Purpose**: Get current authenticated user info

**cURL**:
```bash
curl http://localhost:8000/auth/status \
  -H "Authorization: Bearer <your_token>"
```

**Response**:
```json
{
  "id": "uuid-string",
  "username": "admin",
  "role": "admin",
  "is_active": true
}
```

---

#### `POST /auth/logout`

**Purpose**: Revoke the current JWT token server-side

**cURL**:
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <your_token>"
```

**Response**:
```json
{
  "message": "Successfully logged out, token revoked"
}
```

> **Note**: This endpoint revokes the token on the server so it can no longer be used, even before its natural expiration. The CLI command `sf auth logout` does **not** call this endpoint -- it only removes the local token file.

---

### Attack Endpoints

#### `GET /attacks/scenarios`

**Purpose**: List attack scenarios

**cURL**:
```bash
curl http://localhost:8000/attacks/scenarios \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
[
  {
    "id": "prompt_injection",
    "name": "Comprehensive Prompt Injection",
    "description": "Multi-tool prompt injection assessment",
    "category": "injection",
    "tools": ["garak", "promptfoo"],
    "mitre_atlas": ["AML.T0051.000"]
  }
]
```

---

#### `POST /attacks/run`

**Purpose**: Start attack run

**cURL**:
```bash
curl -X POST http://localhost:8000/attacks/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "prompt_injection",
    "target_model": "gpt-3.5-turbo",
    "config": {}
  }'
```

**Response**:
```json
{
  "id": "run_20260209_144800",
  "scenario_id": "prompt_injection",
  "target_model": "gpt-3.5-turbo",
  "status": "queued",
  "progress": 0.0,
  "created_at": "2026-02-09T14:48:00Z"
}
```

---

#### `GET /attacks/runs/{id}/verify`

**Purpose**: Verify evidence chain integrity for an attack run

**cURL**:
```bash
curl http://localhost:8000/attacks/runs/{run_id}/verify \
  -H "Authorization: Bearer <token>"
```

**Response**:
```json
{
  "valid": true,
  "total": 5,
  "verified": 5,
  "broken_at": null
}
```

---

### Report Endpoints

#### `GET /reports/{id}/download`

**Purpose**: Download a report from S3 (falls back to regeneration if S3 is unavailable)

**cURL**:
```bash
curl -O http://localhost:8000/reports/{report_id}/download \
  -H "Authorization: Bearer <token>"
```

**Response**: Binary file download (HTML, PDF, or JSONL depending on report format)

---

### Drift Detection Endpoints

#### `POST /drift/baseline`

**Purpose**: Create a safety baseline for a model

#### `POST /drift/compare`

**Purpose**: Compare current model behavior against a baseline

#### `GET /drift/baselines`

**Purpose**: List all saved baselines

#### `GET /drift/history/{baseline_id}`

**Purpose**: View comparison history for a baseline

---

### Supply Chain Endpoints

#### `POST /supply-chain/scan`

**Purpose**: Scan a model's supply chain (dependencies, license, model card, signatures)

#### `GET /supply-chain/scans`

**Purpose**: List all supply chain scans

#### `GET /supply-chain/scans/{id}`

**Purpose**: Get details of a specific scan

---

### Backdoor Detection Endpoints

#### `POST /backdoor/scan`

**Purpose**: Scan a model for backdoors (behavioral, pickle, weight analysis)

#### `GET /backdoor/scans`

**Purpose**: List all backdoor scans

#### `GET /backdoor/scans/{id}`

**Purpose**: Get details of a specific scan

---

### Agent Testing Endpoints

#### `POST /agent/test`

**Purpose**: Launch an agent safety test (tool misuse, hallucination, unauthorized access)

#### `GET /agent/tests`

**Purpose**: List all agent tests

#### `GET /agent/tests/{id}`

**Purpose**: Get details of a specific agent test

---

### Synthetic Data Endpoints

#### `POST /synthetic/generate`

**Purpose**: Generate a synthetic adversarial prompt dataset (encoding, translation, synonym, leetspeak, whitespace, fragmentation mutations)

#### `GET /synthetic/datasets`

**Purpose**: List generated synthetic datasets

#### `GET /synthetic/datasets/{id}`

**Purpose**: Get details of a specific synthetic dataset with sample prompts

---

### Webhook Endpoints

#### `POST /webhooks`

**Purpose**: Create a webhook endpoint for event notifications

**cURL**:
```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://my-server.com/hook",
    "events": ["attack.completed", "scan.completed"],
    "description": "My notification webhook"
  }'
```

**Response**: Returns webhook details including a `secret` for HMAC signature verification (shown only on creation).

#### `GET /webhooks`

**Purpose**: List all webhooks for the current user

#### `GET /webhooks/{id}`

**Purpose**: Get details of a specific webhook

#### `PUT /webhooks/{id}`

**Purpose**: Update a webhook (URL, events, active status)

#### `DELETE /webhooks/{id}`

**Purpose**: Delete a webhook

#### `POST /webhooks/{id}/test`

**Purpose**: Send a test ping event to verify webhook delivery

**Event Types**: `attack.completed`, `attack.failed`, `scan.completed`, `report.generated`, `agent.test.completed`

**Webhook Headers**: Each delivery includes `X-SentinelForge-Event`, `X-SentinelForge-Signature` (HMAC-SHA256), and `X-SentinelForge-Delivery` (unique ID).

---

### Webhook CLI Commands

#### `sf webhook create <url>`

**Purpose**: Register a new webhook endpoint

**Command**:
```bash
sf webhook create https://my-server.com/hook --events attack.completed,scan.completed --description "My hook"
```

#### `sf webhook list`

**Purpose**: List all registered webhooks

#### `sf webhook delete <id>`

**Purpose**: Delete a webhook by ID

#### `sf webhook test <id>`

**Purpose**: Send a test ping to a webhook

---

For complete API documentation, visit: http://localhost:8000/docs
