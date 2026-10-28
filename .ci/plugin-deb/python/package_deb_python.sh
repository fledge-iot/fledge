#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:?ERROR: missing argument OUTPUT_DIR for the built .deb}"
CONSTRAINTS="${2:?ERROR: missing argument CONSTRAINTS_FILE (shared python pin set)}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

arch=all
package_manager=deb
requirements=""
source ./Package

PKG_NAME="fledge-${plugin_type}-${plugin_name//_/-}"
VERSION_FILE="VERSION.${plugin_type}.${plugin_name}"
if [[ ! -f "$VERSION_FILE" ]]; then
    echo "ERROR: ${VERSION_FILE} not found" >&2
    exit 1
fi
PKG_VERSION="$(sed -n "s/^fledge_${plugin_type}_${plugin_name}_version=//p" "$VERSION_FILE" | tr -d '[:space:]')"
if [[ -z "$PKG_VERSION" ]]; then
    PKG_VERSION="$(sed -n 's/^fledge_.*_version=//p' "$VERSION_FILE" | head -1 | tr -d '[:space:]')"
fi
FLEDGE_CONSTRAINT="$(sed -n 's/^fledge_version//p' "$VERSION_FILE" | head -1 | tr -d '[:space:]')"
FLEDGE_OP="$(printf '%s' "$FLEDGE_CONSTRAINT" | sed 's/[0-9].*$//')"
FLEDGE_VER="$(printf '%s' "$FLEDGE_CONSTRAINT" | sed 's/^[^0-9]*//')"
PKG_DESCRIPTION="$(head -1 Description)"

PLUGIN_SRC="python/fledge/plugins/${plugin_type}/${plugin_install_dirname}"
if [[ ! -d "$PLUGIN_SRC" ]]; then
    echo "ERROR: plugin source not found at ${PLUGIN_SRC}" >&2
    exit 1
fi

PINNED="$(mktemp)"
REQ_FILE="python/requirements-${plugin_name}.txt"
if [[ -f "$REQ_FILE" ]]; then
    RESOLVE_ENV="$(mktemp -d)"
    python3 -m venv "$RESOLVE_ENV"
    "$RESOLVE_ENV/bin/pip" install --quiet --upgrade pip
    "$RESOLVE_ENV/bin/pip" install --quiet -r "$REQ_FILE" -c "$CONSTRAINTS"
    "$RESOLVE_ENV/bin/pip" freeze | grep -viE '^pkg[-_]resources==' > "$PINNED"
    rm -rf "$RESOLVE_ENV"
fi

STAGE="$(mktemp -d)"
INSTALL_DIR="usr/local/fledge/python/fledge/plugins/${plugin_type}/${plugin_install_dirname}"
mkdir -p "${STAGE}/${INSTALL_DIR}" "${STAGE}/DEBIAN"
cp -R "${PLUGIN_SRC}/." "${STAGE}/${INSTALL_DIR}/"
cp "$PINNED" "${STAGE}/${INSTALL_DIR}/requirements-pinned.txt"

DEPENDS="fledge"
if [[ -n "$FLEDGE_OP" && -n "$FLEDGE_VER" ]]; then
    DEPENDS="fledge (${FLEDGE_OP} ${FLEDGE_VER})"
fi

cat > "${STAGE}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${PKG_VERSION}
Architecture: all
Maintainer: Helin Data <support@helindata.com>
Depends: ${DEPENDS}
Description: ${PKG_DESCRIPTION}
EOF

cat > "${STAGE}/DEBIAN/postinst" <<EOF
#!/bin/sh
set -e
REQS="/${INSTALL_DIR}/requirements-pinned.txt"
if [ -s "\$REQS" ]; then
    if python3 -m pip install --help 2>/dev/null | grep -q break-system-packages; then
        python3 -m pip install --break-system-packages -r "\$REQS"
    else
        python3 -m pip install -r "\$REQS"
    fi
fi
EOF
chmod 755 "${STAGE}/DEBIAN/postinst"

mkdir -p "$OUT_DIR"
dpkg-deb --build --root-owner-group "$STAGE" "${OUT_DIR}/${PKG_NAME}_${PKG_VERSION}_all.deb"

ls -la "$OUT_DIR"
