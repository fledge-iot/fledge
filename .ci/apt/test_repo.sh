#!/usr/bin/env bash
# Smoke-test an apt repository by installing fledge inside a clean container.

set -euo pipefail

APT_REPO_URL="${1:?usage: test_repo.sh <apt-repo-url> [deb-arch]}"
ARCH="${2:-amd64}"
CODENAME="${CODENAME:-stable}"
COMPONENT="${COMPONENT:-main}"
BASE_IMAGE="${BASE_IMAGE:-ubuntu:22.04}"

case "${ARCH}" in
    amd64) PLATFORM="linux/amd64" ;;
    arm64) PLATFORM="linux/arm64" ;;
    armhf) PLATFORM="linux/arm/v7" ;;
    *) echo "ERROR: unsupported architecture: ${ARCH}" >&2; exit 1 ;;
esac

echo ">> Testing apt repository ${APT_REPO_URL} (${CODENAME} ${COMPONENT}, ${ARCH})"

# If KEYRING_URL is set, verify signatures against that pinned keyring
# (deb [signed-by=...]); otherwise fall back to [trusted=yes] for the local
# unsigned build-mechanics smoke.
docker run --rm \
    --platform "${PLATFORM}" \
    --add-host=host.docker.internal:host-gateway \
    -e APT_REPO_URL="${APT_REPO_URL}" \
    -e CODENAME="${CODENAME}" \
    -e COMPONENT="${COMPONENT}" \
    -e KEYRING_URL="${KEYRING_URL:-}" \
    "${BASE_IMAGE}" bash -euxo pipefail -c '
        export DEBIAN_FRONTEND=noninteractive
        # bullseye is EOL: its security pool only exists on archive.debian.org now
        . /etc/os-release
        if [ "${VERSION_CODENAME}" = bullseye ]; then
            sed -i "s|http://deb.debian.org/debian-security|http://archive.debian.org/debian-security|" /etc/apt/sources.list
        fi
        apt-get update
        apt-get install -y --no-install-recommends ca-certificates curl sudo build-essential python3-dev rsyslog

        printf "%s\n" "#!/bin/sh" "echo \"[systemctl stub] \$*\" >&2" "exit 0" > /usr/bin/systemctl
        chmod +x /usr/bin/systemctl

        # Fledge logs through syslog, so something must be listening on /dev/log
        touch /var/log/syslog
        rm -f /run/rsyslogd.pid
        rsyslogd

        if [ -n "${KEYRING_URL}" ]; then
            curl -fsSL "${KEYRING_URL}" -o /usr/share/keyrings/fledge.gpg
            echo "deb [signed-by=/usr/share/keyrings/fledge.gpg] ${APT_REPO_URL} ${CODENAME} ${COMPONENT}" > /etc/apt/sources.list.d/fledge.list
        else
            echo "deb [trusted=yes] ${APT_REPO_URL} ${CODENAME} ${COMPONENT}" > /etc/apt/sources.list.d/fledge.list
        fi
        apt-get update
        apt-cache policy fledge
        apt-get install -y fledge
        dpkg -l fledge

        # The package starts Fledge itself when it detects a container
        ok=0
        for i in $(seq 1 60); do
            if curl -fsS http://localhost:8081/fledge/ping; then
                ok=1
                break
            fi
            sleep 2
        done
        if [ "${ok}" -ne 1 ]; then
            echo "ERROR: Fledge did not answer /fledge/ping within 120s" >&2
            tail -n 100 /usr/local/fledge/data/core.err 2>/dev/null || true
            tail -n 100 /var/log/syslog 2>/dev/null || true
            exit 1
        fi
        /usr/local/fledge/bin/fledge stop
    '
