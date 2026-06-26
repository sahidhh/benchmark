# CLAUDE.md

## Setup

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=your_key_here
```

## Run

```bash
python benchmark.py
```

## Architecture

Single-file runner (`benchmark.py`) that composes a prompt from a profile, task, and fixture, sends it to OpenRouter, and records metrics.

**Prompt = profile + task + fixture:**
- `profiles/` — system prompts
- `tasks/` — user instructions
- `fixtures/` — code files (single file or directory)

**Flow:** `config.yaml` → load files → build messages → POST to OpenRouter → write `results/raw/BM-XXXX.json` + append `results/reports/results.csv`

## Config

```yaml
run:
  model: "google/gemini-2.5-flash-lite"
  profile:
    - "profiles/baseline.md"   # list for multi-profile run
  task: "tasks/investigate.md"
  fixture: "fixtures/python-investigation"  # file or directory
  temperature: 0
  max_tokens: 1200
```

## Benchmark IDs

Sequential: BM-0001, BM-0002, ... Derived from count of existing `results/raw/BM-*.json` files.

## CSV columns

Objective: `benchmark_id`, `timestamp`, `model`, `profile`, `task`, `fixture`, `input_tokens`, `output_tokens`, `latency_ms`, `cost_usd`, `finish_reason`

Manual (fill after run): `behavior_compliance`, `scope_discipline`, `engineering_quality`, `cost_efficiency`, `notes`
