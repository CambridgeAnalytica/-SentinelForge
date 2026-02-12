# SentinelForge Deployment Guide

**Complete Step-by-Step Instructions for Production Deployment**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment (AWS)](#production-deployment-aws)
4. [Production Deployment (On-Premises)](#production-deployment-on-premises)
5. [Configuration](#configuration)
6. [Health Checks & Verification](#health-checks--verification)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Python | 3.11+ | CLI and local development |
| Git | 2.30+ | Version control |

> **Note**: No Go toolchain is needed. The worker service is Python-based
> (async with asyncpg).

### Required API Keys

You will need at least **one** of the following:

- **OpenAI API Key** - For testing GPT models
- **Anthropic API Key** - For testing Claude models
- **Azure OpenAI** - For Azure-hosted models
- **AWS Bedrock** - For AWS-hosted models

### System Requirements

**Minimum** (Development):
- 8 GB RAM
- 4 CPU cores
- 50 GB disk space

**Recommended** (Production):
- 16 GB RAM
- 8 CPU cores
- 200 GB SSD
- Network connectivity to model providers

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/CambridgeAnalytica/-SentinelForge.git SentinelForge
cd SentinelForge
```

**Expected Output**: You should be in the `SentinelForge` directory.

### Step 2: Create Environment Configuration

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

**Expected Output**: A new `.env` file is created.

### Step 3: Configure Environment Variables

Edit `.env` file with your settings:

```bash
# Linux / macOS
nano .env

# Windows
notepad .env
```

#### Required Variables (API will not start without these)

The API validates these three variables at startup. If any are missing, empty,
or too weak, it calls `sys.exit(1)` and refuses to start (unless `DEBUG=true`,
which downgrades the errors to warnings).

```env
# -----------------------------------------------------------------
# 1. JWT_SECRET_KEY (REQUIRED - 32+ characters)
#    Signs authentication tokens. Generate with:
#    python -c "import secrets; print(secrets.token_hex(32))"
# -----------------------------------------------------------------
JWT_SECRET_KEY=<paste-your-generated-64-hex-char-string>

# -----------------------------------------------------------------
# 2. DEFAULT_ADMIN_USERNAME (REQUIRED)
#    Username for the initial admin account.
# -----------------------------------------------------------------
DEFAULT_ADMIN_USERNAME=sf_admin

# -----------------------------------------------------------------
# 3. DEFAULT_ADMIN_PASSWORD (REQUIRED - 12+ characters)
#    Must be 12+ chars, mixed case, numbers, and symbols.
#    Common weak passwords (admin, password, changeme) are rejected.
# -----------------------------------------------------------------
DEFAULT_ADMIN_PASSWORD=MyStr0ng!Pass#2026
```

#### Database Configuration

For local development, the defaults work with Docker Compose. No changes needed.

```env
POSTGRES_USER=sentinelforge_user
POSTGRES_PASSWORD=sentinelforge_password
POSTGRES_DB=sentinelforge
```

> **Important**: The `DATABASE_URL` in `.env.example` uses the synchronous
> driver (`postgresql://`). This is correct for the worker, which uses asyncpg
> directly. However, the API expects the async driver prefix
> (`postgresql+asyncpg://`). The `docker-compose.yml` sets the correct values
> for each service automatically, so you generally do not need to set
> `DATABASE_URL` manually for local development. If you do set it for
> production, use:
> - API: `postgresql+asyncpg://user:pass@host:5432/dbname`
> - Worker: `postgresql://user:pass@host:5432/dbname` (asyncpg connects directly)

#### CORS Configuration

```env
# For local development, allow the API's own origin:
CORS_ORIGINS=["http://localhost:8000"]

# Or use DEBUG=true to bypass CORS enforcement entirely (dev only):
DEBUG=true
```

#### Model Provider API Keys

```env
# At least ONE model provider API key is needed to run attacks
OPENAI_API_KEY=sk-proj-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
AZURE_OPENAI_API_KEY=...
```

#### Optional: Other providers

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

> **SECURITY**: Never commit `.env` to version control!

### Step 4: Start Services

```bash
# Build and start all containers
docker compose up -d
```

**Expected Output**:
```
[+] Running 10/10
 - Network sf-network          Created
 - Volume "sf_postgres-data"   Created
 - Volume "sf_minio-data"      Created
 - Container sf-postgres       Started
 - Container sf-minio          Started
 - Container sf-minio-init     Started
 - Container sf-jaeger         Started
 - Container sf-prometheus     Started
 - Container sf-grafana        Started
 - Container sf-api            Started
 - Container sf-worker         Started
```

**Verification -- Check all services are running**:
```bash
docker compose ps
```

**Expected Output**:
```
NAME                IMAGE                         STATUS
sf-api              sentinelforge-api            Up (healthy)
sf-grafana          grafana/grafana              Up
sf-jaeger           jaegertracing/all-in-one     Up
sf-minio            minio/minio                  Up (healthy)
sf-postgres         postgres:16-alpine           Up (healthy)
sf-prometheus       prom/prometheus              Up
sf-worker           sentinelforge-worker         Up
```

### Step 5: Install CLI

```bash
cd cli
pip install -e .
cd ..
```

**Expected Output**:
```
Successfully installed sentinelforge-cli-1.3.0
```

**Verify CLI**:
```bash
sf version
```

**Expected Output**:
```
SentinelForge CLI v1.3.0
Enterprise AI Security Testing Platform
```

### Step 6: Access Web Interfaces

Open these URLs in your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| API Documentation | http://localhost:8000/docs | N/A |
| Grafana | http://localhost:3000 | admin / admin |
| Jaeger UI | http://localhost:16686 | N/A |
| Prometheus | http://localhost:9090 | N/A |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

### Step 7: Verify API Health

**Linux / macOS:**
```bash
curl http://localhost:8000/health
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "services": {
    "database": "healthy"
  },
  "timestamp": "2026-02-10T12:00:00Z"
}
```

### Step 8: First Login

```bash
sf auth login
```

Enter the `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` values you
configured in Step 3:

```
Username: sf_admin
Password: MyStr0ng!Pass#2026
```

**Expected Output**:
```
Login successful!
```

### Step 9: Run First Test

```bash
# List available scenarios
sf attack list
```

**Expected Output**:
```
+--------------------+-------------------------------+-----------------+
| ID                 | Name                          | Tools           |
+--------------------+-------------------------------+-----------------+
| prompt_injection   | Comprehensive Prompt Inject.. | garak, promptf..|
| jailbreak          | Jailbreak Testing             | garak, pyrit    |
| multi-turn         | Multi-Turn Adversarial        | custom          |
+--------------------+-------------------------------+-----------------+
```

```bash
# Run a test (NOTE: This requires valid API keys)
sf attack run prompt_injection --target gpt-3.5-turbo

# Check status of all runs
sf attack runs
```

**Expected Output**:
```
Launching attack: prompt_injection -> gpt-3.5-turbo
Run ID: run_20260209_144800
Status: queued
```

---

## Production Deployment (AWS)

### Architecture Overview

```
Internet -> ALB -> ECS/Fargate
              +-- API Service (2+ replicas)
              +-- Worker Service (3+ replicas)
              +-- RDS PostgreSQL
                 +-- S3 (artifacts)
                    +-- CloudWatch (logs/metrics)
```

### Step 1: Prerequisites

1. **AWS Account** with permissions for:
   - ECS, ECR, RDS, S3, ALB, VPC, IAM
2. **AWS CLI** configured
3. **Terraform** (optional, for IaC)

### Step 2: Create ECR Repositories

```bash
# Create repositories for images
aws ecr create-repository --repository-name sentinelforge/api
aws ecr create-repository --repository-name sentinelforge/worker
aws ecr create-repository --repository-name sentinelforge/tools
```

**Expected Output**:
```json
{
  "repository": {
    "repositoryArn": "arn:aws:ecr:us-east-1:...",
    "repositoryUri": "123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/api"
  }
}
```

### Step 3: Build and Push Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Build images using the Makefile
make build

# Tag for ECR
docker tag sentinelforge/api:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/api:latest
docker tag sentinelforge/worker:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/worker:latest

# Push to ECR
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/api:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/worker:latest
```

> **Note**: The `make build` target builds all three Docker images (api, worker,
> tools) using the Dockerfiles in `infra/docker/`.

### Step 4: Create RDS PostgreSQL

```bash
aws rds create-db-instance \
  --db-instance-identifier sentinelforge-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16.1 \
  --master-username sentinelforge_admin \
  --master-user-password 'YOUR_SECURE_PASSWORD_HERE' \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name my-db-subnet-group \
  --backup-retention-period 7 \
  --multi-az
```

**Expected Output**: Database instance creation initiated (takes 10-15 minutes).

### Step 5: Create S3 Bucket

```bash
aws s3api create-bucket \
  --bucket sentinelforge-artifacts-prod \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket sentinelforge-artifacts-prod \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket sentinelforge-artifacts-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Step 6: Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name sentinelforge-prod
```

### Step 7: Create Task Definitions

Create `ecs-task-api.json`:
```json
{
  "family": "sentinelforge-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [{
    "name": "api",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/sentinelforge/api:latest",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql+asyncpg://user:pass@rds-endpoint:5432/sentinelforge"},
      {"name": "S3_BUCKET", "value": "sentinelforge-artifacts-prod"},
      {"name": "CORS_ORIGINS", "value": "[\"https://sentinelforge.yourdomain.com\"]"}
    ],
    "secrets": [
      {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "DEFAULT_ADMIN_USERNAME", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "DEFAULT_ADMIN_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/sentinelforge-api",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "api"
      }
    }
  }]
}
```

> **Important**: `DATABASE_URL` for the API must use the `postgresql+asyncpg://`
> prefix. For the worker task definition, use `postgresql://` (the worker
> connects with asyncpg directly, not via SQLAlchemy).

