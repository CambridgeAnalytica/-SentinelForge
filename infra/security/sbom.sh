#!/bin/bash
# SentinelForge SBOM Generation Script
# Generates Software Bill of Materials for all container images

set -e

IMAGES=("sentinelforge/api:latest" "sentinelforge/worker:latest" "sentinelforge/tools:latest")
OUTPUT_DIR="sbom"

mkdir -p "$OUTPUT_DIR"

echo "📋 Generating SBOMs..."

for IMAGE in "${IMAGES[@]}"; do
    NAME=$(echo "$IMAGE" | cut -d'/' -f2 | cut -d':' -f1)
    echo "  Scanning $IMAGE..."

    if command -v syft &> /dev/null; then
        syft "$IMAGE" -o spdx-json > "$OUTPUT_DIR/${NAME}-sbom.json" 2>/dev/null
        echo "  ✅ $OUTPUT_DIR/${NAME}-sbom.json"
    else
        echo "  ⚠️  syft not installed, skipping $IMAGE"
        echo "  Install: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
    fi
done

echo "✅ SBOM generation complete"
