from __future__ import annotations

import json
import subprocess
import threading
import time
import urllib.request
from dataclasses import dataclass, field

import numpy as np


def query_gpu_memory_gb() -> float | None:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
    except Exception:
        return None

    if not output:
        return None
    first_line = output.splitlines()[0].strip()
    try:
        return float(first_line) / 1024.0
    except ValueError:
        return None


def query_vllm_metrics(base_url: str) -> dict:
    metrics = {}
    try:
        with urllib.request.urlopen(f"{base_url}/metrics", timeout=2) as resp:
            content = resp.read().decode("utf-8")
    except Exception:
        return metrics

    for line in content.splitlines():
        if line.startswith("vllm:kv_cache_usage_perc"):
            try:
                metrics["kv_cache_usage_perc"] = float(line.split()[-1])
            except ValueError:
                pass
        elif line.startswith("vllm:num_requests_waiting"):
            try:
                metrics["num_requests_waiting"] = float(line.split()[-1])
            except ValueError:
                pass
        elif line.startswith("vllm:num_requests_running"):
            try:
                metrics["num_requests_running"] = float(line.split()[-1])
            except ValueError:
                pass
    return metrics


@dataclass
class OnlineExperimentMonitor:
    base_url: str
    sample_interval_sec: float = 0.5
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    gpu_mem_samples_gb: list[float] = field(default_factory=list, init=False)
    kv_cache_usage_samples: list[float] = field(default_factory=list, init=False)
    waiting_request_samples: list[float] = field(default_factory=list, init=False)
    running_request_samples: list[float] = field(default_factory=list, init=False)

    def _sample_once(self) -> None:
        mem_gb = query_gpu_memory_gb()
        if mem_gb is not None:
            self.gpu_mem_samples_gb.append(mem_gb)

        metrics = query_vllm_metrics(self.base_url)
        if "kv_cache_usage_perc" in metrics:
            self.kv_cache_usage_samples.append(metrics["kv_cache_usage_perc"])
        if "num_requests_waiting" in metrics:
            self.waiting_request_samples.append(metrics["num_requests_waiting"])
        if "num_requests_running" in metrics:
            self.running_request_samples.append(metrics["num_requests_running"])

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
        return self.summary()

    def summary(self) -> dict:
        def summarize(samples: list[float], prefix: str) -> dict:
            if not samples:
                return {}
            return {
                f"avg_{prefix}": round(float(np.mean(samples)), 4),
                f"max_{prefix}": round(float(np.max(samples)), 4),
            }

        summary = {}
        if self.gpu_mem_samples_gb:
            summary["avg_gpu_mem_gb"] = round(float(np.mean(self.gpu_mem_samples_gb)), 4)
            summary["peak_gpu_mem_gb"] = round(float(np.max(self.gpu_mem_samples_gb)), 4)
        if self.kv_cache_usage_samples:
            summary["avg_kv_cache_usage_perc"] = round(float(np.mean(self.kv_cache_usage_samples)), 4)
            summary["max_kv_cache_usage_perc"] = round(float(np.max(self.kv_cache_usage_samples)), 4)
        if self.waiting_request_samples:
            summary["avg_num_requests_waiting"] = round(float(np.mean(self.waiting_request_samples)), 4)
            summary["max_num_requests_waiting"] = round(float(np.max(self.waiting_request_samples)), 4)
        if self.running_request_samples:
            summary["avg_num_requests_running"] = round(float(np.mean(self.running_request_samples)), 4)
            summary["max_num_requests_running"] = round(float(np.max(self.running_request_samples)), 4)
        summary["monitor_sample_interval_sec"] = self.sample_interval_sec
        summary["monitor_gpu_samples"] = len(self.gpu_mem_samples_gb)
        summary["monitor_kv_samples"] = len(self.kv_cache_usage_samples)
        return summary