Register task:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-api.json
```

### Step 8: Create ECS Services

```bash
aws ecs create-service \
  --cluster sentinelforge-prod \
  --service-name api \
  --task-definition sentinelforge-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000"
```

### Step 9: Configure Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name sentinelforge-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Create target group
aws elbv2 create-target-group \
  --name sentinelforge-api-tg \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /health \
  --target-type ip

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

### Step 10: Verify Deployment

```bash
# Check service status
aws ecs describe-services --cluster sentinelforge-prod --services api

# Get ALB DNS name
aws elbv2 describe-load-balancers --names sentinelforge-alb --query 'LoadBalancers[0].DNSName'
```

Test health endpoint:
```bash
curl https://your-alb-dns-name.us-east-1.elb.amazonaws.com/health
```

---

## Production Deployment (On-Premises)

### Step 1: Prepare Server

**Recommended**: Ubuntu 22.04 LTS or RHEL 8+

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (includes Docker Compose v2 as a plugin)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Verify both Docker and Compose v2 are available
docker --version
docker compose version
```

> **Note**: Modern Docker installations include Compose v2 as a built-in plugin
> (`docker compose`). The legacy standalone binary `docker-compose` (v1) is
> deprecated. All commands in this guide use the v2 syntax: `docker compose`.

### Step 2: Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/sentinelforge
cd /opt/sentinelforge

