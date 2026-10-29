#!/usr/bin/env bash
set -euo pipefail

VERSION_FILE="${1:?usage: resolve_version.sh VERSION_FILE TAG [KEY]}"
TAG="${2-}"
KEY="${3:-}"

version="$(grep '^fledge_version=' "${VERSION_FILE}" | head -1 | cut -d= -f2 | tr -d '[:space:]')"
if [[ -z "${version}" ]]; then
    echo "ERROR: unable to determine fledge_version from ${VERSION_FILE}" >&2
    exit 1
fi

rc=""
if [[ -n "${TAG}" ]]; then
    stripped="${TAG#v}"
    if [[ "${stripped}" == "${version}" ]]; then
        rc=""
    elif [[ "${stripped}" =~ ^${version//./\\.}-rc\.([1-9][0-9]*)$ ]]; then
        rc="${BASH_REMATCH[1]}"
    else
        echo "ERROR: tag '${TAG}' does not match VERSION file fledge_version='${version}' (expected v${version} or v${version}-rc.<n>)" >&2
        exit 1
    fi
fi

if [[ -n "${rc}" ]]; then
    deb_version="${version}~rc.${rc}"
    image_version="${version}-rc.${rc}"
    suite_suffix="-rc"
else
    deb_version="${version}"
    image_version="${version}"
    suite_suffix=""
fi

if [[ -n "${KEY}" ]]; then
    case "${KEY}" in
        version) echo "${version}" ;;
        rc) echo "${rc}" ;;
        deb_version) echo "${deb_version}" ;;
        image_version) echo "${image_version}" ;;
        suite_suffix) echo "${suite_suffix}" ;;
        *) echo "ERROR: unknown key '${KEY}'" >&2; exit 1 ;;
    esac
    exit 0
fi

echo "version=${version}"
echo "rc=${rc}"
echo "deb_version=${deb_version}"
echo "image_version=${image_version}"
echo "suite_suffix=${suite_suffix}"
