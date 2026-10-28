#!/usr/bin/env bash
set -euo pipefail

BASE_IMAGE="${1:?ERROR: missing BASE_IMAGE}"
PLATFORM="${2:?ERROR: missing PLATFORM}"
CODENAME="${3:?ERROR: missing CODENAME}"
DEB_ARCH="${4:?ERROR: missing DEB_ARCH}"
OUT_DIR="${OUT_DIR:-./build-out}"
APT_REPO_URL="${APT_REPO_URL:-https://packages.helinplatform.com/apt}"
CORE_DIR=".ci/deb/core"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

mkdir -p "$OUT_DIR" "$CORE_DIR"

if [[ -n "${FLEDGE_CORE_DEB:-}" ]]; then
    cp "$FLEDGE_CORE_DEB" "${CORE_DIR}/fledge-core.deb"
else
    index_url="${APT_REPO_URL}/dists/${CODENAME}${APT_SUITE_SUFFIX:-}/main/binary-${DEB_ARCH}/Packages"
    pool_path="$(curl -fsSL "$index_url" | awk '
        BEGIN { RS = ""; FS = "\n" }
        {
            is_core = 0; path = ""
            for (i = 1; i <= NF; i++) {
                if ($i == "Package: fledge") is_core = 1
                if ($i ~ /^Filename: /) path = substr($i, 11)
            }
            if (is_core && path != "") { print path; exit }
        }')"
    if [[ -z "$pool_path" ]]; then
        echo "ERROR: no fledge core package for ${CODENAME}/${DEB_ARCH} in ${index_url}" >&2
        exit 1
    fi
    curl -fsSL "${APT_REPO_URL}/${pool_path}" -o "${CORE_DIR}/fledge-core.deb"
fi

if docker buildx inspect fledge-builder >/dev/null 2>&1; then
    docker buildx use fledge-builder
else
    docker buildx create --name fledge-builder --use
fi

docker buildx build \
    --file .ci/deb/Dockerfile.light \
    --target artifact \
    --output "type=local,dest=${OUT_DIR}" \
    --platform "$PLATFORM" \
    --build-arg BASE_IMAGE="$BASE_IMAGE" \
    --build-arg CORE_DEB="${CORE_DIR}/fledge-core.deb" \
    .

ls -la "$OUT_DIR"
