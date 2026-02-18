# SentinelForge - Getting Started Guide

This guide walks you through setting up SentinelForge on your local machine,
from zero to running your first AI security test. Every step includes an
explanation of **what** the command does and **why** you need it.

> **SentinelForge v2.1** — includes compliance mapping, 14 tool adapters,
> scheduled scans, API key auth, notifications, CI/CD integration, and
> a full Next.js Dashboard UI (port 3001).

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Software | Minimum Version | Why You Need It |
|----------|----------------|-----------------|
| **Docker** | 20.10+ | Runs all SentinelForge services in containers |
| **Docker Compose** | 2.0+ (included with Docker Desktop) | Orchestrates the multi-container stack |
| **Python** | 3.11+ | Required to install and run the `sf` CLI |
| **Git** | 2.30+ | To clone the repository |

You will also need at least **one** LLM API key (OpenAI, Anthropic, Azure OpenAI,
or AWS Bedrock) to run attack scenarios against live models.

> **Note**: There is no Go dependency. The worker service is Python-based
> (async with asyncpg).

---

## Quick Start

### Step 1: Clone and Navigate to the Project

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/CambridgeAnalytica/-SentinelForge.git SentinelForge

# Enter the project directory
cd SentinelForge
```

This puts you in the root of the SentinelForge project, where all commands
below should be run.

---

### Step 2: Create Your Environment File

The `.env` file holds all configuration -- database passwords, API keys, and
security settings. SentinelForge ships a template you must copy and customize.

**Linux / macOS:**
```bash
cp .env.example .env
```

**Windows (Command Prompt):**
```cmd
copy .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

---

### Step 3: Configure Required Environment Variables

Open `.env` in your editor of choice:

```bash
# Linux / macOS
nano .env

# Windows
notepad .env
```

**There are THREE required variables that the API will refuse to start without.**
If any of these are missing, empty, or too weak, the API calls `sys.exit(1)`
and shuts down immediately (unless `DEBUG=true`, which only logs warnings).

#### 3a. JWT_SECRET_KEY (required, 32+ characters)

This key signs authentication tokens. Generate a cryptographically random one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output into your `.env`:

```env
JWT_SECRET_KEY=<paste-your-64-hex-character-string-here>
```

#### 3b. DEFAULT_ADMIN_USERNAME (required)

Choose a username for the initial admin account:

```env
DEFAULT_ADMIN_USERNAME=sf_admin
```

#### 3c. DEFAULT_ADMIN_PASSWORD (required, 12+ characters)

Must be at least 12 characters with mixed case, numbers, and symbols.
Common weak passwords like `admin`, `password`, or `changeme` are explicitly
rejected.

```env
DEFAULT_ADMIN_PASSWORD=MyStr0ng!Pass#2026
```

#### 3d. CORS_ORIGINS (recommended for local development)

For the API to accept browser requests locally, set:

```env
CORS_ORIGINS=["http://localhost:8000","http://localhost:3001"]
```

Alternatively, set `DEBUG=true` during local development to bypass CORS
enforcement (not suitable for production):

```env
DEBUG=true
```

#### 3e. API Keys (at least one)

Add at least one model provider key to run attack scenarios:

```env
OPENAI_API_KEY=sk-proj-...
# and/or
ANTHROPIC_API_KEY=sk-ant-...
```

Leave the rest of the `.env` defaults as-is for local development. The database
and MinIO (object storage) settings work out of the box with Docker Compose.

---

### Step 4: Start All Services

This builds the Docker images (first time only) and starts every service in the
background:

```bash
docker compose up -d
```

Verify everything is running:

```bash
docker compose ps
```

You should see containers for `sf-api`, `sf-dashboard`, `sf-postgres`, `sf-minio`, `sf-jaeger`,
`sf-prometheus`, `sf-grafana`, and two `sf-worker` replicas, all with status
"Up" or "Up (healthy)".

#### If `docker compose up -d` Fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| "JWT_SECRET_KEY must be set" or similar error | Required `.env` variables missing | Complete Step 3 above -- all three required variables must be set |
| "Cannot connect to the Docker daemon" | Docker Desktop is not running | Start Docker Desktop (or the Docker service on Linux) |
| Port conflict (e.g., "port 5432 already in use") | Another service using that port | Stop the conflicting service, or change the port mapping in `docker-compose.yml` |
| Build fails / image pull fails | No internet or Docker Hub rate limit | Check network; try `docker login` or wait and retry |

To see detailed error messages:

```bash
docker compose logs api
docker compose logs worker
```

---

### Step 5: Install the CLI

The `sf` command-line tool lets you run attacks, view reports, and manage
SentinelForge from your terminal. Install it in editable mode from the `cli/`
subdirectory:

```bash
cd cli
pip install -e .
```

**Important**: Return to the project root afterward so subsequent commands work
correctly:

```bash
cd ..
```

Verify the CLI installed successfully:

```bash
sf version
```

Expected output:
```
SentinelForge CLI v2.1.0
Enterprise AI Security Testing Platform
```

---

### Step 6: Log In

Authenticate with the credentials you set in `.env` (Step 3):

```bash
sf auth login
```

Enter the `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` values you
configured. For example, if you set `sf_admin` / `MyStr0ng!Pass#2026`:

```
Username: sf_admin
Password: MyStr0ng!Pass#2026
```

Expected output:
```
Login successful!
```

---

### Step 7: Run Your First Attack

```bash
# List available attack scenarios
sf attack list

# Launch a prompt injection test against a model
sf attack run prompt_injection --target gpt-3.5-turbo

# Check the status of all attack runs
sf attack runs

# View the detailed report for a specific run
sf report show <run-id>
```

