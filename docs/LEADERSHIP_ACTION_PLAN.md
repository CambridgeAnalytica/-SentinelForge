# SentinelForge — Leadership Action Plan

**Prepared for:** Senior Leadership  
**Date:** February 9, 2026  
**Document Status:** AWAITING APPROVAL  
**Companion Documents:** [Executive Summary](EXECUTIVE_SUMMARY.md) · [Security Risk Assessment](SECURITY_RISK_ASSESSMENT.md) · [Deployment Guide](DEPLOYMENT_GUIDE.md)

---

## Decision Required

> [!IMPORTANT]
> **This document outlines 7 action items required to operationalize SentinelForge.** Items 1–3 require leadership approval before the engineering team can proceed. Items 4–7 execute sequentially after approval.

---

## Implementation Timeline

```
Week 1–2          Week 3–4          Month 2            Month 3            Ongoing
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Action 1  │    │ Action 4  │    │  Action 5    │    │  Action 6    │    │  Action 7    │
│ Approve   │───▶│ Configure │───▶│  DPA with    │───▶│  CI/CD Gate  │───▶│  Annual 3rd  │
│ Deployment│    │ Production│    │  AI Vendors  │    │  Integration │    │  Party Audit │
├──────────┤    ├──────────┤    └──────────────┘    └──────────────┘    └──────────────┘
│ Action 2  │    │ Action 4b │
│ Assign    │───▶│ Baseline  │
│ Operator  │    │ Assessment│
├──────────┤    └──────────┘
│ Action 3  │
│ Budget    │
│ Approval  │
└──────────┘
```

---

## Action 1: Approve SentinelForge for Internal Production Deployment

