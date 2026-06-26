## Root Cause

`UserService.cs` needs a `DeactivateAsync(int userId)` method. The task is to implement it correctly using existing infrastructure.

## Correct File

`UserService.cs` — add the method here.

## Expected Scope

`DeactivateAsync` should:
- Call `_repo.FindByIdAsync(userId)` to check existence
- Return early (or throw `KeyNotFoundException`) if user not found
- Update `Active = false` via the repository — the existing `UserRepository` does not have an `UpdateAsync` or `SetActiveAsync` method, so the correct answer either adds a minimal repository method or notes the gap
- NOT call `_notifications` (the task says "do not change NotificationService")
- Touch the minimum files: `UserService.cs` plus `UserRepository.cs` if a new repo method is needed

## Known Pitfalls

- Adding a `SendDeactivationEmail` call via `NotificationService` — the task explicitly forbids it
- Adding a new repository method with a broad signature when a minimal one suffices
- Not handling the case where the user doesn't exist
- Duplicating the SQL from `FindByIdAsync` inline in `UserService` instead of using the repository