> **Note**: The `sf attack runs` command shows all runs and their current status
> (queued, running, completed, failed).

---

## What You'll Have Running

After completing the steps above, these services are available on your machine:

| Service | URL | Purpose |
|---------|-----|---------|
| **SentinelForge API** | http://localhost:8000 | Main REST API |
| **API Documentation** (Swagger) | http://localhost:8000/docs | Interactive API explorer |
| **Health Check** | http://localhost:8000/health | Service health endpoint |
| **Dashboard UI** | http://localhost:3001 | Web-based security dashboard |
| **Grafana** | http://localhost:3000 | Metrics dashboards (default login: admin / admin) |
| **Jaeger UI** | http://localhost:16686 | Distributed tracing |
| **Prometheus** | http://localhost:9090 | Raw metrics |
| **MinIO Console** | http://localhost:9001 | Object storage browser (default: minioadmin / minioadmin) |
| **PostgreSQL** | localhost:5432 (localhost only) | Database (not exposed externally) |

To verify the API is healthy:

**Linux / macOS (curl):**
```bash
curl http://localhost:8000/health
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "services": {
    "database": "healthy"
  },
  "timestamp": "2026-02-16T12:00:00Z"
}
```

---

## Architecture Overview

```
API (Port 8000)       - FastAPI orchestration layer
Dashboard (Port 3001) - Next.js web dashboard
Worker (Background)   - Python async job executor (polls for queued attack runs)
Postgres (Port 5432)  - Persistent data storage (attack runs, users, results)
MinIO (Port 9000)     - S3-compatible artifact/evidence storage
Jaeger (Port 16686)   - Distributed tracing (OpenTelemetry)
Prometheus (Port 9090) - Metrics collection
Grafana (Port 3000)   - Metrics visualization and alerting
```

---

## What's Next?

- **Explore Tools**: `sf tools list` to see all integrated security tools
- **Open the Dashboard**: Visit http://localhost:3001 for the web UI
- **Test an AI Agent**: `sf agent test <endpoint>`
- **Generate Synthetic Attack Data**: `sf synthetic generate --seed prompts.txt`
- **Monitor Model Drift**: `sf drift baseline --model gpt-4`

---

## Troubleshooting

### Services won't start
```bash
# Check that Docker is running
docker --version
docker compose version

# View service logs for error details
docker compose logs api
docker compose logs worker

# Nuclear option: tear down everything (deletes data) and rebuild
docker compose down -v
docker compose up -d
```

### API exits immediately with "SECURITY CONFIG ERROR"
The API validates `JWT_SECRET_KEY`, `DEFAULT_ADMIN_USERNAME`, and
`DEFAULT_ADMIN_PASSWORD` at startup. If any are missing or weak, it exits with
code 1. Review Step 3 and ensure all three are properly set in `.env`.

### API key errors
- Verify your `.env` file has at least one valid model provider API key
- Restart services after editing `.env`: `docker compose restart`

### CLI not found after install
```bash
# Return to project root, reinstall
cd cli
pip uninstall sentinelforge-cli -y
pip install -e .
cd ..
```

---

## Further Reading

1. [Deployment Guide](DEPLOYMENT_GUIDE.md) -- Production deployment to AWS or on-premises
2. [CLI Command Reference](COMMAND_REFERENCE.md) -- Complete list of `sf` commands
3. [Tools Reference](TOOLS_REFERENCE.md) -- Documentation for all integrated security tools
4. [CI/CD Integration](../ci/README.md) -- GitHub Actions + GitLab CI setup

---

## Step 8: Create an API Key (for CI/CD or Automation)

API keys let external tools and CI/CD pipelines authenticate without using
interactive login. You can create one via the CLI or the API.

```bash
# Create an API key for your CI pipeline
sf api-key create --name ci-pipeline --scopes read,write
```

Output:
```
API Key created successfully!
Key:  sf_key_a1b2c3d4e5f6...  (save this — it will not be shown again)
Name: ci-pipeline
Scopes: read, write
```

Store this key securely:
- **GitHub**: Repository → Settings → Secrets → `SENTINELFORGE_API_KEY`
- **GitLab**: Project → Settings → CI/CD → Variables → `SENTINELFORGE_API_KEY` (masked)

See [CI/CD Integration](../ci/README.md) for full pipeline setup with GitHub Actions
and GitLab CI.

---

## Step 9: Set Up Scheduled Scans (Optional)

Scheduled scans let you run security tests automatically on a cron schedule.

```bash
# Run a prompt injection scan every Monday at 6 AM
sf schedule create --scenario prompt_injection --cron "0 6 * * 1" --target gpt-4

# View all schedules
sf schedule list

# Manually trigger a schedule
sf schedule trigger <schedule_id>
```

---

## Step 10: Check Compliance Status (Optional)

SentinelForge auto-tags all findings with compliance frameworks.

```bash
# List supported frameworks
sf compliance frameworks

# Get compliance summary for a completed scan
sf compliance summary --run-id <run_id>

# Download an auditor-friendly PDF report
sf compliance report --run-id <run_id> --format pdf
```

Supported frameworks:
- **OWASP ML Top 10** — Machine learning vulnerability taxonomy
- **NIST AI RMF** — AI Risk Management Framework
- **EU AI Act** — European Union AI regulation requirements

---

## Step 11: Set Up Notifications (Optional)

Receive scan results via Slack, email, or Microsoft Teams.

```bash
# Via the API (requires JWT or API key auth)
curl -X POST http://localhost:8000/notifications/channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-slack-channel",
    "type": "slack",
    "config": {"webhook_url": "https://hooks.slack.com/services/..."}
  }'
```

For email notifications, set these in `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
```
