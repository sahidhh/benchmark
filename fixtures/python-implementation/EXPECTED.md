## Root Cause

Three bugs and two missing implementations in `app.py`:

1. **No input validation** (`create_task`, line 21): missing title raises `KeyError`; empty title should return 400.

2. **Unhandled `KeyError`** (`get_task`, line 30): `_tasks[task_id]` raises `KeyError` for unknown IDs instead of returning 404.

3. **`update_task` not implemented** (line 36): returns `None` (Flask returns 200 with empty body).

4. **`delete_task` not implemented** (line 42): returns `None`.

## Correct File

`app.py` only. `tests.py` is a read-only specification — must not be modified.

## Expected Files

`app.py` only.

## Expected Scope

Fix all 4 issues so all tests in `tests.py` pass. Use the existing `_tasks` dict and `_next_id` counter. Do not add a database. Do not modify `tests.py`.

## Known Pitfalls

- Modifying `tests.py` to make tests pass rather than fixing `app.py`
- Adding a database or external dependency instead of using the existing in-memory store
- Implementing `update_task` to replace the entire task rather than merging the patch fields
- Missing the empty-title 400 validation (only handling missing title)
