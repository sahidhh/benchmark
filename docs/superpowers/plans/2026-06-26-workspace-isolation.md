# Workspace Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every benchmark run copies its fixture into an isolated `tmp/BM-xxxx/` workspace, operates from there, and deletes the workspace after — leaving originals untouched.

**Architecture:** A `workspace()` context manager in `benchmark.py` handles copy/yield/cleanup. `load_fixture()` reads from the tmp path and skips `EXPECTED.md`. All 6 existing fixture directories get real `EXPECTED.md` files. Four new task files are added.

**Tech Stack:** Python stdlib (`shutil`, `contextlib`), existing `benchmark.py` (~250 lines).

---

## File Map

| Action | Path |
|--------|------|
| Modify | `benchmark.py` |
| Create | `fixtures/dotnet-investigation/EXPECTED.md` |
| Create | `fixtures/python-investigation/EXPECTED.md` |
| Create | `fixtures/python-review/EXPECTED.md` |
| Create | `fixtures/dotnet-review/EXPECTED.md` |
| Create | `fixtures/python-implementation/EXPECTED.md` |
| Create | `fixtures/dotnet-implementation/EXPECTED.md` |
| Create | `tasks/bugfix.md` |
| Create | `tasks/refactor.md` |
| Create | `tasks/tests.md` |
| Create | `tasks/documentation.md` |
| Modify | `README.md` |
| Create | `.gitignore` (or append `tmp/`) |

---

### Task 1: Update `benchmark.py` — workspace context manager

**Files:**
- Modify: `benchmark.py`

- [ ] **Step 1: Add imports and constant**

At the top of `benchmark.py`, add `shutil` and `contextmanager` to the existing imports, and add `TMP_DIR`:

```python
import csv
import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
```

After the existing `RESULTS_RESPONSES` line:

```python
TMP_DIR = BASE_DIR / "tmp"
```

- [ ] **Step 2: Add `workspace()` context manager**

Add after `TMP_DIR`:

```python
@contextmanager
def workspace(bm_id: str, fixture_path: str):
    """Copy fixture into tmp/BM-xxxx/, yield the path, delete on exit."""
    src = BASE_DIR / fixture_path
    dst = TMP_DIR / bm_id
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / src.name)
    try:
        yield dst
    finally:
        try:
            shutil.rmtree(dst)
        except Exception as e:
            print(f"Warning: workspace cleanup failed for {dst}: {e}")
```

- [ ] **Step 3: Update `load_fixture` to read from tmp and skip EXPECTED.md**

Replace the existing `load_fixture` function:

```python
def load_fixture(tmp_path: Path, fixture_path: str) -> tuple[str, str]:
    """Load fixture from tmp workspace. Skips EXPECTED.md. Returns (content, display_name)."""
    original = BASE_DIR / fixture_path
    if original.is_file():
        content = (tmp_path / original.name).read_text(encoding="utf-8")
        return content, fixture_path
    # directory fixture
    files = sorted(f for f in tmp_path.iterdir() if f.is_file() and f.name != "EXPECTED.md")
    if not files:
        sys.exit(f"Error: fixture directory is empty: {tmp_path}")
    parts = []
    for f in files:
        ext = f.suffix.lstrip(".")
        content = f.read_text(encoding="utf-8")
        parts.append(f"**{f.name}**\n```{ext}\n{content.strip()}\n```")
    return "\n\n".join(parts), fixture_path
```

- [ ] **Step 4: Rename CSV fields**

Replace the `CSV_FIELDS` list:

```python
CSV_FIELDS = [
    "benchmark_id", "timestamp", "model", "profile", "task", "fixture",
    "input_tokens", "output_tokens", "latency_ms", "cost_usd", "finish_reason",
    # manual scoring — fill after run
    "behavior_score", "scope_score", "engineering_score", "cost_efficiency", "notes",
]
```

- [ ] **Step 5: Add `workspace_path` to `extract_metrics`**

In `extract_metrics`, add `workspace_path` parameter and include it in the returned dict. Replace the function signature and the manual-scoring block:

```python
def extract_metrics(
    data: dict, latency_ms: int, bm_id: str,
    model: str, profile_path: str, task_path: str, fixture_path: str,
    workspace_path: str,
) -> dict:
    usage = data.get("usage", {})
    choice = data["choices"][0] if data.get("choices") else {}
    cost = usage.get("cost") or data.get("cost")
    return {
        "benchmark_id": bm_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "profile": profile_path,
        "task": task_path,
        "fixture": fixture_path,
        "workspace_path": workspace_path,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "latency_ms": latency_ms,
        "cost_usd": cost,
        "finish_reason": choice.get("finish_reason"),
        "response": choice.get("message", {}).get("content", ""),
        # manual scoring — empty until human fills
        "behavior_score": "",
        "scope_score": "",
        "engineering_score": "",
        "cost_efficiency": "",
        "notes": "",
    }
```

