from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field

import numpy as np


def query_gpu_memory_stats() -> dict:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
    except Exception:
        return {}

    if not output:
        return {}
    first_line = output.splitlines()[0].strip()
    try:
        used_mb_str, total_mb_str = [item.strip() for item in first_line.split(",", maxsplit=1)]
        used_gb = float(used_mb_str) / 1024.0
        total_gb = float(total_mb_str) / 1024.0
    except (ValueError, IndexError):
        return {}

    stats = {
        "gpu_mem_gb": used_gb,
        "gpu_total_mem_gb": total_gb,
    }
    if total_gb > 0:
        stats["gpu_mem_utilization_perc"] = used_gb / total_gb
    return stats


def query_vllm_metrics(base_url: str) -> dict:
    metrics = {}
    try:
        with urllib.request.urlopen(f"{base_url}/metrics", timeout=2) as resp:
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
        elif metric_name == "cpu_cache_usage_perc":
            metrics["cpu_cache_usage_perc"] = metric_value
        elif metric_name == "num_requests_waiting":
            metrics["num_requests_waiting"] = metric_value
        elif metric_name == "num_requests_running":
            metrics["num_requests_running"] = metric_value
        elif metric_name == "num_requests_swapped":
            metrics["num_requests_swapped"] = metric_value
    return metrics


@dataclass
class OnlineExperimentMonitor:
    base_url: str
    sample_interval_sec: float = 0.5
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    gpu_mem_samples_gb: list[float] = field(default_factory=list, init=False)
    gpu_total_mem_gb: float | None = field(default=None, init=False)
    gpu_mem_utilization_samples: list[float] = field(default_factory=list, init=False)
    kv_cache_usage_samples: list[float] = field(default_factory=list, init=False)
    cpu_cache_usage_samples: list[float] = field(default_factory=list, init=False)
    waiting_request_samples: list[float] = field(default_factory=list, init=False)
    running_request_samples: list[float] = field(default_factory=list, init=False)
    swapped_request_samples: list[float] = field(default_factory=list, init=False)

    def _sample_once(self) -> None:
        gpu_stats = query_gpu_memory_stats()
        if "gpu_mem_gb" in gpu_stats:
            self.gpu_mem_samples_gb.append(gpu_stats["gpu_mem_gb"])
        if "gpu_total_mem_gb" in gpu_stats and self.gpu_total_mem_gb is None:
            self.gpu_total_mem_gb = gpu_stats["gpu_total_mem_gb"]
        if "gpu_mem_utilization_perc" in gpu_stats:
            self.gpu_mem_utilization_samples.append(gpu_stats["gpu_mem_utilization_perc"])

        metrics = query_vllm_metrics(self.base_url)
        if "kv_cache_usage_perc" in metrics:
            self.kv_cache_usage_samples.append(metrics["kv_cache_usage_perc"])
        if "cpu_cache_usage_perc" in metrics:
            self.cpu_cache_usage_samples.append(metrics["cpu_cache_usage_perc"])
        if "num_requests_waiting" in metrics:
            self.waiting_request_samples.append(metrics["num_requests_waiting"])
        if "num_requests_running" in metrics:
            self.running_request_samples.append(metrics["num_requests_running"])
        if "num_requests_swapped" in metrics:
            self.swapped_request_samples.append(metrics["num_requests_swapped"])

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._sample_once()
            time.sleep(self.sample_interval_sec)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.sample_interval_sec * 2)
        self._sample_once()
        return self.summary()

    def summary(self) -> dict:
        def summarize(samples: list[float], prefix: str, max_key: str = "max") -> dict:
            if not samples:
                return {}
            return {
                f"min_{prefix}": round(float(np.min(samples)), 4),
                f"avg_{prefix}": round(float(np.mean(samples)), 4),
                f"{max_key}_{prefix}": round(float(np.max(samples)), 4),
            }

        summary = {}
        if self.gpu_mem_samples_gb:
            summary.update(summarize(self.gpu_mem_samples_gb, "gpu_mem_gb", max_key="peak"))
            summary["initial_gpu_mem_gb"] = round(float(self.gpu_mem_samples_gb[0]), 4)
            summary["final_gpu_mem_gb"] = round(float(self.gpu_mem_samples_gb[-1]), 4)
        if self.gpu_total_mem_gb is not None:
            summary["gpu_total_mem_gb"] = round(float(self.gpu_total_mem_gb), 4)
        if self.gpu_mem_utilization_samples:
            summary.update(
                summarize(
                    self.gpu_mem_utilization_samples,
                    "gpu_mem_utilization_perc",
                    max_key="peak",
                )
            )
        if self.kv_cache_usage_samples:
            summary.update(summarize(self.kv_cache_usage_samples, "kv_cache_usage_perc"))
        if self.cpu_cache_usage_samples:
            summary.update(summarize(self.cpu_cache_usage_samples, "cpu_cache_usage_perc"))
        if self.waiting_request_samples:
            summary.update(summarize(self.waiting_request_samples, "num_requests_waiting"))
        if self.running_request_samples:
            summary.update(summarize(self.running_request_samples, "num_requests_running"))
        if self.swapped_request_samples:
            summary.update(summarize(self.swapped_request_samples, "num_requests_swapped"))
        summary["monitor_sample_interval_sec"] = self.sample_interval_sec
        summary["monitor_gpu_samples"] = len(self.gpu_mem_samples_gb)
        summary["monitor_kv_samples"] = len(self.kv_cache_usage_samples)
        summary["monitor_cpu_cache_samples"] = len(self.cpu_cache_usage_samples)
        return summary
