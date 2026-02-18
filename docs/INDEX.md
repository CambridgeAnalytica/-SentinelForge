# SentinelForge Documentation Index

Welcome to the SentinelForge documentation! This index will help you find the right documentation for your needs.

## Getting Started

- **[README.md](../README.md)** - Project overview, features, and architecture
- **[Getting Started Guide](GETTING_STARTED.md)** - Quick setup for local development
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions (local, AWS, on-premises)
- **[CI/CD Integration](../ci/README.md)** - GitHub Actions + GitLab CI setup guide

## Reference Guides

- **[COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)** - All commands with expected outputs
  - Makefile commands
  - Docker Compose commands
  - CLI commands (`sf`)
  - API endpoints
  - Environment variables

- **[TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)** - All integrated AI security tools
  - Tool descriptions and capabilities
  - Usage examples
  - Configuration options
  - Expected outputs

## Version History

- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and features

## Configuration & Deployment

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (create from `.env.example`) |
| `docker-compose.yml` | Multi-service orchestration |
| `Makefile` | Development commands |
| `tools/registry.yaml` | Tool registry configuration (14 tools, 14 adapters) |
| `scenarios/*.yaml` | Attack scenario definitions |
| `playbooks/*.yaml` | Incident response playbooks |
| `ci/github/action.yml` | GitHub Actions composite action |
| `ci/gitlab/.gitlab-ci-template.yml` | GitLab CI reusable template |

### Docker Images

| Image | Dockerfile | Purpose |
|-------|-----------|---------|
| `sentinelforge-api` | `infra/docker/Dockerfile.api` | FastAPI service |
| `sentinelforge-worker` | `infra/docker/Dockerfile.worker` | Python async worker (asyncio + asyncpg) |
| `sentinelforge-tools` | `infra/docker/Dockerfile.tools` | BlackICE tools (14 isolated venvs) |
| `sentinelforge-dashboard` | `infra/docker/Dockerfile.dashboard` | Next.js web dashboard |

## Quick Reference

### First-Time Setup (Local)

Before you begin, you **must** configure your `.env` file. The platform will not start without these values.

**Bash (Linux / macOS / Git Bash on Windows):**

```bash
cd sentinelforge
cp .env.example .env

# REQUIRED: Edit .env and set these three values:
#   JWT_SECRET_KEY         - Generate: python -c "import secrets; print(secrets.token_hex(32))"
#   DEFAULT_ADMIN_USERNAME - Choose your admin username
#   DEFAULT_ADMIN_PASSWORD - 12+ chars, must include uppercase, lowercase, numbers, symbols

# Also add any model API keys you plan to use (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

docker compose up -d
cd cli && pip install -e .
sf auth login
sf attack list
```

**PowerShell (Windows):**

```powershell
cd sentinelforge
Copy-Item .env.example .env

# REQUIRED: Open .env in your editor and set:
#   JWT_SECRET_KEY         - Generate: python -c "import secrets; print(secrets.token_hex(32))"
#   DEFAULT_ADMIN_USERNAME - Choose your admin username
#   DEFAULT_ADMIN_PASSWORD - 12+ chars, must include uppercase, lowercase, numbers, symbols

# Also add any model API keys you plan to use (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)

docker compose up -d
cd cli; pip install -e .
sf auth login
sf attack list
```

> **Important**: There are no default admin credentials. You must set `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` in `.env` before starting the services. The password is validated for complexity (12+ characters with mixed case, numbers, and symbols).

### Common Tasks

| Task | Command |
|------|---------|
| Start all services | `make up` or `docker compose up -d` |
| Stop all services | `make down` |
| View logs | `make logs` or `docker compose logs -f` |
| Run tests | `make test` |
| List tools | `sf tools list` |
| Run attack | `sf attack run <scenario> --target <model>` |
| Generate report | `sf report generate <run_id>` |
| Create schedule | `sf schedule create --scenario <id> --cron "..."` |
| Create API key | `sf api-key create --name <name>` |
| Compliance summary | `sf compliance summary --run-id <id>` |

