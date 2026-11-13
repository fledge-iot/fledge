# Backup

Backup lets an admin take an on-demand backup of the Fledge database, watch it reach `COMPLETED`, and see it listed with a file on disk that can later be downloaded or restored.

## Sub-features

- `backup-create` starts an on-demand backup as an admin.
- `backup-complete` shows the backup moving from `RUNNING` to `COMPLETED`.
- `backup-file` writes a backup file under the data directory.
- `backup-admin-only` refuses backup creation to the non-admin `user`.

## How to get to it (user POV)

- `POST /fledge/backup` as an admin (GUI Backup & Restore, Backup).
- `GET /fledge/backup`, `GET /fledge/backup/<id>`, and `GET /fledge/backup/status` (GUI Backup & Restore list).
- `GET /fledge/backup/<id>/download` (GUI download button).

## Driving it with fledge_verify.py

Preconditions:

- `fv launch --run backup-1` printed `READY`.
- No backups exist yet: `fv api GET /fledge/backup --expect 200 --label backup-pre-empty` returns `"backups": []`.

- **Refused for non-admin.** Run `fv api POST /fledge/backup --as user:fledge --expect 403 --label backup-admin-only`. Then `fv api GET /fledge/backup --expect 200 --label backup-admin-only-list` still returns no backups.
- **Create a backup.** Run `fv api POST /fledge/backup --expect 200 --label backup-create`. The body is `{"status": "running"}`.
- **Backup completes.** Poll `fv api GET /fledge/backup --expect 200 --label backup-poll` every few seconds, up to 120 seconds (a fresh instance completes in under 10). One entry appears with `id` 1, a `date`, and `status` `COMPLETED`. Read it alone with `fv api GET /fledge/backup/1 --expect 200 --label backup-read`.
- **File on disk.** Run `fv sql "SELECT id, file_name, status, exit_code FROM backups ORDER BY id DESC LIMIT 1" --label backup-row` and `fv exec --label backup-file -- ls -l /usr/local/fledge/data/backup`. The row has `exit_code` 0 and a `file_name` like `/usr/local/fledge/data/backup/fledge_backup_<YYYY_MM_DD_HH_MM_SS>.tar.gz`, and that file is in the listing with a non-zero size (about 40 KB on a fresh instance).
- **Audited.** Run `fv api GET "/fledge/audit?source=BKEXC&limit=5" --expect 200 --label backup-audit`. The newest entry has `details` `{"status": "completed"}` and a timestamp matching the backup `date`.
- **Ran as a task.** Run `fv api GET "/fledge/task/latest?name=backup%20on%20demand" --expect 200 --label backup-task`. The task is `Complete` with `exitCode` 0.

## Gotchas

- The backup runs as a task from the `backup on demand` schedule; it is asynchronous. `POST /fledge/backup` returning 200 with `"running"` only means the request was accepted.
- The `backups` table stores `status` as an integer (2 for completed); the API maps it to the uppercase name. Assert on the API string and use the row only for `file_name` and `exit_code`.
- The backup directory lives on the run's data volume and disappears with `fv cleanup`. The `backup-file` listing in evidence is the lasting proof.
- Status strings are uppercase (`RUNNING`, `COMPLETED`, `CANCELED`, `INTERRUPTED`, `FAILED`, `RESTORED`).
