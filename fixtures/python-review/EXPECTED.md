## Root Cause

Three critical issues in `main.py`:

1. **SQL injection** (`get_user`, line 9): `f"SELECT * FROM users WHERE username = '{username}'"` — raw string interpolation, trivially exploitable.

2. **Weak password hashing** (`hash_password`, line 17): MD5 is not a password hashing algorithm. Should be `bcrypt`, `argon2`, or `scrypt`.

3. **Remote code execution** (`process_user_input`, line 36): `eval(user_data["expression"])` executes arbitrary user-supplied Python. Critical severity.

## Correct File

`main.py` — single file, all issues present.

## Expected Files

`main.py` only.

## Expected Scope

Report all 3 issues with line references and severity. Do not implement fixes. Do not pad with minor style issues.

## Known Pitfalls

- Missing `eval()` as RCE — models often focus on SQL injection and MD5 and skip it
- Flagging `/tmp` path in `create_temp_file` as a high severity issue — it is low severity (predictable name, not a critical bug)
- Implementing fixes instead of reviewing
- Adding style/formatting observations that dilute the signal
