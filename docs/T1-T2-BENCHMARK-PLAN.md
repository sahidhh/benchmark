# T1/T2 Benchmark Plan

**Status:** Planned — not yet run
**Next BM IDs:** BM-0075+
**Purpose:** Convert T1 and T2 from heuristic to evidence-based assignments

---

## Why T1/T2 are still heuristic

BM-0045-0074 ran an implement task against 6 models. The investigation and reviewer
profiles were included but run on an implementation task -- a mismatch. That data shows
"what happens when a profile conflicts with its task", not how the profile performs
on its own matched task. Invalid for tier assignment.

T1 was never benchmarked at all (no schema/security fixtures existed).

---

## T2 -- High Reasoning

### What to run

```bash
# Investigation runs (6 runs: 3 models x 2 profiles)
python benchmark.py --config config-t2-investigate.yaml

# Review runs (6 runs: 3 models x 2 profiles)
python benchmark.py --config config-t2-review.yaml
```

Models under test:
- anthropic/claude-sonnet-4-6  -- incumbent (heuristic T2)
- google/gemini-2.5-flash      -- challenger (T3-adjacent, costs less)
- deepseek/deepseek-r1         -- challenger (strong reasoning)

### Evidence threshold to reassign T2

- >= 3 clean stop finishes per model
- behavior_compliance >= 2 on all runs (model followed the profile)
- engineering_quality >= 2 on all runs (model found the real root cause / bugs)
- If a cheaper model meets threshold and Sonnet does not outperform it: reassign T2

### Ground truth for scoring

dotnet-investigation (correct answer):
1. OrderRepository.InsertOrderAsync -- quantities not persisted (blob stores ProductId only)
2. OrderRepository.GetOrderAsync -- quantities reconstructed as 1 on read
3. OrderRepository.GetProductPriceAsync -- fetches CURRENT price, not price at order time
   Root cause: total changes over time because price is read at calculation, not stored at placement

dotnet-review (correct answer):
1. CRITICAL: SQL injection in GetByEmail (string interpolation)
2. CRITICAL: SQL injection in UpdateRole (string interpolation)
3. HIGH: UpdateRole has no rowcount check -- silently succeeds on missing userId
4. MEDIUM: DeactivateUser opens second connection while GetUserById already holds one
5. PATTERN: No parameterized queries anywhere in the class

---

## T1 -- Frontier

Blocked: needs new fixtures (schema migration, security audit, DB invariant).
These require deliberate construction around irreversible or high-stakes operations.

New fixtures needed:
- fixtures/dotnet-schema-migration/ -- migration adding NOT NULL column to existing table
- fixtures/dotnet-security-audit/   -- auth token refresh with subtle credential flaw

New tasks needed:
- tasks/schema-migration.md  -- "Add this column safely. We have 8M rows in prod."
- tasks/security-audit.md    -- "Review this auth flow for credential exposure risks."

Models: claude-opus-4-8 (incumbent) vs claude-sonnet-4-6 (is T1 overkill?)
Evidence threshold: engineering_quality = 3 required (no partial credit for T1 tasks).

---

## Quantization control (open-weight models only)

When benchmarking DeepSeek or Qwen variants, pin the provider:

  python benchmark.py --config config-t2-investigate.yaml --provider Fireworks

Log the provider used in the notes column. Without pinning, OpenRouter may route
the same model to different quantization levels between runs, making results incomparable.

---

## Timeline

| Phase              | Config                      | Runs | Est. cost | Status   |
|--------------------|-----------------------------|-----:|----------:|----------|
| T2 investigation   | config-t2-investigate.yaml  |    6 | ~$0.005   | Ready    |
| T2 review          | config-t2-review.yaml       |    6 | ~$0.005   | Ready    |
| T1 schema/security | (fixtures needed first)     |    6 | ~$0.010   | Blocked  |

---

## After running

1. Fill scoring columns in results/reports/results.csv
2. Update docs/EVIDENCE-LOG.md with results (follow the T3/T4 entry template)
3. Update tier-to-model mappings in 05-runtimes/opencode/README.md if tier changes
4. If T2 model changes, update routing rules in 04-routing/routing-rules.md
