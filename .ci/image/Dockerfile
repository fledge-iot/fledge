# Official fledge runtime image. Built from the same .deb we publish to the
# apt repository so the Docker artifact and the apt package are byte-identical.
# We publish two variants: a "slim" image with only the core runtime, and a "full" image with supporting plugins.
ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS slim

ARG FLEDGE_VERSION
ARG FLEDGE_CODENAME

LABEL org.opencontainers.image.title="fledge" \
      org.opencontainers.image.description="Fledge IIoT edge runtime — ${FLEDGE_VERSION} on ${FLEDGE_CODENAME}" \
      org.opencontainers.image.source="https://github.com/fledge-iot/fledge" \
      org.opencontainers.image.vendor="Helin Data B.V." \
      org.opencontainers.image.version="${FLEDGE_VERSION}"

ENV DEBIAN_FRONTEND=noninteractive \
    FLEDGE_ROOT=/usr/local/fledge \
    FLEDGE_DATA=/usr/local/fledge/data \
    FLEDGE_STORAGE_GRACE=90 \
    PATH=/usr/local/fledge/bin:$PATH \
    PYTHONPATH=/usr/local/fledge/python \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# systemctl stub — fledge's .deb postinst calls it during install; harmless to no-op. #TODO What is this about?
RUN printf '%s\n' '#!/bin/sh' 'echo "[systemctl stub] $*" >&2' 'exit 0' > /usr/bin/systemctl \
 && chmod +x /usr/bin/systemctl

# Debian 11 (bullseye) is EOL: its security pool was removed from deb.debian.org and now lives only on
# archive.debian.org, so `apt-get install` 404s on the -security packages. No-op on every other base image.
RUN . /etc/os-release \
 && if [ "${VERSION_CODENAME}" = bullseye ]; then \
      sed -i 's|http://deb.debian.org/debian-security|http://archive.debian.org/debian-security|' /etc/apt/sources.list; \
    fi

# Install fledge from the .deb that the build job produced.
# build-essential + python3-dev are build-only helpers for fledge's postinst
# pip install, which can compile wheels from source.
# rsyslog gives fledge's logger() calls somewhere to land so the entrypoint can
# tail them out to `docker logs`.
COPY fledge.deb /tmp/fledge.deb
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl rsyslog build-essential python3-dev \
 && (dpkg -i /tmp/fledge.deb || apt-get install -y --no-install-recommends -f) \
 && apt-get purge -y --auto-remove build-essential python3-dev \
 && rm -rf /root/.cache/pip /tmp/fledge.deb \
 && rm -rf /var/lib/apt/lists/*

COPY rsyslog.conf /etc/rsyslog.conf
COPY rsyslog-rotate.sh /usr/local/bin/fledge-log-rotate
COPY entrypoint.sh /usr/local/bin/fledge-entrypoint
RUN chmod +x /usr/local/bin/fledge-log-rotate /usr/local/bin/fledge-entrypoint

EXPOSE 8081
VOLUME ["/usr/local/fledge/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://localhost:8081/fledge/ping || exit 1

ENTRYPOINT ["/usr/local/bin/fledge-entrypoint"]

# Default ("batteries included") variant. dry runs build the slim target only.
FROM slim AS full

ARG FLEDGE_CODENAME
ARG APT_REPO_URL=https://packages.helinplatform.com/apt

COPY plugins.txt /tmp/plugins.txt
RUN curl -fsSL "${APT_REPO_URL}/fledge.gpg" -o /usr/share/keyrings/fledge.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/fledge.gpg] ${APT_REPO_URL} ${FLEDGE_CODENAME} main" \
      > /etc/apt/sources.list.d/fledge.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends build-essential python3-dev \
 && xargs -a /tmp/plugins.txt apt-get install -y --no-install-recommends \
 && apt-get purge -y --auto-remove build-essential python3-dev \
 && rm -rf /var/lib/apt/lists/* /root/.cache/pip /tmp/plugins.txt
