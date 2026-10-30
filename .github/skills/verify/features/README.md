# Fledge verification map

This directory is the maintained source for verifying the user-facing behavior of the Fledge core REST API. Read this index before driving an instance, then use the matching feature file as the recipe.

## Baseline preconditions

- `fv` means `python3 .github/skills/verify/scripts/fledge_verify.py` (Linux/macOS) or `python .github\skills\verify\scripts\fledge_verify.py` (Windows), run from the repo root.
- The image `fledge-local:dev` is built from the current checkout with `fv build`.
- A fresh instance is started with `fv launch --run <feature>-<n>`. Its data volume starts empty, so Fledge seeds a new sqlite database: users `admin` and `user` (password `fledge`), the seeded schedules (`purge`, `stats collection`, `backup on demand`, `restore on demand`, ...), and the `rest_api` category with authentication mandatory.
- `fv doctor` reports `healthy` before the first drive call.
- Never drive an instance this run did not launch. `fv list` shows the labelled verify containers; other containers on the Docker host belong to someone else.

## Driving conventions

- Every journey starts from a freshly launched instance unless its preconditions say otherwise. One run per feature keeps evidence readable.
- Drive public `/fledge/...` routes as a logged-in user with `fv api`. `--as admin` is the default; use `--as user:fledge` for the seeded non-admin and `--as none` for anonymous calls.
- Commands below use POSIX quoting. They work unchanged in PowerShell 7.3+. Windows PowerShell 5.1 strips the inner double quotes from inline JSON; there, put the body in a file and pass `--data '@body.json'`.
- Use `--expect <status>` on every call that has a known answer, so a wrong status fails the step instead of scrolling past.
- Label every call `--label <sub-feature-id>-<step>` so the evidence directory reads as the journey.
- `fv sql` and `fv exec` are for observing side effects. Never change state through them.

## Proof and skip reporting

- A journey is proven by: the mutating call, a separate `GET` showing the new state, and the side effect (audit entry, stored row, or file on disk).
- Audit entries are the cross-cutting side effect: `GET /fledge/audit?source=<CODE>&limit=5` returns `{"audit": [...], "totalCount": N}` with the newest entry first.
- Evidence for run `<run>` is in `.verify-evidence/<run>/`, numbered in call order, and survives `fv cleanup`.
- Report an unreachable step with the call that failed, its status and body, and the unmet precondition. Do not substitute a different route and report the original as verified.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with fledge_verify.py` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

Keep implementation details out of the map. Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [Health and services](./health.md) covers ping, the service registry, and storage and logging health.
- [Authentication and users](./auth-users.md) covers login, wrong-password rejection, admin-only user creation, role enforcement, and logout.
- [Configuration](./configuration.md) covers creating a category, changing an item, reading it back, and the audit trail.
- [Schedules and tasks](./schedules-tasks.md) covers listing schedules, running one on demand, observing its task, and disabling and enabling a schedule.
- [Backup](./backup.md) covers creating an on-demand backup, polling it to completion, and the backup file on disk.
