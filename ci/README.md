# SentinelForge CI/CD Integration

Run AI/ML security scans automatically in your CI/CD pipeline. Uses SentinelForge's API with API key authentication (v1.5+).

## GitHub Actions

### Quick Start

```yaml
# .github/workflows/security-scan.yml
name: AI Security Scan

on:
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: sentinelforge/scan@v1
        with:
          api_url: ${{ secrets.SENTINELFORGE_URL }}
          api_key: ${{ secrets.SENTINELFORGE_API_KEY }}
          scenario: 'prompt-injection-suite'
          target_model: 'openai:gpt-4'
          fail_on_severity: 'high'    # Fail PR if high+ findings
          comment_on_pr: 'true'       # Post results as PR comment
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `api_url` | ✅ | — | SentinelForge API base URL |
| `api_key` | ✅ | — | API key (use GitHub Secrets) |
| `scenario` | ✅ | — | Attack scenario ID to run |
| `target_model` | ✅ | — | Model identifier |
| `fail_on_severity` | ❌ | `high` | Gate: `critical`, `high`, `medium`, `low`, `none` |
| `timeout` | ❌ | `600` | Max scan wait time (seconds) |
| `config` | ❌ | `{}` | Extra config as JSON |
| `comment_on_pr` | ❌ | `true` | Post results as PR comment |

### Outputs

| Output | Description |
|--------|-------------|
| `scan_id` | Scan run ID |
| `status` | Final status |
| `total_findings` | Total findings count |
| `critical_count` | Critical findings count |
| `high_count` | High findings count |
| `report_url` | Link to full report |

### PR Comment Example

The action posts a formatted comment on your PR with:
- Severity badge (🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / ✅ CLEAN)
- Findings summary table
- Top 5 findings with descriptions
- Link to the full report

---

## GitLab CI

### Quick Start

```yaml
# .gitlab-ci.yml
include:
  - remote: 'https://raw.githubusercontent.com/sentinelforge/sentinelforge/main/ci/gitlab/.gitlab-ci-template.yml'

sentinelforge-scan:
  extends: .sentinelforge-scan
  variables:
    SF_API_URL: "https://your-sentinelforge.example.com"
    SF_API_KEY: $SENTINELFORGE_API_KEY    # Set in GitLab CI/CD Variables
    SF_SCENARIO: "prompt-injection-suite"
    SF_TARGET_MODEL: "openai:gpt-4"
    SF_FAIL_ON: "high"
```

### Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SF_API_URL` | ✅ | — | SentinelForge API URL |
| `SF_API_KEY` | ✅ | — | API key (use CI/CD variables) |
| `SF_SCENARIO` | ✅ | — | Attack scenario ID |
| `SF_TARGET_MODEL` | ✅ | — | Target model |
| `SF_FAIL_ON` | ❌ | `high` | Severity gate |
| `SF_TIMEOUT` | ❌ | `600` | Timeout (seconds) |
| `SF_CONFIG` | ❌ | `{}` | Extra config JSON |

---

## Creating an API Key

```bash
# Via API (requires JWT auth)
curl -X POST https://your-sentinelforge/api-keys \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-pipeline", "scopes": ["read", "write"]}'
```

Store the returned `raw_key` in your CI/CD secrets:
- **GitHub**: Settings → Secrets → `SENTINELFORGE_API_KEY`
- **GitLab**: Settings → CI/CD → Variables → `SENTINELFORGE_API_KEY` (masked)

---

## Recommended Scenarios

| Scenario | When to Run | Description |
|----------|-------------|-------------|
| `prompt_injection` | Every PR | 48 prompts covering direct injection, encoding, context manipulation, payload splitting |
| `jailbreak` | Every PR | 39 prompts for DAN/STAN, roleplay, token smuggling, philosophical override |
| `system_prompt_defense` | Every PR | 29 prompts across 6 extraction techniques |
| `data_leakage` | Weekly / Release | 30 prompts for PII, credential, and training data extraction |
| `toxicity_bias` | Weekly / Release | 22 prompts for toxicity, demographic bias, stereotypes, hate speech |
| `hallucination` | Weekly / Release | 21 prompts for factual accuracy, source fabrication, confidence calibration |
| `multi_turn_social_engineering` | Weekly / Release | 28 multi-turn prompts with 3 manipulation strategies |
| `rag_poisoning` | On RAG changes | 18 prompts for RAG-specific injection, conflicting context, exfiltration |
| `drift-baseline-check` | Nightly | Compare against drift baselines |
| `supply-chain-scan` | On dependency changes | Check model artifacts |