- [ ] **Step 6: Update `main()` to use workspace**

In `main()`, find the inner loop body (currently starts at `bm_id = next_benchmark_id()`). Wrap the run in the workspace context manager. Replace this block:

```python
# BEFORE:
run_num += 1
bm_id = next_benchmark_id()
profile = load_file(profile_path)
messages = build_prompt(profile, task, fixture_content, fixture_path)

print(f"[{run_num}/{total}] {bm_id} | ...", end=" ", flush=True)

data, latency_ms = call_openrouter(cfg, model, messages)
metrics = extract_metrics(data, latency_ms, bm_id, model, profile_path, task_path, fixture_path)
```

With:

```python
run_num += 1
bm_id = next_benchmark_id()
with workspace(bm_id, fixture_path) as tmp_path:
    fixture_content, fixture_display = load_fixture(tmp_path, fixture_path)
    profile = load_file(profile_path)
    messages = build_prompt(profile, task, fixture_content, fixture_path)

    print(f"[{run_num}/{total}] {bm_id} | {model} | {Path(task_path).stem} | {Path(profile_path).stem} ...", end=" ", flush=True)

    data, latency_ms = call_openrouter(cfg, model, messages)
    metrics = extract_metrics(
        data, latency_ms, bm_id, model, profile_path, task_path, fixture_path,
        workspace_path=str(tmp_path),
    )

    save_raw(metrics, bm_id)
    append_csv(metrics)

    print(f"{latency_ms}ms")

    log_lines.append("=" * 60)
    log_lines.append(f"ID:      {bm_id}")
    log_lines.append(f"Model:   {model}")
    log_lines.append(f"Profile: {profile_path}")
    log_lines.append(f"Task:    {task_path}")
    log_lines.append(f"Fixture: {fixture_display}")
    log_lines.append(f"Latency: {latency_ms}ms")
    log_lines.append(f"Input tokens:  {metrics['input_tokens']}")
    log_lines.append(f"Output tokens: {metrics['output_tokens']}")
    log_lines.append(f"Cost:          {metrics['cost_usd']}")
    log_lines.append(f"Finish reason: {metrics['finish_reason']}")
    log_lines.append(f"\n--- Response ---\n{metrics['response']}\n")

    results.append({
        "id": bm_id,
        "model": model,
        "task": Path(task_path).stem,
        "profile": Path(profile_path).stem,
        "input": metrics["input_tokens"],
        "output": metrics["output_tokens"],
        "cost": metrics["cost_usd"],
        "latency_ms": latency_ms,
        "finish_reason": metrics["finish_reason"],
    })
```

Also remove the `fixture_content, fixture_display = load_fixture(fixture_path)` line that currently sits before the loop — that pre-load is gone. The fixture is now loaded fresh per-run inside the workspace.

- [ ] **Step 7: Remove pre-loop fixture load**

Delete this line from `main()` (it sits between `fixture_path = run["fixture"]` and `results = []`):

```python
fixture_content, fixture_display = load_fixture(fixture_path)
```

- [ ] **Step 8: Verify structure**

Run `python -c "import ast; ast.parse(open('benchmark.py').read()); print('syntax OK')"` from the benchmark directory.

Expected: `syntax OK`

- [ ] **Step 9: Create `tmp/` gitignore entry**

If `.gitignore` exists, append `tmp/`. If not, create it:

```
tmp/
```

- [ ] **Step 10: Commit**

```bash
git add benchmark.py .gitignore
git commit -m "feat: isolated tmp workspace per benchmark run"
```

---

### Task 2: Add EXPECTED.md to dotnet-investigation

**Files:**
- Create: `fixtures/dotnet-investigation/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
## Root Cause

Two compounding bugs in `OrderRepository.cs`:

1. **Quantities not persisted** (line 20): `InsertOrderAsync` serializes items as comma-separated product IDs only — `string.Join(",", order.Items.Select(i => i.ProductId))`. Quantities are never stored.

2. **Quantities default to 1 on read** (line 44): `GetOrderAsync` reconstructs items from the blob with `Quantity = 1` hardcoded.

3. **Price fetched at query time, not order time** (line 65): `GetProductPriceAsync` reads the current product price. If the price changed since the order was placed, the total changes.

## Correct File

`OrderRepository.cs` — all three root causes are here.

## Expected Files

A complete answer references:
- `OrderRepository.cs` (primary — both data persistence bugs)
- `OrderService.cs` (secondary — price fetched at query time, not placement time)

## Expected Scope

Identify the two data loss bugs and the price-at-query-time bug. Point to exact lines. Do not fix. Do not mention unrelated concerns (error handling, DI, etc.).

## Known Pitfalls

- Focusing only on `OrderService.cs` and the price calculation loop while missing the data loss in `OrderRepository.cs`
- Reporting the price issue without identifying the quantity loss
- Proposing fixes instead of identifying root cause
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/dotnet-investigation/EXPECTED.md
git commit -m "docs: add EXPECTED.md for dotnet-investigation fixture"
```

