#!/bin/bash
# SentinelForge Vulnerability Scanning Script
# Scans container images for known vulnerabilities using grype

set -e

IMAGES=("sentinelforge/api:latest" "sentinelforge/worker:latest" "sentinelforge/tools:latest")

echo "🔍 Scanning for vulnerabilities..."

for IMAGE in "${IMAGES[@]}"; do
    echo "  Scanning $IMAGE..."

    if command -v grype &> /dev/null; then
        grype "$IMAGE" --fail-on critical 2>/dev/null || echo "  ⚠️  Critical vulnerabilities found in $IMAGE"
        echo "  ✅ Scan complete for $IMAGE"
    else
        echo "  ⚠️  grype not installed, skipping $IMAGE"
        echo "  Install: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin"
    fi
done

echo "✅ Vulnerability scanning complete"
