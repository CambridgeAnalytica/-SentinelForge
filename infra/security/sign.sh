#!/bin/bash
# SentinelForge Image Signing Script
# Signs container images with cosign

set -e

IMAGES=("sentinelforge/api:latest" "sentinelforge/worker:latest" "sentinelforge/tools:latest")
COSIGN_KEY="${COSIGN_KEY:-cosign.key}"

echo "✍️ Signing container images..."

for IMAGE in "${IMAGES[@]}"; do
    echo "  Signing $IMAGE..."

    if command -v cosign &> /dev/null; then
        if [ -f "$COSIGN_KEY" ]; then
            cosign sign --key "$COSIGN_KEY" "$IMAGE"
            echo "  ✅ Signed $IMAGE"
        else
            echo "  ⚠️  Cosign key not found at $COSIGN_KEY"
            echo "  Generate: cosign generate-key-pair"
        fi
    else
        echo "  ⚠️  cosign not installed, skipping"
        echo "  Install: go install github.com/sigstore/cosign/v2/cmd/cosign@latest"
    fi
done

echo "✅ Image signing complete"