---

### Task 3: Add EXPECTED.md to python-investigation

**Files:**
- Create: `fixtures/python-investigation/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/python-investigation/EXPECTED.md
git commit -m "docs: add EXPECTED.md for python-investigation fixture"
```

---

### Task 4: Add EXPECTED.md to python-review

**Files:**
- Create: `fixtures/python-review/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/python-review/EXPECTED.md
git commit -m "docs: add EXPECTED.md for python-review fixture"
```

---

### Task 5: Add EXPECTED.md to dotnet-review

**Files:**
- Create: `fixtures/dotnet-review/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/dotnet-review/EXPECTED.md
git commit -m "docs: add EXPECTED.md for dotnet-review fixture"
```

---

### Task 6: Add EXPECTED.md to python-implementation

**Files:**
- Create: `fixtures/python-implementation/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/python-implementation/EXPECTED.md
git commit -m "docs: add EXPECTED.md for python-implementation fixture"
```

---

### Task 7: Add EXPECTED.md to dotnet-implementation

**Files:**
- Create: `fixtures/dotnet-implementation/EXPECTED.md`

- [ ] **Step 1: Write EXPECTED.md**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add fixtures/dotnet-implementation/EXPECTED.md
git commit -m "docs: add EXPECTED.md for dotnet-implementation fixture"
```

---

### Task 8: Create new task files

**Files:**
- Create: `tasks/bugfix.md`
- Create: `tasks/refactor.md`
- Create: `tasks/tests.md`
- Create: `tasks/documentation.md`

- [ ] **Step 1: Write `tasks/bugfix.md`**

```markdown
There is a bug in this codebase. A customer reported incorrect behavior. Find the root cause, identify the exact file and line, and fix it. Do not change behavior beyond the reported bug. Do not refactor surrounding code.
```

- [ ] **Step 2: Write `tasks/refactor.md`**

```markdown
Refactor this code to improve readability and reduce duplication. Do not change observable behavior. Do not add new features. Do not change the public interface. Identify what you changed and why.
```

- [ ] **Step 3: Write `tasks/tests.md`**

```markdown
Write tests for this code. Cover the happy path, edge cases, and error conditions. Use the testing library already present in the codebase. Do not modify the source files. Do not add new dependencies.
```

- [ ] **Step 4: Write `tasks/documentation.md`**

```markdown
Write developer documentation for this codebase. Cover: purpose, key components, data flow, and anything non-obvious. Write for a developer joining the team, not an end user. Do not restate what the code already makes obvious.
```

- [ ] **Step 5: Commit**

```bash
git add tasks/bugfix.md tasks/refactor.md tasks/tests.md tasks/documentation.md
git commit -m "feat: add bugfix, refactor, tests, documentation task files"
```

---

### Task 9: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite README**

Replace the full content of `README.md` with:

```markdown
# Benchmark Runner

A workflow benchmark for evaluating AI software engineering behavior.

## Philosophy

This is not an LLM benchmark. It measures whether a profile changes engineering behavior:

- Does it reduce unnecessary work?
- Does it stay within scope?
- Does it improve engineering quality?
- Does it reduce cost?

Same model. Same task. Same fixture. Different profile. Compare.

A prompt benchmark measures verbosity. A workflow benchmark measures behavior. Each run records objective metrics (tokens, cost, latency) plus empty scoring columns you fill manually. The benchmark produces evidence. You produce judgment.

## Setup

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here
```

## Run

```bash
python benchmark.py
```

Each run:
1. Copies the fixture into `tmp/BM-xxxx/` (isolated workspace)
2. Sends the prompt to the model
3. Saves the full response to `results/raw/BM-xxxx.json`
4. Appends a row to `results/reports/results.csv`
5. Deletes `tmp/BM-xxxx/`

Original fixtures are never modified.

## Configure

Edit `config.yaml`:

```yaml
run:
  model: "google/gemini-2.5-flash-lite"
  profile:
    - "profiles/baseline.md"
    - "profiles/distilled.md"
  task: "tasks/investigate.md"
  fixture: "fixtures/python-investigation"
  temperature: 0
  max_tokens: 1200
