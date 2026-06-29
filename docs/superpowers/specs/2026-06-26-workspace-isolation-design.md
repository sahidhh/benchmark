# Benchmark Runner — Workspace Isolation Design

Date: 2026-06-26

## Problem

The benchmark runner reads fixtures directly from `fixtures/`. If future agentic runs write files back (tool use, git commits), fixtures get mutated. Even for read-only runs, a copy-on-start contract makes reproducibility explicit and sets the foundation for agentic execution.

## Goal

Every benchmark run operates on an isolated copy of the fixture. Originals never change.

---

## Architecture Changes

### `benchmark.py`

**New constant:**
```python
TMP_DIR = BASE_DIR / "tmp"
```

**New context manager:**
```python
@contextmanager
def workspace(bm_id: str, fixture_path: str):
    src = BASE_DIR / fixture_path
    dst = TMP_DIR / bm_id
    shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst / src.name)
    try:
        yield dst
    finally:
        try:
            shutil.rmtree(dst)
        except Exception as e:
            print(f"Warning: cleanup failed for {dst}: {e}")
```

**`load_fixture(tmp_path)`** — updated signature. Reads from tmp copy. Skips `EXPECTED.md` (exists for manual eval, never sent to LLM).

**`extract_metrics`** — adds `workspace_path` to JSON. Not in CSV (path is gone by the time you read the CSV).

**`main()`** inner loop:
```python
bm_id = next_benchmark_id()
with workspace(bm_id, fixture_path) as tmp_path:
    fixture_content, fixture_display = load_fixture(tmp_path)
    # ... rest of run unchanged
```

**CSV column renames:**
- `behavior_compliance` → `behavior_score`
- `scope_discipline` → `scope_score`
- `engineering_quality` → `engineering_score`

Net: ~+25 lines. Total stays under 300.

---

## Fixture Structure

Every fixture directory contains:

```
fixtures/python-investigation/
    app.py
    database.py
    auth.py
    EXPECTED.md        ← never sent to LLM, human eval only
```

`EXPECTED.md` schema:
```markdown
## Root Cause
What the bug/issue actually is.

## Correct File
Which file(s) contain the root cause.

## Expected Files
Which files a correct answer should reference.

## Expected Scope
What a good-scoped response looks like (what to include, what to skip).

## Known Pitfalls
What a model commonly gets wrong on this fixture.
```

---

## Task Files

Existing: `review.md`, `investigate.md`, `implement.md`, `architecture.md`

New:
- `bugfix.md` — find root cause and fix it (no investigation pause)
- `refactor.md` — restructure without changing behavior
- `tests.md` — write tests for existing code
- `documentation.md` — produce developer docs

All tasks: concise, direct, specify scope constraints.

---

## Directory Structure

```
benchmark/
    benchmark.py
    config.yaml
    profiles/
    tasks/
    fixtures/
        <name>/
            <source files>
            EXPECTED.md
    tmp/               ← created at runtime, gitignored
    results/
    docs/
    README.md
```

---

## Data Flow

```
config.yaml
    → next_benchmark_id() → BM-xxxx
    → workspace(bm_id, fixture_path)
        → copy fixtures/<name>/ to tmp/BM-xxxx/
        → load_fixture(tmp_path)  [skips EXPECTED.md]
        → build prompt
        → POST to OpenRouter
        → extract_metrics  [includes workspace_path in JSON]
        → save_raw BM-xxxx.json
        → append_csv
    → workspace cleanup: rm tmp/BM-xxxx/
```

---

## Invariants

- `fixtures/` is never written to, only read at copy time
- `EXPECTED.md` is never included in any prompt
- Workspace cleanup always runs (try/finally), failure warns but does not crash
- `tmp/` is gitignored
- CSV fields are append-only (no schema migrations mid-file)

---

## Out of Scope

- No automatic scoring
- No database
- No async / parallel execution
- No tool-use execution (workspace is ready for it, runner is not wired yet)
