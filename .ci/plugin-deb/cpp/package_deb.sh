#!/usr/bin/env bash
set -euo pipefail

FLEDGE_INSTALL="${1:?ERROR: missing argument FLEDGE_INSTALL_DIR (e.g. /usr/local/fledge)}"
OUT_DIR="${2:?ERROR: missing argument OUTPUT_DIR for the built .deb}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

DEB_ARCH="$(dpkg --print-architecture)"

arch="$DEB_ARCH"
package_manager=deb
requirements=""
source ./Package

PKG_NAME="fledge-${plugin_type}-${plugin_name}"
PKG_VERSION="$(tr -d '[:space:]' < VERSION)"

PLUGIN_INSTALLED="${FLEDGE_INSTALL}/plugins/${plugin_type}/${plugin_install_dirname}"
if [[ ! -d "$PLUGIN_INSTALLED" ]]; then
    echo "ERROR: built plugin not found at ${PLUGIN_INSTALLED}; run make install first" >&2
    exit 1
fi

STAGE="$(mktemp -d)"
mkdir -p "${STAGE}/usr/local/fledge/plugins/${plugin_type}" "${STAGE}/DEBIAN"
cp -R "$PLUGIN_INSTALLED" "${STAGE}/usr/local/fledge/plugins/${plugin_type}/"

PLUGIN_STAGED="${STAGE}/usr/local/fledge/plugins/${plugin_type}/${plugin_install_dirname}"
BUNDLE_DIR="${STAGE}/usr/local/fledge/lib"
collect_needed() {
    objdump -p "$1" 2>/dev/null | awk '/NEEDED/{print $2}'
}
bundle_from_usr_local_lib() {
    local so needed family
    for so in "$1"/*.so*; do
        [[ -e "$so" ]] || continue
        collect_needed "$so"
    done | sort -u | while read -r needed; do
        family="/usr/local/lib/${needed%%.so*}.so"
        if compgen -G "${family}*" > /dev/null; then
            mkdir -p "$BUNDLE_DIR"
            cp -a ${family}* "$BUNDLE_DIR/"
        fi
    done
}
bundle_from_usr_local_lib "$PLUGIN_STAGED"
if [[ -d "$BUNDLE_DIR" ]]; then
    bundle_from_usr_local_lib "$BUNDLE_DIR"
fi

.ci/deb/generate_control.sh "$DEB_ARCH" > "${STAGE}/DEBIAN/control"

mkdir -p "$OUT_DIR"
dpkg-deb --build --root-owner-group "$STAGE" "${OUT_DIR}/${PKG_NAME}_${PKG_VERSION}_${DEB_ARCH}.deb"

ls -la "$OUT_DIR"
