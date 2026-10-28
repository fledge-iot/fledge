ARG BASE_IMAGE=ubuntu:22.04

FROM ${BASE_IMAGE} AS builder
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 python3-pip python3-venv \
        dpkg-dev

WORKDIR /build/plugin
COPY . /build/plugin

RUN chmod +x .ci/deb/package_deb_python.sh \
    && .ci/deb/package_deb_python.sh /artifacts .ci/deb/python-constraints.txt

FROM scratch AS artifact
COPY --from=builder /artifacts/ /
