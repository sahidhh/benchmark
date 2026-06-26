## Root Cause

Three issues in `UserService.cs`:

1. **SQL injection in `GetByEmail`** (line 23): `$"SELECT ... WHERE email = '{email}'"` — string interpolation directly into SQL.

2. **SQL injection in `UpdateRole`** (line 33): `$"UPDATE users SET role = '{role}' WHERE id = {userId}"` — both `role` and `userId` interpolated.

3. **Silent failure in `UpdateRole`** (line 35 comment): no rowcount check after `ExecuteNonQuery()`. If `userId` doesn't exist, the update silently does nothing.

4. **Double connection in `DeactivateUser`** (lines 41–49): calls `GetUserById(userId)` which opens a connection, then opens a second connection for the UPDATE. Unnecessary resource usage.

## Correct File

`UserService.cs` — single file, all issues present.

## Expected Files

`UserService.cs` only.

## Expected Scope

Report all 4 issues with method names and line references. Do not fix. Do not add observations about DI or logging patterns.

## Known Pitfalls

- Reporting only `GetByEmail` injection and missing `UpdateRole` injection
- Missing the silent-failure pattern in `UpdateRole`
- Flagging the double-connection as a bug rather than an inefficiency
- Implementing parameterized queries instead of reviewing
