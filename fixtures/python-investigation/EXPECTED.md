## Root Cause

Multiple security vulnerabilities across the auth stack:

1. **SQL injection in `database.py` line 19**: `get_user()` uses raw string interpolation — `f"SELECT ... WHERE username='{username}' AND password='{password}'"`. Classic injection vector.

2. **Plaintext passwords** (`database.py` line 19): passwords compared directly without hashing.

3. **Password leak in `list_all_users()`** (`database.py` line 43): returns the `password` field to callers.

4. **Missing admin authorization** (`app.py` line 28): `/api/admin/users` has a `# TODO: restrict to admin only` comment — any authenticated user can list all users.

5. **Hardcoded secret** (`auth.py` line 8): `SECRET = "dev-secret-do-not-use-in-prod"` is in source.

## Correct File

`database.py` is the primary source (SQL injection, plaintext passwords, password leak). `app.py` has the authorization gap. `auth.py` has the hardcoded secret.

## Expected Files

A complete answer references all three files: `database.py`, `app.py`, `auth.py`.

## Expected Scope

Identify all 5 issues with file + line references. Do not implement fixes. Do not invent issues not present in the code.

## Known Pitfalls

- Reporting only the SQL injection and missing the password leak in `list_all_users()`
- Missing the admin authorization gap in `app.py`
- Fixing code instead of reporting findings
- Inventing issues (e.g., "no rate limiting") not visible in the fixture
