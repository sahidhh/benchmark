"""Benchmark Runner v0.5 — workflow benchmark for engineering profiles.

CLI overrides (all optional — config.yaml used as base):
  --model MODEL         Override model (or comma-separated list)
  --profile PROFILE     Override profile path (or comma-separated list)
  --task TASK           Override task path (or comma-separated list)
  --fixture FIXTURE     Override fixture path
  --provider PROVIDER   Pin OpenRouter provider (e.g. 'Fireworks', 'Together')
  --max-tokens N        Override max_tokens
  --config CONFIG       Use alternate config file (default: config.yaml)
  --dry-run             Print matrix without running

Notes:
  - Gemini BYOK runs show cost_usd=0 (charged to your Google key). Check
    OpenRouter activity CSV for byok_usage_inference to get real cost.
  - DeepSeek-r1 tokens_reasoning shows hidden thinking tokens you are billed for.

Examples:
  python benchmark.py --model google/gemini-2.5-flash --task tasks/investigate.md
  python benchmark.py --config config-t2-review.yaml --model google/gemini-2.5-flash --max-tokens 2500
  python benchmark.py --model anthropic/claude-sonnet-4-6 --dry-run
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


BASE_DIR = Path(__file__).parent
RESULTS_RAW = BASE_DIR / "results" / "raw"
RESULTS_CSV = BASE_DIR / "results" / "reports" / "results.csv"
RESULTS_RESPONSES = BASE_DIR / "results" / "responses"

CSV_FIELDS = [
    "benchmark_id", "timestamp", "model", "provider", "profile", "task", "fixture",
    "input_tokens", "output_tokens", "tokens_reasoning", "latency_ms", "cost_usd",
    "finish_reason",
    "behavior_compliance", "scope_discipline", "engineering_quality", "cost_efficiency", "notes",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Runner v0.5")
    p.add_argument("--model",      help="Model(s) comma-separated to override config")
    p.add_argument("--profile",    help="Profile path(s) comma-separated")
    p.add_argument("--task",       help="Task path(s) comma-separated")
    p.add_argument("--fixture",    help="Fixture path")
    p.add_argument("--provider",   help="Pin OpenRouter provider (e.g. Fireworks, Together)")
    p.add_argument("--max-tokens", type=int, dest="max_tokens", help="Override max_tokens")
    p.add_argument("--config",     default="config.yaml", help="Config file")
    p.add_argument("--dry-run",    action="store_true", help="Print matrix without executing")
    return p.parse_args()


def load_config(config_file: str = "config.yaml") -> dict:
    with open(BASE_DIR / config_file) as f:
        cfg = yaml.safe_load(f)
    api_key = cfg["openrouter"]["api_key"]
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, "")
        if not api_key:
            sys.exit(f"Error: env var {env_var} not set")
        cfg["openrouter"]["api_key"] = api_key
    return cfg


def apply_cli_overrides(cfg: dict, args: argparse.Namespace) -> dict:
    run = cfg.setdefault("run", {})
    if args.model:
        run["model"] = [m.strip() for m in args.model.split(",")]
    if args.profile:
        run["profile"] = [p.strip() for p in args.profile.split(",")]
    if args.task:
        run["task"] = [t.strip() for t in args.task.split(",")]
    if args.fixture:
        run["fixture"] = args.fixture
    if args.max_tokens is not None:
        run["max_tokens"] = args.max_tokens
    if args.provider:
        cfg.setdefault("openrouter", {})["provider"] = args.provider
    return cfg


def load_file(path: str) -> str:
    p = BASE_DIR / path
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    return p.read_text(encoding="utf-8")


def load_fixture(fixture_path: str) -> tuple:
    p = BASE_DIR / fixture_path
    if not p.exists():
        sys.exit(f"Error: fixture not found: {p}")
    if p.is_file():
        return p.read_text(encoding="utf-8"), fixture_path
    files = sorted(f for f in p.iterdir() if f.is_file())
    if not files:
        sys.exit(f"Error: fixture directory is empty: {p}")
    parts = []
    for f in files:
        ext = f.suffix.lstrip(".")
        content = f.read_text(encoding="utf-8")
        parts.append(f"**{f.name}**\n```{ext}\n{content.strip()}\n```")
    return "\n\n".join(parts), fixture_path


def build_prompt(profile: str, task: str, fixture_content: str, fixture_path: str) -> list:
    p = Path(fixture_path)
    if (BASE_DIR / fixture_path).is_file():
        ext = p.suffix.lstrip(".")
        code_block = f"```{ext}\n{fixture_content.strip()}\n```"
    else:
        code_block = fixture_content
    user_msg = f"{task.strip()}\n\n{code_block}"
    return [
        {"role": "system", "content": profile.strip()},
        {"role": "user", "content": user_msg},
    ]


def next_benchmark_id() -> str:
    RESULTS_RAW.mkdir(parents=True, exist_ok=True)
    existing = list(RESULTS_RAW.glob("BM-*.json"))
    n = len(existing) + 1
    return f"BM-{n:04d}"


def next_response_file() -> Path:
    RESULTS_RESPONSES.mkdir(parents=True, exist_ok=True)
    n = len(list(RESULTS_RESPONSES.glob("response_*.txt"))) + 1
    return RESULTS_RESPONSES / f"response_{n:03d}.txt"


def call_openrouter(cfg: dict, model: str, messages: list) -> tuple:
    url = cfg["openrouter"]["base_url"].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg['openrouter']['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/benchmark-runner",
        "X-Title": "Benchmark Runner",
    }
    payload = {"model": model, "messages": messages}
    run = cfg.get("run", {})
    if "temperature" in run:
        payload["temperature"] = run["temperature"]
    if "max_tokens" in run:
        payload["max_tokens"] = run["max_tokens"]

    provider = cfg.get("openrouter", {}).get("provider")
    if provider:
        payload["provider"] = {"order": [provider], "allow_fallbacks": False}

    start = time.monotonic()
    resp = requests.post(url, headers=headers, json=payload, timeout=300)
    latency_ms = round((time.monotonic() - start) * 1000)

    if not resp.ok:
        sys.exit(f"OpenRouter error {resp.status_code}: {resp.text}")

    return resp.json(), latency_ms


def extract_metrics(data, latency_ms, bm_id, model, provider, profile_path, task_path, fixture_path):
    usage = data.get("usage", {})
    choice = data["choices"][0] if data.get("choices") else {}
    cost = usage.get("cost") or data.get("cost")
    # reasoning tokens: present for DeepSeek-r1 and other thinking models
    tokens_reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens") \
        or usage.get("reasoning_tokens") \
        or 0
    return {
        "benchmark_id": bm_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provider": provider,
        "profile": profile_path,
        "task": task_path,
        "fixture": fixture_path,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "tokens_reasoning": tokens_reasoning if tokens_reasoning else "",
        "latency_ms": latency_ms,
        "cost_usd": cost,
        "finish_reason": choice.get("finish_reason"),
        "response": choice.get("message", {}).get("content", ""),
        "behavior_compliance": "",
        "scope_discipline": "",
        "engineering_quality": "",
        "cost_efficiency": "",
        "notes": "",
    }


def save_raw(metrics: dict, bm_id: str) -> Path:
    RESULTS_RAW.mkdir(parents=True, exist_ok=True)
    out = RESULTS_RAW / f"{bm_id}.json"
    out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def append_csv(metrics: dict) -> None:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    write_header = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(metrics)


def main():
    args = parse_args()
    cfg = load_config(args.config)
    cfg = apply_cli_overrides(cfg, args)
    run = cfg["run"]

    models = run["model"] if isinstance(run["model"], list) else [run["model"]]
    profile_paths = run["profile"] if isinstance(run["profile"], list) else [run["profile"]]
    task_paths = run["task"] if isinstance(run["task"], list) else [run["task"]]
    fixture_path = run["fixture"]

    fixture_content, fixture_display = load_fixture(fixture_path)
    total = len(models) * len(task_paths) * len(profile_paths)

    if args.dry_run:
        provider_label = cfg.get("openrouter", {}).get("provider", "auto")
        mt = run.get("max_tokens", "config")
        print(f"Dry run -- {total} runs [provider: {provider_label}] [max_tokens: {mt}]\n")
        n = 0
        for model in models:
            for task_path in task_paths:
                for profile_path in profile_paths:
                    n += 1
                    print(f"  [{n}/{total}] {model} | {Path(task_path).stem} | {Path(profile_path).stem}")
        return

    results = []
    log_lines = []
    run_num = 0

    for model in models:
        for task_path in task_paths:
            task = load_file(task_path)
            for profile_path in profile_paths:
                run_num += 1
                bm_id = next_benchmark_id()
                profile = load_file(profile_path)
                messages = build_prompt(profile, task, fixture_content, fixture_path)

                label = f"{Path(task_path).stem} | {Path(profile_path).stem}"
                print(f"[{run_num}/{total}] {bm_id} | {model} | {label} ...", end=" ", flush=True)

                data, latency_ms = call_openrouter(cfg, model, messages)
                provider_used = cfg.get("openrouter", {}).get("provider", "auto")
                metrics = extract_metrics(
                    data, latency_ms, bm_id,
                    model, provider_used, profile_path, task_path, fixture_path,
                )

                save_raw(metrics, bm_id)
                append_csv(metrics)

                reasoning_note = f" [reasoning: {metrics['tokens_reasoning']}]" if metrics["tokens_reasoning"] else ""
                print(f"{latency_ms}ms{reasoning_note}")

                log_lines.append("=" * 60)
                log_lines.append(f"ID:       {bm_id}")
                log_lines.append(f"Model:    {model}")
                log_lines.append(f"Provider: {provider_used}")
                log_lines.append(f"Profile:  {profile_path}")
                log_lines.append(f"Task:     {task_path}")
                log_lines.append(f"Fixture:  {fixture_display}")
                log_lines.append(f"Latency:  {latency_ms}ms")
                log_lines.append(f"Input:    {metrics['input_tokens']} tokens")
                log_lines.append(f"Output:   {metrics['output_tokens']} tokens")
                log_lines.append(f"Reasoning:{metrics['tokens_reasoning']} tokens")
                log_lines.append(f"Cost:     {metrics['cost_usd']} (Gemini BYOK: check openrouter activity)")
                log_lines.append(f"Finish:   {metrics['finish_reason']}")
                log_lines.append(f"\n--- Response ---\n{metrics['response']}\n")

                results.append({
                    "id": bm_id,
                    "model": model,
                    "provider": provider_used,
                    "task": Path(task_path).stem,
                    "profile": Path(profile_path).stem,
                    "input": metrics["input_tokens"],
                    "output": metrics["output_tokens"],
                    "reasoning": metrics["tokens_reasoning"] or "-",
                    "cost": metrics["cost_usd"],
                    "latency_ms": latency_ms,
                    "finish_reason": metrics["finish_reason"],
                })

    summary_lines = ["\n## Summary\n"]
    hdr = "| ID       | Model                     | Prov | Task           | Profile        | In  | Out | Reason | Lat(ms) | Cost     | Finish |"
    sep = "|----------|---------------------------|------|----------------|----------------|----:|----:|-------:|--------:|---------:|--------|"
    summary_lines.extend([hdr, sep])
    for r in results:
        cost = f"${r['cost']:.4f}" if r["cost"] else "BYOK"
        row = (
            f"| {r['id']:<8} | {r['model']:<25} | {r['provider']:<4} | {r['task']:<14} | "
            f"{r['profile']:<14} | {str(r['input'] or '-'):>3} | {str(r['output'] or '-'):>3} | "
            f"{str(r['reasoning']):>6} | {r['latency_ms']:>7} | {cost:>8} | {r['finish_reason'] or '-'} |"
        )
        summary_lines.append(row)

    for line in summary_lines:
        print(line)

    log_lines.extend(summary_lines)
    resp_file = next_response_file()
    resp_file.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nResponses saved: {resp_file}")


if __name__ == "__main__":
    main()
