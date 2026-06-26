"""Benchmark Runner v0.3 — workflow benchmark for engineering profiles."""

import csv
import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


BASE_DIR = Path(__file__).parent
RESULTS_RAW = BASE_DIR / "results" / "raw"
RESULTS_CSV = BASE_DIR / "results" / "reports" / "results.csv"
RESULTS_RESPONSES = BASE_DIR / "results" / "responses"
TMP_DIR = BASE_DIR / "tmp"


@contextmanager
def workspace(bm_id: str, fixture_path: str):
    """Copy fixture into tmp/BM-xxxx/, yield the path, delete on exit."""
    src = BASE_DIR / fixture_path
    dst = TMP_DIR / bm_id
    if not src.exists():
        sys.exit(f"Error: fixture not found: {src}")
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


CSV_FIELDS = [
    "benchmark_id", "timestamp", "model", "profile", "task", "fixture",
    "input_tokens", "output_tokens", "latency_ms", "cost_usd", "finish_reason",
    # manual scoring — fill after run
    "behavior_score", "scope_score", "engineering_score", "cost_efficiency", "notes",
]


def load_config() -> dict:
    with open(BASE_DIR / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    api_key = cfg["openrouter"]["api_key"]
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var, "")
        if not api_key:
            sys.exit(f"Error: env var {env_var} not set")
        cfg["openrouter"]["api_key"] = api_key
    return cfg


def load_file(path: str) -> str:
    p = BASE_DIR / path
    if not p.exists():
        sys.exit(f"Error: file not found: {p}")
    return p.read_text(encoding="utf-8")


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


def build_prompt(profile: str, task: str, fixture_content: str, fixture_path: str) -> list[dict]:
    p = Path(fixture_path)
    # for single file inject as code block; for dir content is already formatted
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


def call_openrouter(cfg: dict, model: str, messages: list[dict]) -> tuple[dict, int]:
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

    start = time.monotonic()
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    latency_ms = round((time.monotonic() - start) * 1000)

    if not resp.ok:
        sys.exit(f"OpenRouter error {resp.status_code}: {resp.text}")

    return resp.json(), latency_ms


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
    cfg = load_config()
    run = cfg["run"]

    models = run["model"] if isinstance(run["model"], list) else [run["model"]]
    profile_paths = run["profile"] if isinstance(run["profile"], list) else [run["profile"]]
    task_paths = run["task"] if isinstance(run["task"], list) else [run["task"]]
    fixture_path = run["fixture"]

    results = []
    log_lines = []  # accumulated verbose output saved to responses file

    total = len(models) * len(task_paths) * len(profile_paths)
    run_num = 0

    for model in models:
        for task_path in task_paths:
            task = load_file(task_path)
            for profile_path in profile_paths:
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

    # summary table (always, even single run)
    summary_lines = []
    summary_lines.append("\n## Summary\n")
    summary_lines.append("| ID       | Model                          | Task                 | Profile              | Input | Output | Latency |     Cost | Finish  |")
    summary_lines.append("|----------|--------------------------------|----------------------|----------------------|------:|-------:|--------:|---------:|---------|")
    for r in results:
        cost = f"${r['cost']:.4f}" if r["cost"] else "-"
        summary_lines.append(
            f"| {r['id']:<8} | {r['model']:<30} | {r['task']:<20} | {r['profile']:<20} "
            f"| {r['input'] or '-':>5} | {r['output'] or '-':>6} | {r['latency_ms']:>7} | {cost:>8} | {r['finish_reason'] or '-'} |"
        )

    for line in summary_lines:
        print(line)

    # save combined run output
    log_lines.extend(summary_lines)
    resp_file = next_response_file()
    resp_file.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nResponses saved: {resp_file}")


if __name__ == "__main__":
    main()
