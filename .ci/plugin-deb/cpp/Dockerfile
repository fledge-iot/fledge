ARG BASE_IMAGE=ubuntu:22.04

FROM ${BASE_IMAGE} AS deps
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

RUN if grep -qs bullseye /etc/apt/sources.list; then \
        sed -i -e 's|deb.debian.org/debian-security|archive.debian.org/debian-security|g' \
               -e 's|deb.debian.org/debian|archive.debian.org/debian|g' \
               -e '/bullseye-updates/d' /etc/apt/sources.list \
        && echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99archive; \
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

FROM deps AS builder

WORKDIR /build
COPY . /build/plugin

RUN find /build/plugin -type f -print0 \
        | xargs -0 -r dos2unix -q 2>/dev/null || true \
    && chmod +x /build/plugin/fledge/requirements.sh \
        /build/plugin/.ci/deb/generate_control.sh \
        /build/plugin/.ci/deb/package_deb.sh

WORKDIR /build/plugin/fledge
RUN bash ./requirements.sh
RUN make -j"$(nproc)"

WORKDIR /build/plugin
RUN if [ -f requirements.sh ]; then bash ./requirements.sh; fi

ENV FLEDGE_INSTALL=/usr/local/fledge
ENV LD_LIBRARY_PATH=/usr/local/fledge/lib

WORKDIR /build/plugin
RUN mkdir -p build && cd build \
    && cmake -DFLEDGE_SRC=/build/plugin/fledge -DFLEDGE_INSTALL="${FLEDGE_INSTALL}" .. \
    && make -j"$(nproc)" \
    && make install

RUN .ci/deb/package_deb.sh "${FLEDGE_INSTALL}" /artifacts

FROM scratch AS artifact
COPY --from=builder /artifacts/ /
