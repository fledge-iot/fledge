# Authentication and users

Authentication lets a person log in with a username and password, use the returned token on every call, and log out. An admin can create users with a role; non-admin roles are refused admin operations.

## Sub-features

- `auth-login` exchanges a username and password for a token.
- `auth-bad-password` refuses a wrong password and an unknown user.
- `auth-create-user` lets an admin create a user, which is audited as `USRAD`.
- `auth-new-user-login` lets the created user log in and read only their own profile.
- `auth-role-enforced` refuses admin operations to the non-admin `user` role.
- `auth-logout` invalidates the token so the next call is refused.

## How to get to it (user POV)

- `POST /fledge/login` with `{"username": ..., "password": ...}` (the GUI login page).
- `POST /fledge/admin/user` as an admin (GUI User Management, Add User).
- `GET /fledge/user` (all users, admin only) and `GET /fledge/user?username=<name>` (one user).
- `PUT /fledge/logout` with the token to log out (GUI logout menu).

## Driving it with fledge_verify.py

Preconditions:

- `fv launch --run auth-1` printed `READY`.
- No user named `verifier` exists: `fv api GET "/fledge/user?username=verifier" --expect 404 --label auth-pre-absent`.

- **Log in as admin.** Run `fv api POST /fledge/login --as none --data '{"username": "admin", "password": "fledge"}' --expect 200 --label auth-login`. The body has `"admin": true`, a `uid`, and a `token`.
- **Wrong password.** Run `fv api POST /fledge/login --as none --data '{"username": "admin", "password": "wrong"}' --expect 404 --label auth-bad-password`. The body `message` is `Username or Password do not match`. Repeat with `"username": "nobody"` and `--label auth-bad-user`; the status is also 404 with `User does not exist`.
- **Create a user.** Run `fv api POST /fledge/admin/user --data '{"username": "verifier", "password": "Verify@123", "role_id": 2, "real_name": "Verify Bot", "description": "created by verify"}' --expect 200 --label auth-create-user`. The body says `verifier user has been created successfully.` and `user` has `userName: "verifier"`, `roleId: 2`.
- **Read it back.** Run `fv api GET "/fledge/user?username=verifier" --expect 200 --label auth-create-user-read`. The body shows the same `userName`, `roleId`, `realName`, and `description`.
- **Audit side effect.** Run `fv api GET "/fledge/audit?source=USRAD&limit=5" --expect 200 --label auth-create-user-audit`. The newest entry has `source: "USRAD"` and `details` with `uname: "verifier"`, `role_id: 2`, and `real_name: "Verify Bot"`.
- **Stored row.** Run `fv sql "SELECT id, uname, role_id, enabled FROM users WHERE uname = 'verifier'" --label auth-create-user-row`. One row with `role_id` 2 and `enabled` `t`.
- **New user logs in.** Run `fv api GET "/fledge/user?username=verifier" --as verifier:Verify@123 --expect 200 --label auth-new-user-login`. The token comes from a real login as `verifier`, recorded in `tokens.json`.
- **Role enforced.** Run `fv api GET /fledge/user --as verifier:Verify@123 --expect 403 --label auth-role-list-users` and `fv api POST /fledge/admin/user --as verifier:Verify@123 --data '{"username": "sneaky", "password": "Sneaky@123"}' --expect 403 --label auth-role-create-user`. Both are 403, and `fv api GET "/fledge/user?username=sneaky" --expect 404 --label auth-role-no-sneaky` confirms nothing was created.
- **Log out.** Run `fv api PUT /fledge/logout --as verifier:Verify@123 --expect 200 --label auth-logout`. The body is `{"logout": true}`. Then run `fv api GET "/fledge/user?username=verifier" --as verifier:Verify@123 --no-relogin --expect 401 --label auth-logout-token-dead`. The old token is refused with `Token appears to be invalid`.
- **Cleanup fixture.** Delete the user with the `userId` from the create step (3 on a fresh instance): `fv api DELETE /fledge/admin/<userId>/delete --expect 200 --label auth-fixture-delete`. The body says `User has been deleted successfully.`

## Gotchas

- A wrong password returns 404, not 401. Assert 404 for `auth-bad-password`.
- The password policy is a configuration category (`password`); the default is `Any characters` with a minimum length of 6. `Verify@123` satisfies every policy level, so keep it.
- Without `--no-relogin`, the helper silently logs in again after a 401, and a logout proof would pass on a fresh token. Always use `--no-relogin` on the post-logout call.
- `--as <user>:<password>` caches tokens per user and password; a different password forces a real login, and a failed one exits with `login failed` without writing an evidence file. Prove login failures through `POST /fledge/login --as none`, which records the response.
- Usernames are lowercased and stripped of spaces on create. Assert on the lowercased name.
- Deleting the seeded `admin` (id 1) returns 403 `Super admin user can not be deleted.` Use the created `verifier` for delete steps.
