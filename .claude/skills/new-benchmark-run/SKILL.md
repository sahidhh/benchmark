---
name: new-benchmark-run
description: Set up and execute a new benchmark matrix (models x profiles x tasks x fixture) for this repo, then summarize the resulting rows. Use when the user wants to benchmark a profile/task/model combination, add a new config file, or compare models on a fixture.
---

# Run a new benchmark matrix

`benchmark.py` composes `system prompt (profile) + user instruction (task) +
code (fixture)`, posts it to OpenRouter, and appends one row per run to
`results/reports/results.csv` plus a raw JSON to `results/raw/BM-XXXX.json`.

## 1. Decide config vs CLI flags

- One-off / exploratory run → use CLI overrides, don't create a file:
  `python benchmark.py --model <m1,m2> --profile <p1,p2> --task <t> --fixture <f>`
- A run worth reproducing or referencing later (e.g. a tier-evidence run like
  `config-t2-review.yaml`) → create `config-<name>.yaml` modeled on the
  existing `config.yaml` / `config-t2-*.yaml` files:
  ```yaml
  openrouter:
    api_key: "${OPENROUTER_API_KEY}"
    base_url: "https://openrouter.ai/api/v1"
  run:
    model: [...]      # list = cartesian product across profile/task
    profile: [...]
    task: "tasks/<x>.md"
    fixture: "fixtures/<x>"
    temperature: 0
    max_tokens: 1200
  ```

## 2. Check for existing profiles/tasks/fixtures first

Before writing a new `profiles/*.md`, `tasks/*.md`, or `fixtures/*` — list
what's already there (`profiles/`, `tasks/`, `fixtures/`) and reuse if it
fits. Don't duplicate a near-identical profile/task; benchmark comparisons
only mean something if the non-varied inputs are exactly shared across runs.

If a genuinely new fixture/task is needed (e.g. for an untested tier per
`docs/T1-T2-BENCHMARK-PLAN.md`), write:
- the fixture as realistic code with a **deliberately seeded, specific bug**
  (see `fixtures/dotnet-investigation/` for the pattern: a bug that requires
  tracing across 2-3 files, not a single obvious line), and
- a **ground-truth answer** for it, recorded in `docs/` before running anything
  — scoring without a pre-committed ground truth is not evidence.

## 3. Dry-run first

`python benchmark.py --config <config> --dry-run` — confirm the matrix
(model x profile x task count) is what's intended before spending tokens,
especially for list-valued `model`/`profile`/`task` (cartesian product).

## 4. Execute

`python benchmark.py --config <config>` (or with CLI overrides). Note from
the module docstring:
- Gemini BYOK runs show `cost_usd=0` — real cost is on the Google key, check
  OpenRouter's activity CSV separately if it matters.
- DeepSeek-r1 `tokens_reasoning` reflects hidden thinking tokens still billed.
- Non-`stop` `finish_reason` (e.g. truncation) invalidates that row for
  tier-evidence purposes — flag it, don't quietly count it.

## 5. Summarize

Read the new rows appended to `results/reports/results.csv` (they're the last
N rows, N = matrix size) and report: model, profile, task, tokens, latency,
cost, finish_reason — plus the new `BM-XXXX` IDs so the user can find the raw
JSON/response text under `results/raw/` and `results/responses/`.

Don't fill in the manual scoring columns yourself here — that's a separate,
judgment-heavy pass (see the `score-benchmark-results` skill).
