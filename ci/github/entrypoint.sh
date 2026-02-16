#!/usr/bin/env bash
# SentinelForge CI/CD scan entrypoint
# Launches a scan, polls for completion, formats results, and optionally comments on PRs.

set -euo pipefail

# ── Configuration ──
API_URL="${SF_API_URL:?SF_API_URL is required}"
API_KEY="${SF_API_KEY:?SF_API_KEY is required}"
SCENARIO="${SF_SCENARIO:?SF_SCENARIO is required}"
TARGET_MODEL="${SF_TARGET_MODEL:?SF_TARGET_MODEL is required}"
FAIL_ON="${SF_FAIL_ON:-high}"
TIMEOUT="${SF_TIMEOUT:-600}"
CONFIG="${SF_CONFIG:-{}}"
COMMENT_ON_PR="${SF_COMMENT_ON_PR:-true}"

SEVERITY_LEVELS=("critical" "high" "medium" "low" "none")

# ── Helper Functions ──

severity_index() {
    local sev="${1,,}"
    for i in "${!SEVERITY_LEVELS[@]}"; do
        if [[ "${SEVERITY_LEVELS[$i]}" == "$sev" ]]; then
            echo "$i"
            return
        fi
    done
    echo 4  # none
}

log() { echo "::group::$1"; }
endlog() { echo "::endgroup::"; }

api() {
    local method="$1" path="$2"
    shift 2
    curl -sf -X "$method" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        "${API_URL}${path}" "$@"
}

# ── Step 1: Launch Scan ──

log "🚀 Launching SentinelForge scan"
echo "Scenario: ${SCENARIO}"
echo "Target:   ${TARGET_MODEL}"

LAUNCH_RESPONSE=$(api POST "/attacks/runs" -d "{
    \"scenario_id\": \"${SCENARIO}\",
    \"target_model\": \"${TARGET_MODEL}\",
    \"config\": ${CONFIG}
}")

SCAN_ID=$(echo "$LAUNCH_RESPONSE" | jq -r '.id // empty')
if [[ -z "$SCAN_ID" ]]; then
    echo "::error::Failed to launch scan. Response: ${LAUNCH_RESPONSE}"
    exit 1
fi

echo "Scan ID: ${SCAN_ID}"
echo "scan_id=${SCAN_ID}" >> "$GITHUB_OUTPUT"
endlog

# ── Step 2: Poll for Completion ──

log "⏳ Waiting for scan to complete (timeout: ${TIMEOUT}s)"

ELAPSED=0
POLL_INTERVAL=10

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    STATUS_RESPONSE=$(api GET "/attacks/runs/${SCAN_ID}")
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status // "unknown"')

    echo "  [${ELAPSED}s] Status: ${STATUS}"

    if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
        break
    fi

    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if [[ "$STATUS" != "completed" && "$STATUS" != "failed" ]]; then
    echo "::warning::Scan timed out after ${TIMEOUT}s"
    echo "status=timed_out" >> "$GITHUB_OUTPUT"
    exit 1
fi

echo "status=${STATUS}" >> "$GITHUB_OUTPUT"
endlog

# ── Step 3: Parse Results ──

log "📊 Parsing scan results"

RESULTS=$(api GET "/attacks/runs/${SCAN_ID}")
FINDINGS=$(echo "$RESULTS" | jq '.findings // []')
TOTAL=$(echo "$FINDINGS" | jq 'length')
CRITICAL=$(echo "$FINDINGS" | jq '[.[] | select(.severity == "critical")] | length')
HIGH=$(echo "$FINDINGS" | jq '[.[] | select(.severity == "high")] | length')
MEDIUM=$(echo "$FINDINGS" | jq '[.[] | select(.severity == "medium")] | length')
LOW=$(echo "$FINDINGS" | jq '[.[] | select(.severity == "low")] | length')

echo "Total findings: ${TOTAL}"
echo "  Critical: ${CRITICAL}"
echo "  High:     ${HIGH}"
echo "  Medium:   ${MEDIUM}"
echo "  Low:      ${LOW}"