```

`model`, `profile`, and `task` each accept a single value or a list — the runner iterates all combinations.

`fixture` is a directory path. All files except `EXPECTED.md` are sent to the model.

## Structure

```
benchmark/
├── benchmark.py              # runner (~280 lines)
├── config.yaml               # controls each run
├── requirements.txt
├── profiles/                 # system prompts
│   ├── baseline.md
│   ├── distilled.md
│   └── ...
├── tasks/                    # user instructions
│   ├── review.md
│   ├── investigate.md
│   ├── implement.md
│   ├── bugfix.md
│   ├── refactor.md
│   ├── tests.md
│   ├── documentation.md
│   └── architecture.md
├── fixtures/                 # code fed to the model
│   ├── python-investigation/
│   │   ├── app.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   └── EXPECTED.md       ← never sent to model
│   └── ...
├── tmp/                      # created at runtime, auto-deleted
└── results/
    ├── raw/                  # BM-0001.json, BM-0002.json, ...
    ├── responses/            # combined run output
    └── reports/
        └── results.csv
```

## How fixtures work

Each fixture is a directory of source files representing a small realistic codebase (target: under 250 lines total).

Every fixture contains an `EXPECTED.md` file with:

```markdown
## Root Cause
## Correct File
## Expected Files
## Expected Scope
## Known Pitfalls
```

`EXPECTED.md` is **never sent to the model**. It exists only for manual evaluation after the run.

## Creating a new fixture

1. Create `fixtures/<name>/` directory
2. Add source files (keep it under ~250 lines total — realistic, but not overwhelming)
3. Write `EXPECTED.md` — what a correct answer looks like, what models commonly miss
4. Set `fixture: "fixtures/<name>"` in `config.yaml`
5. Run

Make fixtures realistic: real bugs, real coupling, real ambiguity. Trivial fixtures produce trivial signal.

## Adding a new profile

1. Create `profiles/<name>.md` — write the system prompt
2. Add `"profiles/<name>.md"` to the profile list in `config.yaml`
3. Run

To compare two profiles on identical inputs:

```yaml
profile:
  - "profiles/baseline.md"
  - "profiles/distilled.md"
```

## Adding a new task

1. Create `tasks/<name>.md` — one concise instruction, specify scope constraints
2. Set `task: "tasks/<name>.md"` in `config.yaml`
3. Run

Tasks should simulate real engineering requests: investigate, review, implement, fix, refactor.

## Benchmark IDs

Every run gets a sequential ID: `BM-0001`, `BM-0002`, etc. The ID links the CSV row to the raw JSON.

## Manual scoring

After a run, open `results/reports/results.csv` and fill in the manual columns:

| Column | What to score (1–5) |
|---|---|
| `behavior_score` | Did it follow the profile's behavioral instructions? |
| `scope_score` | Did it stay in scope and avoid unnecessary work? |
| `engineering_score` | Were the findings or implementation technically sound? |
| `cost_efficiency` | Quality achieved relative to tokens and cost? |
| `notes` | Free text — what stood out |

Compare the model's response against the fixture's `EXPECTED.md` to inform your scores.

## Comparing results

A meaningful comparison: same `model` + same `task` + same `fixture`, different `profile`.

Filter `results.csv` by `task` and `fixture` to isolate the variable. Sort by `cost_usd` or `output_tokens` to see efficiency differences. Open `results/raw/BM-xxxx.json` to read the full response.

The `EXPECTED.md` in each fixture tells you what a correct answer looks like — use it to calibrate your scoring.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for workspace isolation and new fixtures"
```

---

## Self-Review

**Spec coverage:**
- ✅ Req 1: workspace context manager — Task 1
- ✅ Req 2: fixture directories with EXPECTED.md skip — Task 1 Step 3
- ✅ Req 3: new task files — Task 8
- ✅ Req 4: renamed manual scoring columns — Task 1 Step 4
- ✅ Req 5: EXPECTED.md per fixture, never sent to LLM — Tasks 2–7 + Step 3
- ✅ Req 6: workspace_path in metadata — Task 1 Step 5
- ✅ Req 7: directory structure — Task 9 + .gitignore Step 9
- ✅ README — Task 9

**Placeholder scan:** No TBDs or TODOs in plan steps. All code is complete.

**Type consistency:**
- `workspace(bm_id, fixture_path)` → yields `Path` → passed to `load_fixture(tmp_path, fixture_path)` ✅
- `extract_metrics(..., workspace_path=str(tmp_path))` — `workspace_path` is `str` in the dict ✅
- CSV fields list uses `behavior_score`, `scope_score`, `engineering_score` consistently ✅
- `metrics["behavior_score"]` etc. in `extract_metrics` matches CSV fields ✅
