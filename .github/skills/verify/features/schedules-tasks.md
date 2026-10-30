# Schedules and tasks

Schedules let a user see what Fledge runs on a timer or on demand, trigger a schedule now, watch the resulting task finish, and turn a schedule off and on. The GUI Schedules page and every "run now" action use these routes.

## Sub-features

- `sched-list` lists schedules with type, repeat, and enabled state.
- `sched-run-now` starts a schedule on demand and produces a task.
- `sched-task-complete` shows the task reaching a final state with an exit code.
- `sched-disable-enable` turns a schedule off and back on, audited as `SCHCH`.

## How to get to it (user POV)

- `GET /fledge/schedule` and `GET /fledge/schedule/<id>` (GUI Schedules page).
- `POST /fledge/schedule/start/<id>` (GUI run-now).
- `GET /fledge/task/latest?name=<schedule name>` and `GET /fledge/task/<task id>` (GUI Tasks view).
- `PUT /fledge/schedule/<id>/disable` and `PUT /fledge/schedule/<id>/enable` (GUI enable toggle).

## Driving it with fledge_verify.py

Preconditions:

- `fv launch --run sched-1` printed `READY`.
- The seeded `purge` schedule exists with id `cea17db8-6ccc-11e7-907b-a6006ad3dba0`.

- **List schedules.** Run `fv api GET /fledge/schedule --expect 200 --label sched-list`. `schedules` has eight entries, including `purge` (`"type": "INTERVAL"`, `"repeat": 600`, `"enabled": true`), `stats collection` (`"repeat": 15`), `backup hourly` (`"enabled": false`), `backup on demand` and `restore on demand` (`"type": "MANUAL"`).
- **Run purge now.** First run `fv api GET "/fledge/task/latest?name=purge" --expect 404 --label sched-task-before`; a fresh instance has no purge task yet. Then run `fv api POST /fledge/schedule/start/cea17db8-6ccc-11e7-907b-a6006ad3dba0 --expect 200 --label sched-run-now`. The body is `{"id": "cea17db8-...", "message": "Schedule started successfully"}`.
- **Task finishes.** Poll `fv api GET "/fledge/task/latest?name=purge" --expect 200 --label sched-task-latest` every few seconds, up to 60 seconds, until `state` is final. The single task has `name: "purge"`, `processName: "purge"`, `state: "Complete"`, `exitCode` 0, a `pid`, and an `endTime`.
- **Task row.** Run `fv sql "SELECT schedule_name, state, exit_code FROM tasks WHERE schedule_name = 'purge' ORDER BY start_time DESC LIMIT 1" --label sched-task-row`. One row with `state` 2 (Complete) and `exit_code` 0.
- **Disable.** Run `fv api PUT /fledge/schedule/cea17db8-6ccc-11e7-907b-a6006ad3dba0/disable --expect 200 --label sched-disable`; the body has `"status": true` and `"message": "Schedule successfully disabled"`. Then `fv api GET /fledge/schedule/cea17db8-6ccc-11e7-907b-a6006ad3dba0 --expect 200 --label sched-disable-read`. `enabled` is `false`.
- **Enable.** Run `fv api PUT /fledge/schedule/cea17db8-6ccc-11e7-907b-a6006ad3dba0/enable --expect 200 --label sched-enable` (`"Schedule successfully enabled"`) and read it again with `--label sched-enable-read`. `enabled` is `true`.
- **Audited.** Run `fv api GET "/fledge/audit?source=SCHCH&limit=5" --expect 200 --label sched-audit`. `totalCount` is 2; both entries have `details.schedule.name` `purge`, the newest with `enabled: true` and the older with `enabled: false`, each carrying the previous state in `details.old_schedule`.

## Gotchas

- `stats collection` runs every 15 seconds on its own, so `GET /fledge/task/latest` without `?name=` is dominated by it. Always filter by name.
- Task `state` is a capitalized enum name (`Running`, `Complete`, `Canceled`, `Interrupted`). On a fresh instance purge finishes in under a second, so the first read is often already `Complete`; on a loaded instance it can be `Running` or 404 `No Tasks found`. Poll for a final state either way.
- Purge on a fresh instance has no readings to remove; `exitCode` 0 is the proof, not a row count.
- Starting a disabled schedule on demand still works; do not use run-now as proof that enable worked.
- Leave `purge` enabled at the end of the journey so later steps on the same instance see the baseline.