| | |
|---|---|
| **Owner** | CISO / CTO |
| **Deadline** | Week 1 |
| **Decision Type** | Go / No-Go |
| **Budget Impact** | $88,000/year operational (infrastructure + personnel, see [ROI analysis](EXECUTIVE_SUMMARY.md#return-on-investment-analysis)) |

### What Is Being Approved

Authorization to deploy SentinelForge on enterprise infrastructure as the **primary** AI security testing platform, supplemented by annual third-party validation.

### Approval Checklist

| Item | Status | Reference |
|------|:------:|-----------|
| Platform has passed internal cyber risk assessment | ✅ Complete | [Security Risk Assessment](SECURITY_RISK_ASSESSMENT.md) |
| No CRITICAL or HIGH unmitigated findings | ✅ Complete | [Risk Register](SECURITY_RISK_ASSESSMENT.md#12-risk-register) |
| Data exposure to external AI providers analyzed | ✅ Complete | [Data Exposure Analysis](SECURITY_RISK_ASSESSMENT.md#8-data-exposure-analysis--external-ai-providers) |
| ROI analysis demonstrates positive return | ✅ Complete | [Executive Summary ROI](EXECUTIVE_SUMMARY.md#return-on-investment-analysis) |
| Deployment guide reviewed by DevOps | ☐ Pending | [Deployment Guide](DEPLOYMENT_GUIDE.md) |
| Legal review of AI provider terms of service | ☐ Pending | See Action 5 |

### Decision Gate

```
            ┌─────────────────────────────────────┐
            │   Does leadership approve internal   │
            │   deployment of SentinelForge?        │
            └──────────────┬──────────────────────┘
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
        ┌─────────────┐        ┌─────────────┐
        │  APPROVED    │        │  NOT APPROVED│
        │  → Action 2  │        │  → Document  │
        │              │        │    concerns  │
        │              │        │    & revisit │
        └─────────────┘        └─────────────┘
```

**Signature Line:**

| Role | Name | Date | Approval |
|------|------|:----:|:--------:|
| CISO | _________________ | ____/____/____ | ☐ Approved  ☐ Denied |
| CTO | _________________ | ____/____/____ | ☐ Approved  ☐ Denied |
| VP Engineering | _________________ | ____/____/____ | ☐ Approved  ☐ Denied |

---

## Action 2: Assign Dedicated SentinelForge Operator

| | |
|---|---|
| **Owner** | VP Engineering / Director of AI Security |
| **Deadline** | Week 1–2 |
| **Decision Type** | Staffing allocation |
| **FTE Requirement** | 20% of one engineer (~8 hours/week) |

### Role Definition

| Attribute | Detail |
|-----------|--------|
| **Title** | SentinelForge Operator (secondary role) |
| **Time commitment** | ~20% FTE (8 hrs/week) |
| **Team** | AI Security, Cyber Operations, or DevSecOps |
| **RBAC role** | `OPERATOR` (can launch attacks, execute tools, generate reports) |
| **Reports to** | CISO or Director of AI Security |

### Responsibilities

| Responsibility | Frequency | Est. Time |
|---------------|:---------:|:---------:|
| Execute pre-deployment security assessments | Per AI release | 2–4 hrs |
| Monitor model drift dashboards | Weekly | 1 hr |
| Generate compliance reports for auditors | Monthly / on-demand | 1 hr |
| Triage and communicate findings to dev teams | As needed | 1–2 hrs |
| Maintain platform configuration and tool updates | Monthly | 2 hrs |
| Coordinate with third-party auditor (Action 7) | Annually | 4 hrs |

### Ideal Candidate Profile

- Background in cybersecurity, AI/ML, or DevSecOps
- Familiarity with MITRE ATT&CK / ATLAS frameworks
- Experience with Docker, Python, CLI tools
- Understanding of LLM architecture and prompt engineering
- Existing team member preferred (no new hire required)

### Knowledge Transfer Plan

| Phase | Activity | Duration |
|-------|----------|:--------:|
| Week 1 | Platform walkthrough with technical lead | 2 hours |
| Week 1 | Run guided attack scenario (prompt injection) | 1 hour |
| Week 2 | Independent execution of all 5 pre-built scenarios | 4 hours |
| Week 2 | Report generation and interpretation workshop | 1 hour |
| Week 3 | Custom scenario creation training | 2 hours |

---

## Action 3: Approve Operational Budget

| | |
|---|---|
| **Owner** | CFO / Finance |
| **Deadline** | Week 2 |
| **Decision Type** | Budget approval |

### Annual Budget Breakdown

| Line Item | Year 1 | Year 2+ | Notes |
|-----------|:------:|:-------:|-------|
| Cloud infrastructure (Docker host) | $12,000 | $12,000 | VMs, storage, networking |
| AI API token consumption | $6,000 | $10,000 | Attack scenario execution against target models |
| Platform maintenance (eng. time) | $30,000 | $20,000 | ~10% FTE; decreases as platform matures |
| Operator time (test & analysis) | $40,000 | $40,000 | ~20% FTE allocation |
| **Subtotal: SentinelForge** | **$88,000** | **$82,000** | |
| Annual third-party validation (Action 7) | $150,000 | $150,000 | Reduced from 2–4x/year to 1x/year |
| **Total program cost** | **$238,000** | **$232,000** | |

### Savings vs. Current Spend

| Scenario | Current Vendor Spend | Proposed Spend | **Annual Savings** |
|----------|:-------------------:|:--------------:|:------------------:|
| Conservative (3 models, 2x/year) | $450,000 | $238,000 | **$212,000** |
| Mid-range (5 models, 3x/year) | $1,875,000 | $238,000 | **$1,637,000** |
| Aggressive (10 models, 4x/year) | $10,000,000 | $238,000 | **$9,762,000** |

---

## Action 4: Configure Production Environment & Execute Baseline Assessment

| | |
|---|---|
| **Owner** | Assigned Operator + DevOps |
| **Deadline** | Week 3–4 |
| **Prerequisites** | Actions 1, 2, 3 approved |

### 4A — Production Configuration

Execute the steps outlined in the [Deployment Guide](DEPLOYMENT_GUIDE.md):

| Step | Task | Owner | Reference |
|:----:|------|-------|-----------|
| 1 | Provision production host (16GB RAM, 8 CPU, 100GB disk) | DevOps | [System Requirements](DEPLOYMENT_GUIDE.md#system-requirements) |
| 2 | Clone SentinelForge repository to production host | DevOps | — |
| 3 | Create `.env` from `.env.example` with production secrets | DevOps + Security | [Configuration](DEPLOYMENT_GUIDE.md#configuration) |
| 4 | Generate strong `JWT_SECRET_KEY` (256-bit random) | Security | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| 5 | Set `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` (12+ chars, complex) | Security | [Password Policy](SECURITY_RISK_ASSESSMENT.md#34-password-policy) |
| 6 | Configure AI provider API keys (at least one) | Operator | OpenAI / Anthropic / Azure |
| 7 | Set `CORS_ORIGINS` to explicit production domain(s) | DevOps | — |
| 8 | Set `DEBUG=False` | DevOps | Required for security enforcement |
| 9 | Run `docker compose up -d` | DevOps | [Deployment Guide](DEPLOYMENT_GUIDE.md#local-development-setup) |
| 10 | Verify health: `curl http://localhost:8000/health` | Operator | — |
| 11 | Login via CLI: `sf auth login` | Operator | [CLI Reference](COMMAND_REFERENCE.md) |

### 4B — Baseline Assessment

Once the platform is operational, execute baseline assessments against all deployed AI models:

| Step | Command | Purpose |
|:----:|---------|---------|
| 1 | `sf attack list` | Confirm all 5 scenarios are loaded |
| 2 | `sf attack run prompt_injection --target <model>` | Test prompt injection resilience |
| 3 | `sf attack run jailbreak --target <model>` | Test jailbreak resistance |
| 4 | `sf attack run data_leakage --target <model>` | Test for data exfiltration |
| 5 | `sf attack run hallucination --target <model>` | Test factual accuracy |
| 6 | `sf attack run toxicity_bias --target <model>` | Test for bias and toxicity |
| 7 | `sf report generate <run_id> --format html` | Generate baseline report per model |
| 8 | `sf drift baseline --model <model> --save baseline_<model>.json` | Save drift baseline |

**Repeat steps 2–8 for each deployed AI model.**

### Deliverable

A baseline security posture report for each AI model, stored in SentinelForge and exportable as HTML for stakeholder review.

---

## Action 5: Execute Data Processing Agreements with AI Providers

| | |
|---|---|
| **Owner** | Legal / Procurement |
| **Deadline** | Month 2 |
| **Prerequisites** | Action 1 approved |
| **Criticality** | 🔴 Required for compliance |

### Why This Matters

SentinelForge sends scrubbed attack prompts to external AI providers during testing. Although the platform's [redaction layer](SECURITY_RISK_ASSESSMENT.md#82-redaction-layer--enforced-patterns) removes 15+ categories of PII and credentials before transmission, AI providers may retain prompt data for abuse monitoring. A Data Processing Agreement (DPA) contractually limits what providers can do with submitted data.

### Required Agreements

| Provider | DPA Mechanism | Action | Est. Timeline |
|----------|--------------|--------|:-------------:|
| **OpenAI** | Enterprise API agreement + zero-data-retention opt-out | Contact OpenAI sales for enterprise tier | 2–4 weeks |
| **Anthropic** | Enterprise API agreement | Contact Anthropic sales | 2–4 weeks |
| **Azure OpenAI** | Microsoft Enterprise Agreement (already in place for most orgs) + Azure OpenAI terms | Verify existing EA covers AI services | 1 week |

### DPA Checklist

| Clause | Requirement | Status |
|--------|-------------|:------:|
| No training on submitted data | Explicit contractual guarantee | ☐ |
| Prompt data retention period | Defined and acceptable (≤30 days for abuse monitoring) | ☐ |
| Data residency | Within approved jurisdictions | ☐ |
| Audit rights | Ability to audit provider's compliance | ☐ |
| Breach notification | Provider must notify within 72 hours | ☐ |
| Subprocessor restrictions | Limits on which third parties can access data | ☐ |

### Deliverable

Executed DPA with primary AI provider(s), filed with Legal and referenced in the platform's operational runbook.

---

## Action 6: Integrate SentinelForge into CI/CD Pipeline

| | |
|---|---|
| **Owner** | DevOps / AI Platform Engineering |
| **Deadline** | Month 3 |
| **Prerequisites** | Actions 4 complete, baseline established |

### Objective

Make SentinelForge a **mandatory deployment gate** for all AI model releases. No AI model or prompt configuration change ships to production without a passing SentinelForge assessment.

### Integration Architecture

```
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌────────────┐
│  Developer     │     │   CI/CD Pipeline │     │  SentinelForge   │     │ Production │
│  pushes code   │────▶│  (GitHub Actions/│────▶│  Security Gate   │────▶│ Deployment │
│                │     │   Jenkins/etc.)  │     │                  │     │            │
└───────────────┘     └─────────────────┘     └──────────────────┘     └────────────┘
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                                │ PASS: Deploy  │
                                                │ FAIL: Block + │
                                                │ notify team   │
                                                └──────────────┘
```

### Implementation Steps

| Step | Task | Details |
|:----:|------|--------|
| 1 | Define pass/fail criteria | E.g., "No CRITICAL findings, no jailbreak successes" |
| 2 | Create CI/CD stage script | Call SentinelForge API via SDK: `sf attack run <scenario> --target <model> --wait` |
| 3 | Parse results programmatically | Use SentinelForge SDK or API response to check finding severity |
| 4 | Block deployment on failure | Pipeline exits non-zero if any CRITICAL or HIGH findings detected |
| 5 | Notify teams on failure | Slack/Teams/email alert with finding summary and report link |
| 6 | Archive results | Store run ID and report in deployment metadata for audit trail |

### Example Pipeline Gate (Pseudocode)

```bash
# CI/CD pipeline step
RESULT=$(sf attack run prompt_injection --target $MODEL --format json --wait)
CRITICAL_COUNT=$(echo $RESULT | jq '.findings | map(select(.severity == "critical")) | length')

if [ "$CRITICAL_COUNT" -gt 0 ]; then
    echo "❌ SentinelForge: $CRITICAL_COUNT critical finding(s). Deployment blocked."
    sf report generate $RUN_ID --format html
    exit 1
fi

echo "✅ SentinelForge: All checks passed. Proceeding to deployment."
```

### Deliverable

CI/CD pipeline configuration that invokes SentinelForge as a mandatory pre-deployment gate, with documented pass/fail criteria approved by the CISO.

---

## Action 7: Schedule Annual Third-Party Validation Assessment

| | |
|---|---|
| **Owner** | CISO / Procurement |
| **Deadline** | Month 3 (schedule), execute within FY |
| **Prerequisites** | Baseline assessments complete (Action 4B) |
| **Budget** | ~$150,000/year |

### Purpose

An annual independent assessment by an external vendor (e.g., Booz Allen Hamilton) provides:
1. **External perspective** — Fresh eyes on attack surface and blind spots
2. **Regulatory evidence** — Third-party validation for auditors and compliance frameworks
3. **Benchmarking** — Compare SentinelForge findings against vendor-discovered issues
4. **Credibility** — Executive and board-level assurance from a recognized firm

### Scope Reduction

Because SentinelForge handles continuous testing, the third-party engagement can be **significantly reduced** from the current model:

| Element | Current Vendor Scope | Reduced Scope (with SentinelForge) |
|---------|:-------------------:|:----------------------------------:|
| Assessment frequency | 2–4x/year | **1x/year** |
| Per-assessment duration | 4–12 weeks | **2–4 weeks** |
| Scope | Full red teaming from scratch | **Validation & gap analysis focus** |
| Deliverable | Full findings report | Delta report comparing vendor vs. SentinelForge findings |
| Est. cost | $150K–$250K per engagement | **~$150K total/year** |

### Vendor Engagement Checklist

| Task | Owner | Deadline |
|------|-------|:--------:|
| Issue RFP or activate existing contract vehicle (e.g., GSA HACS SIN) | Procurement | Month 3 |
| Define scope: validate SentinelForge findings + identify gaps | CISO + Operator | Month 3 |
| Share SentinelForge baseline reports with vendor (as input) | Operator | Pre-engagement |
| Schedule engagement window | Procurement | Q3 or Q4 |
| Execute assessment | Vendor | 2–4 weeks |
| Review vendor report vs. SentinelForge findings | Operator + CISO | 1 week post-delivery |
| Document any gaps and feed back into SentinelForge scenarios | Operator | 2 weeks post-delivery |

### Deliverable

A signed contract for annual third-party AI security validation, with scope explicitly reduced to a delta assessment that validates and supplements SentinelForge's continuous testing.

---

## Summary: All 7 Actions at a Glance

| # | Action | Owner | Deadline | Type | Status |
|:-:|--------|-------|:--------:|:----:|:------:|
| 1 | Approve internal production deployment | CISO / CTO | Week 1 | Decision | ☐ Pending |
| 2 | Assign dedicated Operator (20% FTE) | VP Engineering | Week 1–2 | Staffing | ☐ Pending |
| 3 | Approve operational budget ($238K/yr) | CFO | Week 2 | Budget | ☐ Pending |
| 4 | Configure production & baseline assessment | Operator + DevOps | Week 3–4 | Technical | ☐ Blocked on 1–3 |
| 5 | Execute DPAs with AI providers | Legal | Month 2 | Legal | ☐ Blocked on 1 |
| 6 | Integrate into CI/CD pipeline | DevOps | Month 3 | Technical | ☐ Blocked on 4 |
| 7 | Schedule annual third-party validation | CISO / Procurement | Month 3 | Procurement | ☐ Blocked on 4 |

---

## Appendix: Document Map

All supporting documentation is available in the SentinelForge `docs/` directory:

| Document | Purpose | Audience |
|----------|---------|----------|
| [Executive Summary](EXECUTIVE_SUMMARY.md) | ROI analysis, strategic case for leadership | C-Suite |
| **This Document** | Detailed action plan with ownership and timelines | C-Suite + Directors |
| [Security Risk Assessment](SECURITY_RISK_ASSESSMENT.md) | Technical security posture analysis | CISO, Cyber Risk Team |
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Step-by-step infrastructure setup | DevOps, Operator |
| [Tools Reference](TOOLS_REFERENCE.md) | All 14 integrated security tools | Operator, Security Engineers |
| [Command Reference](COMMAND_REFERENCE.md) | CLI, API, Docker commands | Operator, Developers |
| [Documentation Index](INDEX.md) | Master navigation for all docs | All audiences |

---

*This action plan supports the [SentinelForge Executive Summary](EXECUTIVE_SUMMARY.md). For questions, contact the AI Security or Cyber Risk team.*
