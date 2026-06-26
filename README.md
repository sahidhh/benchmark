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
