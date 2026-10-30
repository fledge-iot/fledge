#!/usr/bin/env bash
# Local dev build: produce the .deb, then build the Docker image from it.
# Mirrors what publish-apt-azure.yml does in CI, but on your laptop.
#
# Usage:
#   .ci/image/build.sh                                        # bookworm/amd64 (defaults)
#   .ci/image/build.sh debian:bullseye-slim                   # bullseye/amd64
#   .ci/image/build.sh debian:bookworm-slim linux/arm64       # bookworm/arm64 (needs QEMU)
#   .ci/image/build.sh ubuntu:24.04 linux/amd64 noble         # explicit codename
set -euo pipefail

BASE_IMAGE="${1:-debian:bookworm-slim}"
PLATFORM="${2:-linux/amd64}"

# Derive codename from base image if not given. Crude but covers our matrix.
if [[ -n "${3:-}" ]]; then
    CODENAME="$3"
else
    case "${BASE_IMAGE}" in
        *bullseye*) CODENAME="bullseye" ;;
        *bookworm*) CODENAME="bookworm" ;;
        ubuntu:22.04*) CODENAME="jammy" ;;
        ubuntu:24.04*) CODENAME="noble" ;;
        *) echo "ERROR: can't derive codename from ${BASE_IMAGE}; pass as arg 3" >&2; exit 1 ;;
    esac
fi

case "${PLATFORM}" in
    linux/amd64) DEB_ARCH="amd64" ;;
    linux/arm64) DEB_ARCH="arm64" ;;
    linux/arm/v7) DEB_ARCH="armhf" ;;
    *) echo "ERROR: unsupported platform ${PLATFORM}" >&2; exit 1 ;;
esac

VERSION="$(grep '^fledge_version=' VERSION | head -1 | cut -d= -f2 | tr -d '[:space:]')"
if [[ -z "${VERSION}" ]]; then
    echo "ERROR: unable to determine fledge_version from VERSION" >&2; exit 1
fi

IMAGE_TAG="${IMAGE_TAG:-fledge:dev-${CODENAME}-${DEB_ARCH}}"
BUILD_OUT_DIR="${OUT_DIR:-./build-out/image-${CODENAME}-${DEB_ARCH}}"

echo ">> Building .deb for ${CODENAME}/${DEB_ARCH} (base=${BASE_IMAGE}, platform=${PLATFORM})"
OUT_DIR="${BUILD_OUT_DIR}" .ci/build/build.sh "${BASE_IMAGE}" "${PLATFORM}"

# Copy the freshly-built .deb into the image build context with a predictable name.
DEB="${BUILD_OUT_DIR}/fledge_${VERSION}_${DEB_ARCH}.deb"
if [[ ! -f "${DEB}" ]]; then
    echo "ERROR: expected .deb not found at ${DEB}" >&2; exit 1
fi
cp -v "${DEB}" .ci/image/fledge.deb
trap 'rm -f .ci/image/fledge.deb' EXIT

echo ">> Building Docker image ${IMAGE_TAG}"
docker buildx build \
    --platform "${PLATFORM}" \
    --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
    --build-arg "FLEDGE_VERSION=${VERSION}" \
    --build-arg "FLEDGE_CODENAME=${CODENAME}" \
    --load \
    -t "${IMAGE_TAG}" \
    -f .ci/image/Dockerfile \
    .ci/image

echo ""
echo "Built: ${IMAGE_TAG}"
echo ""
echo "Try it:"
echo "    docker run --rm -d -p 8081:8081 --name fledge-dev ${IMAGE_TAG}"
echo "    curl -fsS http://localhost:8081/fledge/ping"
echo "    docker stop fledge-dev"
