#!/usr/bin/env bash
# Build apt repository metadata for one codename from .deb artifacts.
#
# Layout produced (cumulative — safe to re-invoke with a different CODENAME
# against the same REPO_DIR; codenames coexist in one tree):
#   pool/${CODENAME}/${COMPONENT}/<initial>/<package>/<deb files>
#   dists/${CODENAME}/${COMPONENT}/binary-${arch}/Packages{,.gz}
#   dists/${CODENAME}/${COMPONENT}/binary-${arch}/Release
#   dists/${CODENAME}/Release
#
# Usage: build_repo.sh INPUT_DIR REPO_DIR
# Env:
#   CODENAME  (required, e.g. bullseye, bookworm)
#   COMPONENT (default: main)
#   ARCHES    (default: "amd64 arm64 armhf", space-separated)
#   ORIGIN    (default: Helin)
#   LABEL     (default: Fledge)

set -euo pipefail

INPUT_DIR="${1:-./build-out}"
REPO_DIR="${2:-./apt-repo-out}"
CODENAME="${CODENAME:?CODENAME env var is required (e.g. bullseye, bookworm)}"
COMPONENT="${COMPONENT:-main}"
ARCHES="${ARCHES:-amd64 arm64 armhf}"
ORIGIN="${ORIGIN:-Helin}"
LABEL="${LABEL:-Fledge}"

NOT_AUTOMATIC="${NOT_AUTOMATIC:-}"
RELEASE_FLAGS=()
if [[ -n "${NOT_AUTOMATIC}" ]]; then
    RELEASE_FLAGS=(-o "APT::FTPArchive::Release::NotAutomatic=yes" -o "APT::FTPArchive::Release::ButAutomaticUpgrades=yes")
fi

POOL_ROOT="${REPO_DIR}/pool/${CODENAME}/${COMPONENT}"

shopt -s nullglob globstar
DEBS=("${INPUT_DIR}"/**/*.deb)
if [[ ${#DEBS[@]} -eq 0 ]]; then
    echo "ERROR: no .deb artifacts found under ${INPUT_DIR}" >&2
    exit 1
fi

for deb in "${DEBS[@]}"; do
    pkg="$(dpkg-deb --field "${deb}" Package)"
    ver="$(dpkg-deb --field "${deb}" Version)"
    pool_dir="${POOL_ROOT}/${pkg:0:1}/${pkg}"
    dest="${pool_dir}/$(basename "${deb}")"
    if [[ -f "${dest}" ]] && ! cmp -s "${deb}" "${dest}"; then
        echo "ERROR: ${dest#"${REPO_DIR}/"} is already published with different content; bump ${pkg} past ${ver} rather than republishing that version" >&2
        exit 1
    fi
    mkdir -p "${pool_dir}"
    cp -f "${deb}" "${dest}"
done

for arch in ${ARCHES}; do
    arch_dir="${REPO_DIR}/dists/${CODENAME}/${COMPONENT}/binary-${arch}"
    mkdir -p "${arch_dir}"
    (
        cd "${REPO_DIR}"
        dpkg-scanpackages --multiversion --arch "${arch}" \
            "pool/${CODENAME}/${COMPONENT}" \
            > "dists/${CODENAME}/${COMPONENT}/binary-${arch}/Packages"
    )
    gzip -k -f "${arch_dir}/Packages"
    cat > "${arch_dir}/Release" <<EOF
Archive: ${CODENAME}
Component: ${COMPONENT}
Origin: ${ORIGIN}
Label: ${LABEL}
Architecture: ${arch}
EOF
done

apt-ftparchive \
    ${RELEASE_FLAGS[@]+"${RELEASE_FLAGS[@]}"} \
    -o "APT::FTPArchive::Release::Origin=${ORIGIN}" \
    -o "APT::FTPArchive::Release::Label=${LABEL}" \
    -o "APT::FTPArchive::Release::Suite=${CODENAME}" \
    -o "APT::FTPArchive::Release::Codename=${CODENAME}" \
    -o "APT::FTPArchive::Release::Architectures=${ARCHES}" \
    -o "APT::FTPArchive::Release::Components=${COMPONENT}" \
    release "${REPO_DIR}/dists/${CODENAME}" > "${REPO_DIR}/dists/${CODENAME}/Release"

echo "Apt repository updated for ${CODENAME} at ${REPO_DIR}"
find "${REPO_DIR}/dists/${CODENAME}" -maxdepth 4 -type f | sort