### Service URLs (Local)

| Service | URL | Credentials |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | N/A (browse interactively) |
| API Health | http://localhost:8000/health | N/A |
| Dashboard UI | http://localhost:3001 | SentinelForge admin credentials |
| Prometheus Metrics | http://localhost:8000/metrics | N/A |
| Grafana | http://localhost:3000 | admin / admin (default Grafana password) |
| Jaeger | http://localhost:16686 | N/A |
| Prometheus | http://localhost:9090 | N/A |
| MinIO | http://localhost:9001 | minioadmin / minioadmin (override via S3_ACCESS_KEY / S3_SECRET_KEY in .env) |

> **Note**: The SentinelForge API itself requires JWT authentication. Use `sf auth login` with the admin credentials you configured in `.env`.

## Documentation by Role

### For DevOps/SRE

1. [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md#docker-compose-commands) - Container management
3. `docker-compose.yml` - Service definitions
4. `infra/observability/` - Monitoring configuration (Prometheus, Grafana)
5. `ci/` - CI/CD integration templates (GitHub Actions, GitLab CI)

### For Security Engineers

1. [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - All 14 security tools with adapters
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md#cli-commands) - CLI usage
3. `scenarios/` - Attack scenarios (YAML definitions)
4. `playbooks/` - Incident response playbooks (YAML definitions)
5. `services/api/data/compliance_frameworks.py` - Compliance framework mappings

### For Developers

1. [Getting Started](GETTING_STARTED.md) - Local setup
2. [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md#api-endpoints) - API documentation
3. `services/api/` - API source code (FastAPI)
4. `services/worker/` - Worker source code (Python async)
5. `sdk/python/` - Python SDK for probe authoring
6. `adapters/models/` - Model adapters (OpenAI, Anthropic, Azure, Bedrock)

## Support & Troubleshooting

### Common Issues

See [DEPLOYMENT_GUIDE.md#troubleshooting](DEPLOYMENT_GUIDE.md#troubleshooting) for solutions to:
- Services won't start (check `.env` required values)
- Database connection errors
- API key errors
- Worker not processing jobs

### Getting Help

1. Check logs: `docker compose logs <service>` (e.g., `docker compose logs api`)
2. Verify configuration: make sure `.env` has all required values set
3. Review documentation in this directory
4. Check service health: `curl http://localhost:8000/health` (bash) or `Invoke-RestMethod http://localhost:8000/health` (PowerShell)

## Architecture

```
+------------------------------------------+
|  CLI (sf) / Dashboard UI (Port 3001)     |
+-------------------+----------------------+
                    |
                    v
+------------------------------------------+
|  FastAPI (Port 8000)                     |
|  +- Health  +- Auth    +- Attacks        |
|  +- Probes  +- Tools   +- Reports       |
|  +- Drift   +- Backdoor +- Supply Chain |
|  +- Agent   +- Synthetic +- Webhooks   |
|  +- Schedules +- API Keys +- Compliance|
|  +- Notifications +- Audit  +- SSE     |
+-------------------+----------------------+
                    |
                    v
+------------------------------------------+
|  Postgres (5432) + MinIO (9000)          |
+-------------------+----------------------+
                    |
                    v
+------------------------------------------+
|  Python async Worker Pool (2 replicas)   |
+-------------------+----------------------+
                    |
                    v
+------------------------------------------+
|  14 BlackICE Tools (Isolated Venvs)      |
|  + Model Adapters (OpenAI, Anthropic...) |
+------------------------------------------+
```

## Contributing

To extend SentinelForge:

1. **Add new tool**: See [TOOLS_REFERENCE.md#adding-new-tools](TOOLS_REFERENCE.md#adding-new-tools)
2. **Add new scenario**: Create YAML in `scenarios/`
3. **Add new playbook**: Create YAML in `playbooks/`
4. **Add model adapter**: Implement `BaseModelAdapter` in `adapters/models/`

## Version

Current version: **2.2.0**

See [CHANGELOG.md](../CHANGELOG.md) for release notes.
