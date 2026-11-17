---
name: verify
description: "Prove a Fledge change works by building this checkout into the fledge-local Docker image, launching an isolated container, and driving the Fledge core REST API (port 8081) the way a client or the GUI does, with recorded evidence. Use after changing Python core services, C storage/services, scripts, or packaging, or whenever asked to verify, reproduce, or demo Fledge behavior end to end."
---

# Verify Fledge

The user-facing surface of this repo is the Fledge core REST API (`/fledge/...`, served on port 8081). The GUI lives in a separate repo and only calls this API; the `fledge` CLI is a thin wrapper over the same API. Verification means building the `.deb` from this checkout, running it in a disposable container, and calling the API as an authenticated user.

Everything goes through one stdlib helper, run from the repo root:

```sh
python3 .github/skills/verify/scripts/fledge_verify.py <command>   # Linux/macOS
python .github\skills\verify\scripts\fledge_verify.py <command>    # Windows
```

Below, `fv` stands for that invocation. It needs Docker with Compose v2 and nothing else on the host.

Read [`features/README.md`](features/README.md) before driving, then use the matching feature file as the recipe.

## Launch

1. **Build the image from this checkout.** `fv build` runs `docker compose -f .ci/local/docker-compose.yml build fledge`, which compiles C/C++ and Python, packages the `.deb`, and installs it into `fledge-local:dev` on `ubuntu:22.04`. The first build takes 15-40 minutes; after that, any source change reruns from `make install` (a few minutes). It writes `.verify-evidence/build.json` with the image id and a fingerprint of the source it was built from. Rebuild after every source change you want to verify.
2. **Start a fresh instance.** `fv launch [--run NAME] [--port N]`. Each launch gets its own container `fledge-verify-<run>`, labels `fledge.verify.run=<run>` and `fledge.verify.repo=<repo path>`, a free host port bound to `127.0.0.1`, and an empty volume `fledge-verify-<run>-data` mounted at `/usr/local/fledge/data`. Fledge creates and seeds its sqlite database on first start, so every run starts from the same baseline.
3. **Ready means usable.** Launch returns only when `GET /fledge/ping` answers 200, `admin`/`fledge` can log in, the `Fledge Core` and `Fledge Storage` services report `running`, and the seeded `purge` and `backup on demand` schedules exist. That takes 10-30 seconds. It times out after `--timeout` seconds (default 300) and leaves the container for inspection; run cleanup afterwards. It prints the port and writes `instance.json`, `tokens.json`, and `000-ready.json` to the run's evidence directory.

Teardown is `fv cleanup` (see Cleanup).

## Doctor

`fv doctor [--run NAME]` answers "is this instance worth driving?" without changing anything. It checks that the Docker daemon is up, the container is running and carries this run's label, the expected host port maps to 8081, the container's image id matches the current `fledge-local:dev`, that image was built from the current source (fingerprint in `build.json`), the installed `VERSION` matches the repo's `VERSION`, ping answers, the admin token is valid, and core services are running. It exits 1 with the failing line marked `FAIL`. Run it first whenever anything looks off; a stale image or stale build is the usual cause of "my change did nothing".

## Drive

Drive the REST API the way a client does, as a real user with a real token:

- `fv api METHOD PATH [--data JSON|@file] [--as admin|none|USER:PASSWORD] [--label NAME] [--expect STATUS]`
  - Logs in as `admin`/`fledge` by default and sends `authorization: <token>` (no `Bearer`). `--as none` sends no token; `--as user:fledge` logs in as the seeded non-admin `user`.
  - Prints status and body, records both to evidence, and exits 1 when `--expect` does not match.
  - Tokens are cached per user and password in `tokens.json`. On a 401 it logs in once more and retries, which keeps long sessions alive. Pass `--no-relogin` to send the cached token as-is and record the 401, which is how a logout or token-expiry proof must be driven.
  - Inline JSON (`--data '{"value": "42"}'`) works in POSIX shells and PowerShell 7.3+. Windows PowerShell 5.1 strips the inner double quotes; there, use `--data '@body.json'`.
- `fv sql "SELECT ..." [--db PATH]` runs a read-only `sqlite3 -json` query inside the container against `/usr/local/fledge/data/fledge.db`, for side-effect proof (rows written).
- `fv exec -- <cmd> [args...]` runs a command inside the container (files written, the `fledge` CLI, logs).

Stable handles: route paths from `python/fledge/services/core/routes.py`, audit log codes from the `log_codes` table (`CONAD`, `CONCH`, `USRAD`, `SCHCH`, `BKEXC`, ...), seeded schedule ids from `scripts/plugins/storage/sqlite/init.sql`. Authentication is mandatory by default: every call except `/fledge/ping` and `/fledge/login` needs a token.

The feature map lists the journeys: health, auth and users, configuration, schedules and tasks, backup.

## Evidence

Every helper call writes a numbered JSON file to `.verify-evidence/<run>/` (`NNN-<label>.json`) with the exact request, status, response body, and timestamp. `.verify-evidence/` is git-ignored and docker-ignored and is never deleted by the helper. Cleanup adds `container.log` (the container's stdout/stderr, which tails syslog and the core error log).

Proof standards:

- Exercise the real user path: the public `/fledge/...` routes with a logged-in user. Never write to the database or call internal setters to make a check pass; `sql` is read-only and is for observing side effects only.
- Capture the action and the resulting state: the mutating call, then a separate read (a `GET` of the same resource) showing the new value.
- Verify side effects alongside the response: the audit entry (`GET /fledge/audit?source=<CODE>`), the stored row (`fv sql`), the file on disk (`fv exec -- ls ...`). A 200 alone proves nothing.
- Prove the negative path where the feature has one: wrong password returns 401, non-admin gets 403 on admin routes.
- No mocks. There is no external system on these journeys; south and north plugins that would talk to devices or PI servers are not installed in this image.
- Label calls with the feature id (`--label config-update`) so the evidence directory reads as the journey.

## Cleanup

`fv cleanup [--run NAME]` removes only the container labelled with that run (default: the latest), after saving its log to `container.log`, and removes its data volume. `fv cleanup --all` does the same for every verify container started from this checkout. `fv list` shows what exists. The evidence directory stays. Never stop containers by name pattern or kill processes by name: the Docker host is shared with unrelated containers, and the helper only touches containers that carry its labels.

Run cleanup after every run, including failed launches.

## Helpers

`scripts/fledge_verify.py` (stdlib Python 3.8+), subcommands:

| Command | Does |
| --- | --- |
| `build` | Compose build of `fledge-local:dev` from this checkout; writes `build.json` |
| `launch [--run] [--port] [--timeout]` | Fresh labelled container, own port and volume; waits until usable |
| `doctor [--run]` | Read-only health, build, and ownership check; exit 1 if not drivable |
| `api METHOD PATH [--data] [--as] [--label] [--expect] [--no-relogin] [--timeout]` | Authenticated REST call, recorded |
| `sql QUERY [--db] [--label]` | Read-only sqlite query in the container, recorded |
| `exec [--label] -- CMD...` | Command in the container, recorded |
| `cleanup [--run] [--all]` | Remove labelled container and volume, keep evidence |
| `list` | Verify containers on this Docker host |

Commands after `launch` default to the run named in `.verify-evidence/LATEST`.
