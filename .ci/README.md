# `.ci/` — Local and pipeline-ready build/test for Fledge `.deb`

These scripts build, package, and smoke-test Fledge `.deb` artifacts in Docker.
They run identically on a developer laptop (Docker Desktop), GitHub Actions, and
Azure DevOps (`Docker@2` task with buildx).

## Supported matrix

The CI workflow (`.github/workflows/publish-apt-azure.yml`) builds six
artifacts on every release:

| Codename | Base image           | Arch  | Runner             | Notes  |
| -------- | -------------------- | ----- | ------------------ | ------ |
| bullseye | debian:bullseye-slim | amd64 | ubuntu-22.04       | native |
| bullseye | debian:bullseye-slim | arm64 | ubuntu-22.04-arm   | native |
| bookworm | debian:bookworm-slim | amd64 | ubuntu-22.04       | native |
| bookworm | debian:bookworm-slim | arm64 | ubuntu-22.04-arm   | native |
| jammy    | ubuntu:22.04         | amd64 | ubuntu-22.04       | native |
| noble    | ubuntu:24.04         | amd64 | ubuntu-22.04       | native |

Native ARM64 runners (`ubuntu-22.04-arm`, GA on public repos since 2025-08
and on private repos since 2026-01) eliminate QEMU emulation from the arm64
build step. ARMv7 (`armhf`) is currently disabled — no native GHA runner
exists and QEMU emulation is too slow; re-enable in the matrix when there's
demand. Ubuntu builds are amd64-only for now; extend the matrix to add
ubuntu arm64 if there's demand.

The resulting apt repository hosts both Debian versions concurrently. End
users select the matching codename in their `sources.list`:

```sh
sudo curl -fsSL https://packages.helinplatform.com/apt/fledge.gpg \
  -o /usr/share/keyrings/fledge.gpg

echo "deb [signed-by=/usr/share/keyrings/fledge.gpg] https://packages.helinplatform.com/apt bookworm main" \
  | sudo tee /etc/apt/sources.list.d/fledge.list
```

Substitute the matching codename (`bullseye`, `bookworm`, `jammy`, `noble`) for the
device's distribution. Never use `[trusted=yes]` against the published repository:
it disables signature verification, which is the control that stops a hijacked
domain or cache from serving arbitrary root-level packages.

## Quick start (local)

```bash
# build the .deb (defaults: debian:bookworm-slim, linux/amd64)
.ci/build/build.sh
```

Artifacts land in `./build-out/fledge_<version>_<arch>.deb`. To smoke-test
the resulting .deb end-to-end, build the apt repo and exercise the
`apt-get install` path:

```bash
mkdir -p staging/bookworm && cp build-out/fledge_*_amd64.deb staging/bookworm/
CODENAME=bookworm COMPONENT=main .ci/apt/build_repo.sh staging/bookworm apt-repo-out
python3 -m http.server 8080 --directory apt-repo-out &
CODENAME=bookworm COMPONENT=main BASE_IMAGE=debian:bookworm-slim \
  .ci/apt/test_repo.sh "http://host.docker.internal:8080" amd64
```

## Targeting other distros or architectures

```bash
# Debian Bullseye, amd64
.ci/build/build.sh debian:bullseye-slim

# Debian Bullseye, arm64 (native on an arm64 host, QEMU on an x86 host)
.ci/build/build.sh debian:bullseye-slim linux/arm64

# Debian Bookworm, arm64
.ci/build/build.sh debian:bookworm-slim linux/arm64
```

## How it works

1. `.ci/build/Dockerfile` — three stages:
   - **deps**: installs build toolchain + runtime deps on the chosen base
     image. Cached across builds.
   - **builder**: copies the repo in, runs `requirements.sh` + `make install`
     (populates `/usr/local/fledge`), then runs
     `scripts/package/debian/build_deb.sh` to package `/usr/local/fledge` into a
     `.deb`. The Boost ABI version is detected from the build host's
     `libboost-dev` package, so the `.deb`'s `Depends:` field matches the
     consumer distro **as long as `BASE_IMAGE` matches that distro**.
   - **artifact**: `FROM scratch` containing only the `.deb`. Docker's
     `--output type=local,dest=./build-out` writes the scratch stage's
     filesystem to the host.

2. `.ci/apt/build_repo.sh` + `.ci/apt/test_repo.sh` — generate unsigned apt
   repository metadata for one codename, then verify that a clean container
   can `apt-get update` and `apt-get install fledge`. Re-invoke
   `build_repo.sh` with different `CODENAME` values to populate multiple
   codenames in the same repository tree; codenames are hermetic
   (`pool/<codename>/...` + `dists/<codename>/...`), so a Bullseye-built
   `.deb` never leaks into Bookworm's Packages file.

## CI integration

The same `docker buildx build --output type=local,dest=<dir>` command runs in
GitHub Actions and Azure DevOps — no workflow-specific logic in the build
itself. See `.github/workflows/publish-apt-azure.yml`.

## Docker image (`.ci/image/`)

After the apt repo publish, the same workflow builds and pushes an official
fledge runtime image to Docker Hub at `fledgeiot/fledge`. The image is
**pinned to the .deb produced by the build job**, not to a git ref — so the
Docker artifact and the apt-repo package are byte-identical fledge runtime.

### Tag scheme

| Tag | Points at |
| --- | --- |
| `fledgeiot/fledge:latest` | bookworm multi-arch (amd64 + arm64) — reference distro |
| `fledgeiot/fledge:<version>` | same as `latest`, with explicit version |
| `fledgeiot/fledge:<codename>` | latest version on that codename, multi-arch where available |
| `fledgeiot/fledge:<version>-<codename>` | versioned, multi-arch where available |
| `fledgeiot/fledge:<version>-<codename>-<arch>` | per-arch intermediary, used by the manifest step |

Multi-arch manifests are produced for `bullseye` and `bookworm` (amd64 + arm64).
`jammy` and `noble` are amd64-only.

### Local dev build (try it on your laptop)

```bash
# defaults: bookworm + amd64
.ci/image/build.sh

# Pick a different distro / arch
.ci/image/build.sh debian:bullseye-slim
.ci/image/build.sh debian:bookworm-slim linux/arm64   # needs QEMU on x86 hosts
.ci/image/build.sh ubuntu:22.04
```

`build.sh` first runs `.ci/build/build.sh` to produce the `.deb`, then `docker
buildx build`s the image with the matching base image. The resulting tag is
`fledge:dev-<codename>-<arch>`.

```bash
docker run --rm -d -p 8081:8081 --name fledge-dev fledge:dev-bookworm-amd64
curl http://localhost:8081/fledge/ping
docker stop fledge-dev

# Pass fledge start flags after the image name
docker run --rm -d -p 8081:8081 --name fledge-dev fledge:dev-bookworm-amd64 --safe-mode
```

### Pulling the published image

```bash
docker run --rm -d -p 8081:8081 --name fledge fledgeiot/fledge:bookworm
curl http://localhost:8081/fledge/ping
docker stop fledge
```

### What's NOT in this image (deliberately)

Compared to `POLARIS-Fledge-Base`:
- No PostgreSQL server. Fledge defaults to sqlite for storage; users who want
  postgres can link an external instance or layer it on top.
- No build toolchain — fledge is pre-built in the .deb.
- No fixed git ref. The image is pinned to whatever `.deb` the build job produced.
