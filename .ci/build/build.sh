#!/usr/bin/env bash
# Build fledge_<version>_<arch>.deb locally via Docker buildx.
#
# Usage:
#   .ci/build/build.sh                           # defaults: Ubuntu 22.04, amd64
#   .ci/build/build.sh ubuntu:22.04              # ubuntu 22.04, amd64
#   .ci/build/build.sh ubuntu:22.04 linux/arm64  # multi-arch via QEMU
#
# Output directory: ./build-out/

set -euo pipefail

BASE_IMAGE="${1:-ubuntu:22.04}"
PLATFORM="${2:-linux/amd64}"
OUT_DIR="${OUT_DIR:-./build-out}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p "$OUT_DIR"

echo ">> Building Fledge .deb"
echo "   base image : $BASE_IMAGE"
echo "   platform   : $PLATFORM"
echo "   output dir : $OUT_DIR"
echo

# Ensure a buildx builder exists and is active.
if docker buildx inspect fledge-builder >/dev/null 2>&1; then
    docker buildx use fledge-builder
else
    docker buildx create --name fledge-builder --use
fi

docker buildx build \
    --file .ci/build/Dockerfile \
    --target artifact \
    --output "type=local,dest=${OUT_DIR}" \
    --platform "$PLATFORM" \
    --build-arg BASE_IMAGE="$BASE_IMAGE" \
    --build-arg DEB_VERSION="${DEB_VERSION:-}" \
    .

echo
echo ">> Build complete. Artifact(s):"
ls -la "$OUT_DIR"