echo "total_findings=${TOTAL}" >> "$GITHUB_OUTPUT"
echo "critical_count=${CRITICAL}" >> "$GITHUB_OUTPUT"
echo "high_count=${HIGH}" >> "$GITHUB_OUTPUT"
echo "report_url=${API_URL}/attacks/runs/${SCAN_ID}" >> "$GITHUB_OUTPUT"
endlog

# ── Step 4: Post PR Comment ──

if [[ "$COMMENT_ON_PR" == "true" && -n "${GITHUB_EVENT_PATH:-}" ]]; then
    PR_NUMBER=$(jq -r '.pull_request.number // empty' "$GITHUB_EVENT_PATH" 2>/dev/null || true)

    if [[ -n "$PR_NUMBER" ]]; then
        log "💬 Posting results to PR #${PR_NUMBER}"

        # Build severity badge
        if [[ $CRITICAL -gt 0 ]]; then
            BADGE="🔴 CRITICAL"
        elif [[ $HIGH -gt 0 ]]; then
            BADGE="🟠 HIGH"
        elif [[ $MEDIUM -gt 0 ]]; then
            BADGE="🟡 MEDIUM"
        elif [[ $LOW -gt 0 ]]; then
            BADGE="🟢 LOW"
        else
            BADGE="✅ CLEAN"
        fi

        # Build findings table
        FINDINGS_TABLE=""
        if [[ $TOTAL -gt 0 ]]; then
            FINDINGS_TABLE="| Severity | Count |\n|----------|-------|\n"
            FINDINGS_TABLE+="| 🔴 Critical | ${CRITICAL} |\n"
            FINDINGS_TABLE+="| 🟠 High | ${HIGH} |\n"
            FINDINGS_TABLE+="| 🟡 Medium | ${MEDIUM} |\n"
            FINDINGS_TABLE+="| 🟢 Low | ${LOW} |\n"
        fi

        # Top findings (first 5)
        TOP_FINDINGS=""
        if [[ $TOTAL -gt 0 ]]; then
            TOP_FINDINGS="\n### Top Findings\n\n"
            TOP_FINDINGS+=$(echo "$FINDINGS" | jq -r '
                [limit(5; .[])] | .[] |
                "- **\(.severity | ascii_upcase)**: \(.title)\n  > \(.description // "No description" | .[0:200])\n"
            ')
        fi

        COMMENT_BODY=$(cat <<EOF
## 🛡️ SentinelForge Security Scan Results

**Status**: ${BADGE} | **Findings**: ${TOTAL} | **Scan ID**: \`${SCAN_ID}\`

${FINDINGS_TABLE}
${TOP_FINDINGS}

<details>
<summary>📋 Scan Details</summary>

- **Scenario**: ${SCENARIO}
- **Target**: ${TARGET_MODEL}
- **Duration**: ${ELAPSED}s
- [Full Report](${API_URL}/attacks/runs/${SCAN_ID})

</details>

---
*Powered by [SentinelForge](https://github.com/sentinelforge) AI Security Platform*
EOF
)

        # Post comment via GitHub API
        REPO="${GITHUB_REPOSITORY}"
        curl -sf -X POST \
            -H "Authorization: Bearer ${GITHUB_TOKEN}" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/${REPO}/issues/${PR_NUMBER}/comments" \
            -d "$(jq -n --arg body "$COMMENT_BODY" '{body: $body}')"

        echo "Comment posted to PR #${PR_NUMBER}"
        endlog
    fi
fi

# ── Step 5: Enforce Severity Gate ──

FAIL_INDEX=$(severity_index "$FAIL_ON")

EXIT_CODE=0
for sev in "${SEVERITY_LEVELS[@]}"; do
    SEV_INDEX=$(severity_index "$sev")
    if [[ $SEV_INDEX -le $FAIL_INDEX ]]; then
        COUNT=$(echo "$FINDINGS" | jq "[.[] | select(.severity == \"${sev}\")] | length")
        if [[ $COUNT -gt 0 ]]; then
            echo "::error::Found ${COUNT} ${sev} finding(s) — exceeds severity gate (${FAIL_ON})"
            EXIT_CODE=1
        fi
    fi
done

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ Scan passed severity gate (fail_on=${FAIL_ON})"
fi

exit $EXIT_CODE
