# Configuration

Configuration lets a user create a configuration category, change one of its items, and read the new value back. Every Fledge service, plugin, and the GUI Settings pages are built on these categories, and each change is audited.

## Sub-features

- `config-create` creates a category with typed items, audited as `CONAD`.
- `config-read` returns a category and a single item with `default` and `value`.
- `config-update` changes an item's value, audited as `CONCH` with old and new values.
- `config-validate` refuses a value that does not match the item type, a non-string value, and an unknown item.
- `config-delete` removes the category.

## How to get to it (user POV)

- `POST /fledge/category` with `{"key", "description", "value": {<item>: {"description", "type", "default"}}}`.
- `GET /fledge/category/<key>` and `GET /fledge/category/<key>/<item>` (GUI Settings and every plugin configuration panel).
- `PUT /fledge/category/<key>/<item>` with `{"value": "<string>"}` (GUI Save on a single field).
- `PUT /fledge/category/<key>` with `{"<item>": "<value>", ...}` (GUI Save on a whole panel).
- `DELETE /fledge/category/<key>`.

## Driving it with fledge_verify.py

Preconditions:

- `fv launch --run config-1` printed `READY`.
- No category named `VERIFY_CFG` exists: `fv api GET /fledge/category/VERIFY_CFG --expect 404 --label config-pre-absent`.

- **Create a category.** Run `fv api POST /fledge/category --data '{"key": "VERIFY_CFG", "description": "verify skill category", "value": {"interval": {"description": "Poll interval", "type": "integer", "default": "10"}, "label": {"description": "Label", "type": "string", "default": "alpha"}}}' --expect 200 --label config-create`. The body has `key: "VERIFY_CFG"` and both items with `value` equal to `default`.
- **Create is audited.** Run `fv api GET "/fledge/audit?source=CONAD&limit=5" --expect 200 --label config-create-audit`. The newest entry has `source: "CONAD"` and `details.name` `VERIFY_CFG`.
- **Update one item.** Run `fv api PUT /fledge/category/VERIFY_CFG/interval --data '{"value": "42"}' --expect 200 --label config-update`. The body shows `"value": "42"` and `"default": "10"`.
- **Read it back.** Run `fv api GET /fledge/category/VERIFY_CFG/interval --expect 200 --label config-update-read`. `value` is `"42"`. Run `fv api GET /fledge/category/VERIFY_CFG --expect 200 --label config-read`; the body is the item map itself (no `key` wrapper), with `interval.value` `"42"` and `label.value` still `"alpha"`.
- **Update is audited.** Run `fv api GET "/fledge/audit?source=CONCH&limit=5" --expect 200 --label config-update-audit`. The newest entry has `details.category` `VERIFY_CFG`, `details.item` `interval`, `details.oldValue` `"10"`, and `details.newValue` `"42"`.
- **Stored row.** Run `fv sql "SELECT key, json_extract(value, '$.interval.value') AS interval FROM configuration WHERE key = 'VERIFY_CFG'" --label config-update-row`. One row with `interval` `"42"`.
- **Bad value refused.** Run `fv api PUT /fledge/category/VERIFY_CFG/interval --data '{"value": "not-a-number"}' --expect 400 --label config-validate`; the reason is `Unrecognized value name for item_name interval`. Then `fv api GET /fledge/category/VERIFY_CFG/interval --expect 200 --label config-validate-read`; `value` is still `"42"`.
- **Non-string and unknown item refused.** Run `fv api PUT /fledge/category/VERIFY_CFG/interval --data '{"value": 42}' --expect 400 --label config-validate-nonstring` (`42 should be a string literal, in double quotes`) and `fv api PUT /fledge/category/VERIFY_CFG/nosuch --data '{"value": "1"}' --expect 404 --label config-unknown-item` (`No detail found for the category_name: VERIFY_CFG and item_name: nosuch`).
- **Delete.** Run `fv api DELETE /fledge/category/VERIFY_CFG --expect 200 --label config-delete` (`{"result": "Category VERIFY_CFG deleted successfully."}`) and `fv api GET /fledge/category/VERIFY_CFG --expect 404 --label config-delete-read`.

## Gotchas

- Item values are always strings in the API, including integers and booleans. `{"value": 42}` is refused with 400; send `"42"`.
- The single-item `PUT` returns the item, the bulk `PUT /fledge/category/<key>` returns the whole category. Assert on the shape you called.
- `GET /fledge/audit?source=CONAD` on a fresh instance already holds the seeded categories (`General`, `Utilities`, `PURGE_READ`, ...). Assert on the newest entry's `details.name`, not on `totalCount`.
- Do not use seeded categories such as `rest_api` or `password` for update proofs: changing them alters authentication for the rest of the run.
