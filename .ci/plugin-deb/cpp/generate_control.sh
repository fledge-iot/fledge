#!/usr/bin/env bash
set -euo pipefail

DEB_ARCH="${1:?ERROR: missing argument DEB_ARCH (amd64, arm64, armhf)}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

arch="$DEB_ARCH"
package_manager=deb
requirements=""
source ./Package

PKG_NAME="fledge-${plugin_type}-${plugin_name}"
PKG_VERSION="$(tr -d '[:space:]' < VERSION)"
PKG_DESCRIPTION="$(head -1 Description)"

FLEDGE_CONSTRAINT="$(tr -d '[:space:]' < fledge.version)"
FLEDGE_OP="$(printf '%s' "$FLEDGE_CONSTRAINT" | sed 's/^fledge_version//; s/[0-9].*$//')"
FLEDGE_VER="$(printf '%s' "$FLEDGE_CONSTRAINT" | sed 's/^[^0-9]*//')"

DEPENDS=""
IFS=',' read -ra REQS <<< "$requirements"
for req in "${REQS[@]}"; do
    req="$(printf '%s' "$req" | tr -d '[:space:]')"
    [[ -z "$req" ]] && continue
    [[ "$req" == fledge-* ]] && continue
    if [[ "$req" == "fledge" && -n "$FLEDGE_OP" && -n "$FLEDGE_VER" ]]; then
        entry="fledge (${FLEDGE_OP} ${FLEDGE_VER})"
    else
        entry="$req"
    fi
    if [[ -z "$DEPENDS" ]]; then
        DEPENDS="$entry"
    else
        DEPENDS="${DEPENDS}, ${entry}"
    fi
done

cat <<EOF
Package: ${PKG_NAME}
Version: ${PKG_VERSION}
Architecture: ${DEB_ARCH}
Maintainer: Helin Data <support@helindata.com>
Depends: ${DEPENDS}
Description: ${PKG_DESCRIPTION}
EOF