# Copy files (adjust source path)
sudo cp -r /path/to/sentinelforge/* .

# Set up environment
sudo cp .env.example .env
sudo nano .env  # Configure with production values
```

### Step 3: Configure Production Environment

Edit `/opt/sentinelforge/.env`:

```env
# -----------------------------------------------------------------
# REQUIRED: Authentication & Security
# The API will refuse to start if these are missing or weak.
# -----------------------------------------------------------------

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=<256-bit-random-key>

# Admin credentials (password must be 12+ chars, mixed case, numbers, symbols)
DEFAULT_ADMIN_USERNAME=sf_admin
DEFAULT_ADMIN_PASSWORD=<strong-production-password>

# -----------------------------------------------------------------
# Database
# -----------------------------------------------------------------
# API uses SQLAlchemy with asyncpg -- requires postgresql+asyncpg:// prefix
DATABASE_URL=postgresql+asyncpg://prod_user:secure_password@postgres:5432/sentinelforge_prod

# Worker connects with asyncpg directly -- uses standard postgresql:// prefix
# (The docker-compose.yml sets this automatically for the worker container;
#  override only if the worker connects to a different host.)

POSTGRES_USER=prod_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=sentinelforge_prod

# -----------------------------------------------------------------
# S3/MinIO
# -----------------------------------------------------------------
S3_ENDPOINT=https://s3.yourdomain.com
S3_BUCKET=sentinelforge-prod

# -----------------------------------------------------------------
# CORS (explicit origins only -- no wildcards in production)
# -----------------------------------------------------------------
CORS_ORIGINS=["https://sentinelforge.yourdomain.com"]

# -----------------------------------------------------------------
# API Keys (use secrets management in production)
# -----------------------------------------------------------------
OPENAI_API_KEY=<from-vault>
ANTHROPIC_API_KEY=<from-vault>

# -----------------------------------------------------------------
# Worker concurrency
# -----------------------------------------------------------------
# docker-compose.yml defaults to 5 if not set. config.py defaults to 10.
# Choose a value appropriate for your hardware.
WORKER_CONCURRENCY=5
```

#### Worker Concurrency Note

The `WORKER_CONCURRENCY` setting controls how many jobs the worker processes
concurrently. The defaults differ across files:

| Source | Default |
|--------|---------|
| `docker-compose.yml` | 5 (`${WORKER_CONCURRENCY:-5}`) |
| `worker.py` | 5 (`os.getenv("WORKER_CONCURRENCY", "5")`) |
| `config.py` | 10 |
| `.env.example` | 10 |

The effective value inside Docker containers is determined by `docker-compose.yml`,
which passes `${WORKER_CONCURRENCY:-5}` -- so the default is **5** unless you
explicitly set it in `.env`. Set it based on available CPU cores and expected load.

#### Tools Registry Path Note

The `.env.example` contains `TOOLS_REGISTRY_PATH=/opt/sentinelforge/tools/registry.yaml`.
Inside Docker containers, the working directory is `/app` and the tools directory
is mounted at `/app/tools/`, so the default in `config.py` (`tools/registry.yaml`,
a relative path) resolves correctly. You generally do not need to override this
unless running outside Docker.

### Step 4: Set Up Reverse Proxy (Nginx)

Install Nginx:
```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

Create `/etc/nginx/sites-available/sentinelforge`:
```nginx
server {
    listen 80;
    server_name sentinelforge.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/sentinelforge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d sentinelforge.yourdomain.com
```

### Step 5: Start Production Services

There is a single `docker-compose.yml` for both development and production.
Customize behavior through your `.env` file settings.

```bash
cd /opt/sentinelforge
sudo docker compose up -d
```

### Step 6: Set Up Systemd Service

Create `/etc/systemd/system/sentinelforge.service`:
```ini
[Unit]
Description=SentinelForge AI Red Team Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sentinelforge
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=root

[Install]
WantedBy=multi-user.target
```

> **Note**: This uses `docker compose` (Compose v2 plugin syntax).
> If you have an older system with only `docker-compose` v1 installed,
> replace with `/usr/local/bin/docker-compose`, but upgrading to v2 is
> strongly recommended.

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sentinelforge
sudo systemctl start sentinelforge
```

---

## Configuration

### Environment Variables Reference

See [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md#environment-variables) for complete list.

### Scaling Configuration

Adjust replicas and resource limits in your `docker-compose.yml` deploy section
or via environment variables:

**API Service**:
```yaml
# In docker-compose.yml under the api service
api:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

**Worker Service**:
```yaml
worker:
  deploy:
    replicas: 5
  environment:
    WORKER_CONCURRENCY: 20
```

---

## Health Checks & Verification

### Manual Health Checks

**Linux / macOS:**
```bash
# API health
curl http://localhost:8000/health

# Database connectivity
docker exec sf-postgres pg_isready

# MinIO connectivity
curl http://localhost:9000/minio/health/live

# Worker status
docker logs sf-worker --tail 50
```

**Windows (PowerShell):**
```powershell
# API health
Invoke-RestMethod http://localhost:8000/health

# Database connectivity
docker exec sf-postgres pg_isready

# Worker status
docker logs sf-worker --tail 50
```

### Automated Monitoring

Set up alerts in Grafana (http://localhost:3000):

1. Import dashboard from `infra/observability/dashboards/`
2. Configure alert channels (Slack, PagerDuty, email)
3. Set thresholds for:
   - API response time > 500ms
   - Error rate > 1%
   - Database connections > 80%
   - Worker queue depth > 100

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs api
docker compose logs worker

# Restart services
docker compose restart
```

**Common cause**: The API container exits immediately with `SECURITY CONFIG ERROR`
because `JWT_SECRET_KEY`, `DEFAULT_ADMIN_USERNAME`, or `DEFAULT_ADMIN_PASSWORD`
is missing or too weak in `.env`. See Step 3 above.

### Database Connection Errors

```bash
# Verify database is running
docker exec sf-postgres pg_isready

# Check credentials match between .env and docker-compose.yml
# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### API Key Errors

```bash
# Verify API keys are set inside the container
docker exec sf-api printenv | grep API_KEY

# Test OpenAI key directly
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Worker Not Processing Jobs

```bash
# Check worker logs
docker logs sf-worker -f

# Verify database connection
docker exec sf-worker printenv DATABASE_URL

# Check job queue
docker exec sf-postgres psql -U sentinelforge_user -d sentinelforge -c "SELECT * FROM attack_runs WHERE status='queued';"
```

---

## Security Best Practices

### Production Checklist

- [ ] Set strong `JWT_SECRET_KEY` (64 hex characters / 256-bit random)
- [ ] Set strong `DEFAULT_ADMIN_PASSWORD` (12+ chars, mixed case, numbers, symbols)
- [ ] Change default database passwords
- [ ] Store API keys in secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Set `CORS_ORIGINS` to explicit production domain(s) -- never use `*`
- [ ] Set `DEBUG=false` (the default)
- [ ] Enable HTTPS/TLS everywhere
- [ ] Configure firewall rules (only expose necessary ports)
- [ ] Enable database encryption at rest
- [ ] Enable S3 bucket encryption
- [ ] Set up VPC/network isolation
- [ ] Configure audit logging
- [ ] Enable MFA for admin accounts
- [ ] Regular security updates (`docker compose pull`)
- [ ] Backup databases daily
- [ ] Monitor for vulnerabilities

### Network Security

```bash
# Firewall rules (example with ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct API access (use reverse proxy)
sudo ufw deny 5432/tcp   # Block direct DB access
sudo ufw enable
```

---

## Next Steps

1. Review [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) for all CLI commands
2. Review [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for tools documentation
3. Set up monitoring dashboards
4. Configure backup automation
5. Train team on platform usage

For production support, monitor logs and set up alerts!
