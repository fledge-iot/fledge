# `.ci/local/` — build and run Fledge from this checkout

Builds the Fledge core from the working tree, packages it as a `.deb`, installs it into a
slim runtime image and starts it. Use it to try a code change in a real container without
going through CI. It runs the same steps as `.ci/build/Dockerfile` and the `slim` target of
`.ci/image/Dockerfile`, so what you test is what CI would ship (minus plugins).

Requires Docker with Compose v2.17 or newer (uses `additional_contexts`).

## Run

From the repo root:

```bash
docker compose -f .ci/local/docker-compose.yml up --build -d
docker compose -f .ci/local/docker-compose.yml logs -f
```

The first build compiles the C++ core and takes 15–40 minutes. Later builds reuse the layer
cache; editing only Python invalidates just the `make install` layer onwards.

Check it is up (the API is on host port **8082**, so it does not clash with another Fledge on 8081):

```bash
curl -s localhost:8082/fledge/ping
docker exec fledge-local cat /usr/local/fledge/VERSION
```

Log in (check the credentials for your build; a fresh image accepts `admin` / `fledge`):

```bash
T=$(curl -s -X POST localhost:8082/fledge/login \
      -d '{"username":"admin","password":"fledge"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "authorization: $T" "localhost:8082/fledge/syslog?source=Fledge&limit=5&nontotals=true"
```

## Stop and clean up

```bash
docker compose -f .ci/local/docker-compose.yml down        # stop, keep data
docker compose -f .ci/local/docker-compose.yml down -v     # stop and delete the data volume
```

## Options

| Variable | Default | Effect |
|---|---|---|
| `FLEDGE_PORT` | `8082` | Host port for the REST API |
| `BASE_IMAGE` | `ubuntu:22.04` | Base image for both the build and the runtime, e.g. `debian:bookworm-slim` |

```bash
FLEDGE_PORT=9000 BASE_IMAGE=debian:bookworm-slim docker compose -f .ci/local/docker-compose.yml up --build -d
```

## How it works

- `deb-builder` builds the `builder` stage of `.ci/build/Dockerfile` (compile, `make install`,
  `build_deb.sh`). It is never started; it only produces the `.deb`.
- `fledge` builds `.ci/local/Dockerfile` with `.ci/image/` as context. It takes the `.deb` from
  `deb-builder` through the `debbuilder` additional context, installs it, and reuses
  `entrypoint.sh` and the rsyslog files from `.ci/image/`.
- Data persists in the `fledge-data` volume, mounted at `/usr/local/fledge/data`.

## Caveats

- `.ci/local/Dockerfile` repeats the install steps of `.ci/image/Dockerfile` (slim target),
  because Compose cannot pass a build stage to that file as `fledge.deb`. If the CI image
  Dockerfile changes, update this one too.
- No plugins are installed. The `full` image pulls them from the signed apt repository, which
  needs network access to `packages.helinplatform.com`.
- Single architecture: the build is for the host platform. Multi-arch builds go through
  `.ci/build/build.sh`.
- The checkout is the build context. On WSL, keeping the repo on the Linux filesystem instead
  of `/mnt/c` makes context transfer noticeably faster.
