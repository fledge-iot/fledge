#!/usr/bin/env bash
set -euo pipefail

BASE_IMAGE="${1:-ubuntu:22.04}"
PLATFORM="${2:-linux/amd64}"
OUT_DIR="${OUT_DIR:-./build-out}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p "$OUT_DIR"

if docker buildx inspect fledge-builder >/dev/null 2>&1; then
    docker buildx use fledge-builder
else
    docker buildx create --name fledge-builder --use
fi

docker buildx build \
    --file .ci/deb/Dockerfile \
    --target artifact \
    --output "type=local,dest=${OUT_DIR}" \
    --platform "$PLATFORM" \
    --build-arg BASE_IMAGE="$BASE_IMAGE" \
    .

ls -la "$OUT_DIR"
