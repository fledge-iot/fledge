#!/usr/bin/env bash
# Build a fledge_<version>_<deb-arch>.deb from an installed Fledge tree.
#
# Usage:
#   scripts/package/debian/build_deb.sh \
#     --fledge-root /usr/local/fledge \
#     --output /artifacts
#
# Optional:
#   --version 3.1.0       defaults to <fledge-root>/VERSION
#   --arch amd64          defaults to dpkg --print-architecture
#   --build-root /tmp/pkg defaults to a temporary directory

set -euo pipefail

VERSION=""
ARCH=""
FLEDGE_ROOT="/usr/local/fledge"
OUTPUT=""
BUILD_ROOT=""

usage() {
  sed -n '1,/^$/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-1}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)     VERSION="$2";     shift 2 ;;
    --arch)        ARCH="$2";        shift 2 ;;
    --fledge-root) FLEDGE_ROOT="$2"; shift 2 ;;
    --output)      OUTPUT="$2";      shift 2 ;;
    --build-root)  BUILD_ROOT="$2";  shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown argument: $1" >&2; usage 1 ;;
  esac
done

[[ -d "${FLEDGE_ROOT}" ]] || {
  echo "ERROR: Fledge root missing at ${FLEDGE_ROOT}" >&2
  echo "       did you run \`make install\` first?" >&2
  exit 1
}
[[ -n "${OUTPUT}"  ]] || { echo "ERROR: --output is required"  >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEB_TEMPLATE_DIR="${SCRIPT_DIR}/deb"
CONTROL_TEMPLATE="${DEB_TEMPLATE_DIR}/control.in"

[[ -f "${CONTROL_TEMPLATE}" ]] || {
  echo "ERROR: control template missing at ${CONTROL_TEMPLATE}" >&2
  exit 1
}

if [[ -z "${VERSION}" ]]; then
  VERSION="$(grep '^fledge_version=' "${FLEDGE_ROOT}/VERSION" | head -1 | cut -d= -f2 | tr -d '[:space:]')"
fi
[[ -n "${VERSION}" ]] || { echo "ERROR: unable to determine Fledge version" >&2; exit 1; }

if [[ -z "${ARCH}" ]]; then
  ARCH="$(dpkg --print-architecture)"
fi

case "${ARCH}" in
  x86_64) ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  armv7l|armv6l) ARCH="armhf" ;;
esac

case "${ARCH}" in
  amd64|arm64) EXTRA_DEPENDS="" ;;
  armhf) EXTRA_DEPENDS=",cpulimit" ;;
  *) echo "ERROR: unsupported Debian architecture: ${ARCH}" >&2; exit 1 ;;
esac

BOOST_VERSION="$(dpkg-query -W -f='${Version}' libboost-dev 2>/dev/null | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+' || true)"
[[ -n "${BOOST_VERSION}" ]] || {
  echo "ERROR: Boost version not found. Is libboost-dev installed?" >&2
  exit 1
}

PYTHON_ABI="$(python3 -c 'import sys; print("{}.{}".format(sys.version_info[0], sys.version_info[1]))' 2>/dev/null || true)"
[[ -n "${PYTHON_ABI}" ]] || {
  echo "ERROR: Python ABI version not found. Is python3 installed?" >&2
  exit 1
}

mkdir -p "${OUTPUT}"

if [[ -z "${BUILD_ROOT}" ]]; then
  BUILD_ROOT="$(mktemp -d)"
  trap 'rm -rf "${BUILD_ROOT}"' EXIT
else
  mkdir -p "${BUILD_ROOT}"
fi

PKG_NAME="fledge_${VERSION}_${ARCH}"
PKGROOT="${BUILD_ROOT}/${PKG_NAME}"
rm -rf "${PKGROOT}"
mkdir -p "${PKGROOT}/usr/local/fledge" "${PKGROOT}/DEBIAN"

# Debian maintainer scripts mirror the upstream fledge-pkg package behavior.
cp -a "${DEB_TEMPLATE_DIR}/DEBIAN/." "${PKGROOT}/DEBIAN/"
find "${PKGROOT}/DEBIAN" -type d -exec chmod 0755 {} +
chmod 0755 "${PKGROOT}/DEBIAN/"*

# Copy the installed tree into the package root.
cp -a "${FLEDGE_ROOT}/." "${PKGROOT}/usr/local/fledge/"

# Render DEBIAN/control.
sed \
  -e "s/@VERSION@/${VERSION}/g" \
  -e "s/@ARCH@/${ARCH}/g" \
  -e "s/@BOOST_VER@/${BOOST_VERSION}/g" \
  -e "s/@PYTHON_ABI@/${PYTHON_ABI}/g" \
  -e "s/@EXTRA_DEPENDS@/${EXTRA_DEPENDS}/g" \
  "${CONTROL_TEMPLATE}" > "${PKGROOT}/DEBIAN/control"
chmod 0644 "${PKGROOT}/DEBIAN/control"

# Match fledge-pkg: ship data as data.new and let postinst merge/preserve the
# user's existing data directory during upgrades.
if [[ -d "${PKGROOT}/usr/local/fledge/data" ]]; then
  mv "${PKGROOT}/usr/local/fledge/data" "${PKGROOT}/usr/local/fledge/data.new"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/backup"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/core.err"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/etc/certs/"*
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/fledge.db"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/logs"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/scripts"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/support"
  rm -rf "${PKGROOT}/usr/local/fledge/data.new/var"
fi

DEB="${OUTPUT}/${PKG_NAME}.deb"
dpkg-deb --build --root-owner-group "${PKGROOT}" "${DEB}"

echo "Built: ${DEB}"
dpkg-deb --info "${DEB}"
