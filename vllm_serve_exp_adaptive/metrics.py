from __future__ import annotations

import json
import urllib.request


def query_vllm_metrics(base_url: str, timeout_sec: float = 2.0) -> dict:
    metrics = {}
    try:
        with urllib.request.urlopen(f"{base_url}/metrics", timeout=timeout_sec) as resp:
            content = resp.read().decode("utf-8")
    except Exception:
        return metrics

    for line in content.splitlines():
        if not line.startswith("vllm:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        metric_name = parts[0].split(":", maxsplit=1)[1].split("{", maxsplit=1)[0]
        try:
            metric_value = float(parts[-1])
        except ValueError:
            continue

        if metric_name in ("kv_cache_usage_perc", "gpu_cache_usage_perc"):
            metrics["kv_cache_usage_perc"] = metric_value
        elif metric_name == "num_requests_waiting":
            metrics["num_requests_waiting"] = metric_value
        elif metric_name == "num_requests_running":
            metrics["num_requests_running"] = metric_value
        elif metric_name == "num_requests_swapped":
            metrics["num_requests_swapped"] = metric_value
    return metrics


def save_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
