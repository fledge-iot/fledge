# syntax=docker/dockerfile:1.6
#
# Local runtime image: same steps as .ci/image/Dockerfile (slim target), but the
# .deb comes straight from the builder stage instead of a file copied into the context.
# Used by .ci/local/docker-compose.yml; build context is .ci/image/.
ARG BASE_IMAGE=ubuntu:22.04

FROM debbuilder AS deb

FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    FLEDGE_ROOT=/usr/local/fledge \
    FLEDGE_DATA=/usr/local/fledge/data \
    FLEDGE_STORAGE_GRACE=90 \
    PATH=/usr/local/fledge/bin:$PATH \
    PYTHONPATH=/usr/local/fledge/python \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN printf '%s\n' '#!/bin/sh' 'echo "[systemctl stub] $*" >&2' 'exit 0' > /usr/bin/systemctl \
 && chmod +x /usr/bin/systemctl

# Debian 11 (bullseye) is EOL: its security pool was removed from deb.debian.org and now lives only on
# archive.debian.org, so `apt-get install` 404s on the -security packages. No-op on every other base image.
RUN . /etc/os-release \
 && if [ "${VERSION_CODENAME}" = bullseye ]; then \
      sed -i 's|http://deb.debian.org/debian-security|http://archive.debian.org/debian-security|' /etc/apt/sources.list; \
    fi

COPY --from=deb /artifacts/fledge_*.deb /tmp/fledge.deb
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl rsyslog build-essential python3-dev \
 && (dpkg -i /tmp/fledge.deb || apt-get install -y --no-install-recommends -f) \
 && apt-get purge -y --auto-remove build-essential python3-dev \
 && rm -rf /root/.cache/pip /tmp/fledge.deb /var/lib/apt/lists/*

COPY rsyslog.conf /etc/rsyslog.conf
COPY rsyslog-rotate.sh /usr/local/bin/fledge-log-rotate
COPY entrypoint.sh /usr/local/bin/fledge-entrypoint
RUN chmod +x /usr/local/bin/fledge-log-rotate /usr/local/bin/fledge-entrypoint

EXPOSE 8081
VOLUME ["/usr/local/fledge/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://localhost:8081/fledge/ping || exit 1

ENTRYPOINT ["/usr/local/bin/fledge-entrypoint"]
