# syntax=docker/dockerfile:1.6
#
# Build Fledge core .deb for a single (distro, arch) tuple.
#
# Usage (from repo root):
#   docker buildx build \
#     --file .ci/build/Dockerfile \
#     --target artifact \
#     --output type=local,dest=./build-out \
#     --platform linux/amd64 \
#     --build-arg BASE_IMAGE=ubuntu:22.04 \
#     .
#
# Output: ./build-out/fledge_<version>_<deb-arch>.deb
#
# Rebuilds are fast after the first run because apt-install and sqlite3 compile
# are cached. Editing C++ source invalidates only the make-install layer.

ARG BASE_IMAGE=ubuntu:22.04@sha256:3b06811b2afd352be909dd088a004166d665dc76d38b13eada33522a9d915c6f

##### Stage: deps — install build toolchain + runtime deps that requirements.sh needs
FROM ${BASE_IMAGE} AS deps
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

# Debian 11 (bullseye) is EOL: its security pool was removed from deb.debian.org and now lives only on
# archive.debian.org, so `apt-get install` 404s on the -security packages. No-op on every other base image.
RUN . /etc/os-release \
 && if [ "${VERSION_CODENAME}" = bullseye ]; then \
      sed -i 's|http://deb.debian.org/debian-security|http://archive.debian.org/debian-security|' /etc/apt/sources.list; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo ca-certificates curl wget git unzip dos2unix \
        build-essential cmake g++ make autoconf automake libtool pkg-config \
        uuid-dev libssl-dev libz-dev libbz2-dev libreadline-dev liblzma-dev libffi-dev \
        libboost-dev libboost-system-dev libboost-thread-dev \
        libpq-dev libcurl4-openssl-dev \
        python3 python3-dev python3-pip python3-setuptools python3-numpy python3-distutils-extra \
        sqlite3 \
        krb5-user \
        avahi-daemon \
        dpkg-dev
# NB: we deliberately do NOT `rm -rf /var/lib/apt/lists/*` here — requirements.sh
# uses `apt search` to detect the local Python-dev package name, which silently
# returns empty with no cache. The cache size doesn't matter: the final
# `artifact` stage is `FROM scratch` and contains only the .deb.

##### Stage: builder — compile Fledge and package the installed tree
FROM deps AS builder

WORKDIR /build
# Full repo (with .dockerignore filtering noise) is the build context.
COPY . /build/fledge

# Git on Windows strips exec bits AND rewrites LF → CRLF. dos2unix is smart
# enough to skip binary files automatically, so run it across the whole tree
# rather than trying to enumerate every shebang-bearing script. Then make sure
# the scripts we call directly are executable.
RUN find /build/fledge -type f -print0 \
        | xargs -0 -r dos2unix -q 2>/dev/null || true \
    && chmod +x /build/fledge/requirements.sh \
        /build/fledge/scripts/package/debian/build_deb.sh \
        /build/fledge/scripts/package/debian/deb/DEBIAN/*

# requirements.sh expects to be run as root (uses sudo internally; in the
# container we are already root, sudo is installed and works as a no-op).
WORKDIR /build/fledge
RUN bash ./requirements.sh

# make install populates /usr/local/fledge, which make_deb then packages.
RUN make -j"$(nproc)" install
ENV FLEDGE_ROOT=/usr/local/fledge

# Package the installed tree with the in-repo Debian package templates.
WORKDIR /build/fledge
ARG DEB_VERSION=
RUN scripts/package/debian/build_deb.sh \
    --fledge-root "${FLEDGE_ROOT}" \
    ${DEB_VERSION:+--version "${DEB_VERSION}"} \
    --output /artifacts

# Collect the artifact at a known path for the final stage to copy out.
RUN ls -la /artifacts

##### Stage: artifact — scratch image holding only the .deb, so
##### `docker buildx build --output type=local,dest=./build-out` writes just the .deb.
FROM scratch AS artifact
COPY --from=builder /artifacts/ /
