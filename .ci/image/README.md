# `.ci/image/` — official fledge container image

`Dockerfile` builds two targets from the same `.deb` we publish to the apt
repository: `slim` (core runtime only) and `full` (core plus every plugin in
`plugins.txt`, installed from the signed apt repo). `entrypoint.sh` runs the
container. `rsyslog.conf` and `rsyslog-rotate.sh` decide where logs go.

## Which plugins the full image ships

`plugins.txt` is the authoritative list and the only place to change it. It holds
28 entries, each pinned to an exact package version, and the `full` stage installs
exactly those from the signed apt repository. An entry can end with `!<codename>`
(one per codename) to skip it on a distribution the plugin is not built for; for
example, omfhint is marked `!bullseye`:

- 15 filters: asset, change, delta, expression, fft, log, metadata, omfhint,
  python35, rate, rename, replace, rms, scale, threshold
- 9 south: dnp3, http-south, modbus, mqtt-readings, mqtt-sparkplug, opcua,
  s2opcua, s7-python, sinusoid
- 4 north: azure-iot, httpc, iec104, kafka

Everything is `3.1.0` except `fledge-north-iec104`, which is `1.9.2` because that
is the last version upstream released.

A plugin can only be listed here once it is published to the apt repository, so
adding one means onboarding its repository to the `.deb` build and publish
workflow first. Deliberately absent today:

- `fledge-south-iec104` — the upstream source is 1.9.2 and no longer compiles
  against 3.1 headers. The maintained 2.0.0 lives in the separate `fledge-power`
  GitHub organisation.
- `fledge-north-http`, the python north HTTP plugin. It has no `build-deb.yml`
  and is not onboarded. Its C++ sibling `fledge-north-httpc` ships instead.

The two HTTP plugins carry no compression. Compressed HTTP exists only in
Helin's `POLARIS-North-HTTP-C-Compress` (`helinhttpc`, libdeflate) and
`POLARIS-South-HTTP-Compress` (zlib, `Content-Encoding: deflate, base64`), which
are a matched pair by wire format and are not part of this image.

## The HTTP north and south pair, read this before configuring them

The image now ships both `fledge-north-httpc` and `fledge-south-http-south`.
Running both in one instance lets the north feed its own south: anything the
south ingests under the same asset prefix is re-sent by the north and ingested
again, one extra copy per cycle, compounding until the instance falls over.

They are shipped together because they are useful separately, on different
instances, as the two ends of one link. Do not enable both on the same instance
unless the asset prefixes provably cannot overlap.

## What is pinned, and what is not

Every input that decides what ends up in the image is pinned:

| Input | How |
|---|---|
| Base image | `name:tag@sha256:...` in every workflow matrix entry and in `.ci/build/Dockerfile` |
| Fledge core | the exact `.deb` the build job produced, copied in, never re-resolved |
| Plugins | `plugins.txt`, `package=version` |
| Plugin python deps | `requirements-pinned.txt` inside each plugin `.deb`, all `==` |
| GitHub Actions | commit SHA on every `uses:` |

The base image is pinned by *index* digest, so one digest covers amd64 and arm64.
The tag is kept in front of the digest for readability; Docker resolves on the
digest and ignores the tag. The same digest has to appear in the `.deb` build
matrix and the image build matrix for a given codename — the runtime's
`libboost-*` must satisfy the ABI the `.deb` was built against, and a floating
tag lets those drift across a point release.

To refresh a base image:

```sh
docker buildx imagetools inspect debian:bookworm-slim --format '{{.Manifest.Digest}}'
```

then replace every occurrence of that image's digest in
`.github/workflows/publish-apt-azure.yml` and `.ci/build/Dockerfile`.

The apt packages installed at image build time (`ca-certificates`, `curl`,
`rsyslog`, and the build-only `build-essential` / `python3-dev`) are **not**
version-pinned. Debian and Ubuntu drop superseded versions from the archive when
a security update lands, so an exact pin turns into a build failure within weeks
rather than a reproducible build. Pinning them properly means building against a
snapshot archive, which is a larger change than this file.

## How logging reaches `docker logs`

Fledge does not write its own log files. Core, the C/C++ services and the python
plugin loggers all call `syslog(3)`, so without a syslog daemon in the container
those messages go nowhere. rsyslog is installed for exactly that reason, and the
entrypoint streams its output to stdout with `tail -F`.

Two things do not go through syslog:

- `scripts/fledge` starts the core as
  `python3 -m fledge.services.core > /dev/null 2> "$FLEDGE_DATA/core.err"`, so
  the core's stderr lands in a file. That is where an early traceback, a broken
  maintainer script or a plugin's import-time stderr shows up, and nothing else
  reads it. The entrypoint tails it alongside syslog.
- South and north service processes have both stdout and stderr on `/dev/null`.
  A `print()` or a direct `sys.stderr.write` inside plugin code is discarded
  before it reaches any sink, and no change to this image can recover it —
  fixing that means changing where fledge points those descriptors. Plugin
  `_LOGGER` calls are unaffected; they go through syslog and are captured.

## Why `/var/log` is not a volume

`VOLUME` only declares a mount point. With no explicit `-v`, Docker creates an
*anonymous* volume, which is orphaned by every `docker rm` without `-v` — a slow
disk leak rather than the log retention it looks like. Since the entrypoint
already streams everything to stdout, retention belongs to the log driver
(`max-size` / `max-file`), which rotates properly and is configurable per
deployment. So only `/usr/local/fledge/data` is declared, and that is real state:
database, config, certificates, support bundles.

The on-disk copy still has to exist, because fledge's own support bundle reads
`/var/log/syslog` directly (`python/fledge/services/core/support.py`). Keeping it
inside the container is only safe if it cannot grow without bound, and the base
image has neither `cron` nor `logrotate` installed, so the stock
`/etc/logrotate.d/rsyslog` never runs. `rsyslog.conf` therefore does its own
size-capped rotation via `rotation.sizeLimit` and `rotation.sizeLimitCommand`,
calling `rsyslog-rotate.sh` to keep a single previous generation. Worst case on
disk is twice the limit. `tail -F` follows by name, so it reattaches after each
rotation.

The config also drops the stock per-facility duplicates (`user.log`, `mail.log`
and friends). Everything fledge emits is `user` facility, so those files doubled
every write for no benefit.

## Tests

`Projects/fledge-local-test/` holds the harness used to verify all of this
against a real published image, without rebuilding:

- `log-coverage-test.sh baseline|patched` installs a probe south plugin that
  emits markers down every logging path and asserts which ones reach
  `docker logs`.
- `rotation-test.sh` floods syslog against a small limit and asserts the file
  stays bounded, that only one previous generation is kept, and that the tail
  survives rotation.
