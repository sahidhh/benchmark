# Benchmark Runner v0.2

A workflow benchmark for AI engineering profiles.

## Purpose

This is **not** an LLM benchmark. It measures whether a profile changes engineering behavior:

- Does it reduce unnecessary work?
- Does it stay within scope?
- Does it improve engineering quality?
- Does it reduce cost?

Same model. Same task. Same fixture. Different profile. Compare.

## Philosophy

A prompt benchmark measures verbosity. A workflow benchmark measures behavior.

Each run records objective metrics (tokens, cost, latency) plus empty scoring columns you fill manually. The benchmark produces evidence. You produce judgement.

## Setup

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here
```

## Run

```bash
python benchmark.py
```

Each run appends a row to `results/reports/results.csv` and saves the full response to `results/raw/BM-XXXX.json`.

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

`profile` accepts a single path or a list — runs one profile after another.

`fixture` accepts a file path or a directory. For directories, all files are loaded and formatted as named code blocks in the prompt.

## Structure

```
benchmark/
├── benchmark.py              # runner (~200 lines)
├── config.yaml               # controls each run
├── requirements.txt
├── profiles/                 # system prompts (what the model acts as)
│   ├── baseline.md
│   ├── distilled.md
│   └── ...
├── tasks/                    # user instructions (what to do with the fixture)
│   ├── review.md
│   ├── investigate.md
│   ├── implement.md
│   └── architecture.md
├── fixtures/                 # code fed to the model
│   ├── python-review/        # single-file review scenario
│   │   └── main.py
│   ├── python-investigation/ # multi-file investigation scenario
│   │   ├── app.py
│   │   ├── database.py
│   │   └── auth.py
│   └── python-implementation/ # buggy code + tests to pass
│       ├── app.py
│       └── tests.py
└── results/
    ├── raw/                  # BM-0001.json, BM-0002.json, ...
    └── reports/
        └── results.csv
```

## Benchmark IDs

Every run gets a sequential ID: `BM-0001`, `BM-0002`, etc. The ID links the CSV row to the raw JSON.

## Adding a new profile

1. Create `profiles/<name>.md` — write the system prompt.
2. Set `profile: "profiles/<name>.md"` in `config.yaml` (or add to the list).
3. Run.

To compare two profiles on identical inputs, list both:

```yaml
profile:
  - "profiles/baseline.md"
  - "profiles/distilled.md"
```

## Adding a new task

1. Create `tasks/<name>.md` — write the user instruction.
2. Set `task: "tasks/<name>.md"` in `config.yaml`.
3. Run.

Tasks should simulate real engineering requests: investigate, review, implement, plan.

## Adding a new fixture

**Single file:**

```
fixtures/my-scenario/main.py
```

Set `fixture: "fixtures/my-scenario/main.py"`.

**Multi-file (directory):**

```
fixtures/my-scenario/
  service.py
  repository.py
  tests.py
```

Set `fixture: "fixtures/my-scenario"`. All files are loaded and sent as named code blocks.

Make fixtures realistic: real bugs, real coupling, real ambiguity. Trivial fixtures produce trivial signal.

## Scoring

After a run, open `results/reports/results.csv` and fill in the manual columns:

| Column | What to score (1–5) |
|---|---|
| `behavior_compliance` | Did it follow the profile's instructions? |
| `scope_discipline` | Did it avoid unnecessary work and stay in scope? |
| `engineering_quality` | Were the findings or implementation technically sound? |
| `cost_efficiency` | Quality achieved relative to tokens and cost spent? |
| `notes` | Free text — what stood out |

## Comparing results

Filter `results.csv` by `task` and `fixture` to isolate the variable (profile). Sort by `cost_usd` or `output_tokens` to see efficiency differences. Read raw JSON to compare response quality directly.

A meaningful comparison: same `model` + same `task` + same `fixture`, different `profile`.
