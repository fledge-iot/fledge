# Health and services

Health lets a client or the GUI confirm that a Fledge instance is up, which services are registered and running, and whether storage and logging have disk to work with.

## Sub-features

- `health-ping` answers without a token with uptime, version, health, and safe-mode state.
- `health-services` lists registered services with their type and status.
- `health-storage` reports the storage service and the disk under the data directory.
- `health-logging` reports log levels and the disk under the log directory.
- `health-auth` rejects anonymous calls to anything but ping and login.

## How to get to it (user POV)

- `GET /fledge/ping` with or without a token (the GUI polls this for its status bar).
- `GET /fledge/service` with a token (GUI South/North/Notifications pages read this).
- `GET /fledge/health/storage` and `GET /fledge/health/logging` with a token.
- `fledge status` inside the container, which prints the same service list.

## Driving it with fledge_verify.py

Preconditions:

- `fv launch --run health-1` printed `READY`.
- `fv doctor` reports `healthy`.

- **Ping anonymously.** Call ping with no token. Run `fv api GET /fledge/ping --as none --expect 200 --label health-ping`. The body has `"health": "green"`, `"safeMode": false`, `"authenticationOptional": false`, an `uptime` above 0, and a `version` equal to the repo's `VERSION` file.
- **List services.** Run `fv api GET /fledge/service --expect 200 --label health-services`. `services` contains an entry with `"type": "Core"` and one with `"type": "Storage"`, both `"status": "running"`, each with a `protocol`, `address`, and `service_port`/`management_port`.
- **Storage health.** Run `fv api GET /fledge/health/storage --expect 200 --label health-storage`. The body has `"name": "Fledge Storage"`, an `uptime`, per-operation `statistics`, and a `disk` object with `used`, `usage`, `available`, and `"status": "green"`.
- **Logging health.** Run `fv api GET /fledge/health/logging --expect 200 --label health-logging`. The body has a `levels` list and a `disk` object with `used`, `usage`, and `available`.
- **Anonymous rejection.** Run `fv api GET /fledge/service --as none --expect 401 --label health-auth-anon`. The status is 401.
- **CLI view.** Run `fv exec --label health-cli -- /usr/local/fledge/bin/fledge status`. Exit code 0; the output says `Fledge v<VERSION> running.` and `Fledge requires authentication.`, and lists the `fledge.services.core` and `fledge.services.storage` processes.
- **Proof.** The evidence directory holds the ping, services, both health reads, the 401, and the CLI output. Uptime in a second `fv api GET /fledge/ping --as none --label health-ping-again` is larger than in the first.

## Gotchas

- Ping is allowed without a token because `allowPing` defaults to true; a 200 from ping does not prove authentication works. Use the 401 step for that.
- `health` in ping turns `amber` or `red` when a service is degraded or the disk is filling. On a shared Docker host with a nearly full disk, `amber` can be an environment fact, not a regression. Check `disk.usage` before blaming the change.
- Right after launch, services other than Core and Storage do not exist: no south, north, or notification plugin is installed in this image. `levels` in logging health is `[]` on a fresh instance for the same reason.
- `fledge status` lists services by process name, not by the registry names `Fledge Core` and `Fledge Storage` that `GET /fledge/service` returns, and it splits its output across stdout and stderr. Assert on the REST steps; the CLI output is supporting evidence.
