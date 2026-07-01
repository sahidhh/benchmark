---
name: score-benchmark-results
description: Fill the manual scoring columns for a completed benchmark run and propagate the conclusion into tier/routing docs. Use after python benchmark.py has produced new rows in results/reports/results.csv that need behavior_compliance, scope_discipline, engineering_quality, cost_efficiency, and notes filled in.
---

# Score a benchmark run

The CSV's objective columns (`benchmark_id`, tokens, latency, cost,
`finish_reason`) are filled automatically by `benchmark.py`. The manual
columns require reading the actual model output and judging it — that's
this skill.

## 1. Gather the evidence for each row to score

For each `benchmark_id`:
- Read `results/raw/BM-XXXX.json` (full request/response + metadata).
- Read the matching file in `results/responses/` for the raw completion text.
- Read the `fixture` and `task` that were used, and — critically — find or ask
  for the **ground truth** for that fixture (e.g. the "Ground truth for
  scoring" section in `docs/T1-T2-BENCHMARK-PLAN.md` for
  `dotnet-investigation` / `dotnet-review`). Never score
  `engineering_quality` from vibes when a ground truth exists — compare
  claim-by-claim.

## 2. Score each column (fill in `results/reports/results.csv`)

- **behavior_compliance** — did the model follow the *profile's* instructions
  (tone, scope, what it was told not to do — e.g. `investigate.md`'s
  fixtures literally say "do not fix it")? Not about correctness.
- **scope_discipline** — did it stay inside the task's boundary (e.g. an
  investigation task that also rewrites code is a scope violation even if
  the analysis is correct)?
- **engineering_quality** — did it find the *actual* root cause / *all* the
  real issues in the ground truth, not just plausible-sounding ones? Partial
  credit for partial matches; check off each ground-truth item found.
- **cost_efficiency** — relative to the row's `cost_usd`/`latency_ms` and
  what comparable models scored on the same fixture — not an absolute
  judgment in isolation.
- **notes** — short, specific: what it got right/wrong, quoting the
  disqualifying line if there's a scope or compliance miss.

A row with `finish_reason` other than `stop` (truncated, length-limited) is
usually not valid evidence for a tier decision — say so in notes rather than
scoring it as if it completed normally.

## 3. Apply the evidence threshold before concluding anything

Per `docs/T1-T2-BENCHMARK-PLAN.md`'s pattern: don't reassign a tier or draw a
conclusion off one run. The stated bar there is `>= 3 clean stop finishes`
per model with `behavior_compliance >= 2` and `engineering_quality >= 2` on
all of them. Apply the same discipline to any tier this repo is evaluating —
count clean runs before concluding.

## 4. Propagate the conclusion (only if the evidence bar above is met)

In order:
1. `results/reports/results.csv` — scoring columns (done in step 2).
2. `docs/EVIDENCE-LOG.md` — append an entry following the existing
   T3/T4 entry template if that file exists in this repo; if it doesn't
   exist yet, ask the user before creating a new doc structure.
3. Tier-to-model mappings referenced from this repo's docs (e.g. a
   `05-runtimes/opencode/README.md`-style mapping) — only if the run changes
   a tier assignment.
4. Routing rules referenced from this repo's docs — only if a T2 (or other
   tier) model assignment actually changed as a result.

Steps 3-4 touch files outside this repo in some setups — if they're not
reachable in the current session, tell the user explicitly what still needs
updating instead of skipping silently.
