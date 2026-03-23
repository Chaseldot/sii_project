from __future__ import annotations

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field


OFFLINE_MONITOR_SUMMARY_KEYS = [
    "avg_gpu_mem_gb",
    "peak_gpu_mem_gb",
    "avg_gpu_mem_utilization_perc",
    "peak_gpu_mem_utilization_perc",
    "gpu_total_mem_gb",
    "initial_gpu_mem_gb",
    "final_gpu_mem_gb",
    "monitor_sample_interval_sec",
    "monitor_gpu_samples",
]


def _parse_visible_gpu_indices() -> set[int] | None:
    raw = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if not raw:
        return None
    indices = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if not item.isdigit():
            return None
        indices.add(int(item))
    return indices or None


def query_visible_gpu_memory_stats() -> dict:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
    except Exception:
        return {}

    if not output:
        return {}

    visible = _parse_visible_gpu_indices()
    used_mb_total = 0.0
    total_mb_total = 0.0
    matched = 0
    for line in output.splitlines():
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            gpu_idx = int(parts[0])
            used_mb = float(parts[1])
            total_mb = float(parts[2])
        except ValueError:
            continue
        if visible is not None and gpu_idx not in visible:
            continue
        used_mb_total += used_mb
        total_mb_total += total_mb
        matched += 1

    if matched == 0:
        return {}

    used_gb = used_mb_total / 1024.0
    total_gb = total_mb_total / 1024.0
    stats = {
        "gpu_mem_gb": used_gb,
        "gpu_total_mem_gb": total_gb,
    }
    if total_gb > 0:
        stats["gpu_mem_utilization_perc"] = used_gb / total_gb
    return stats


def summarize_gpu_monitor_samples(
    gpu_mem_samples_gb: list[float],
    gpu_mem_utilization_samples: list[float],
    gpu_total_mem_gb: float | None,
    sample_interval_sec: float,
) -> dict:
    summary = {}
    if gpu_mem_samples_gb:
        summary["avg_gpu_mem_gb"] = round(sum(gpu_mem_samples_gb) / len(gpu_mem_samples_gb), 4)
        summary["peak_gpu_mem_gb"] = round(max(gpu_mem_samples_gb), 4)
        summary["initial_gpu_mem_gb"] = round(gpu_mem_samples_gb[0], 4)
        summary["final_gpu_mem_gb"] = round(gpu_mem_samples_gb[-1], 4)
    if gpu_mem_utilization_samples:
        summary["avg_gpu_mem_utilization_perc"] = round(
            sum(gpu_mem_utilization_samples) / len(gpu_mem_utilization_samples),
            4,
        )
        summary["peak_gpu_mem_utilization_perc"] = round(max(gpu_mem_utilization_samples), 4)
    if gpu_total_mem_gb is not None:
        summary["gpu_total_mem_gb"] = round(gpu_total_mem_gb, 4)
    summary["monitor_sample_interval_sec"] = sample_interval_sec
    summary["monitor_gpu_samples"] = len(gpu_mem_samples_gb)

    ordered = {}
    for key in OFFLINE_MONITOR_SUMMARY_KEYS:
        if key in summary:
            ordered[key] = summary[key]
    return ordered


@dataclass
class OfflineGpuMonitor:
    sample_interval_sec: float = 0.5
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    gpu_mem_samples_gb: list[float] = field(default_factory=list, init=False)
    gpu_total_mem_gb: float | None = field(default=None, init=False)
    gpu_mem_utilization_samples: list[float] = field(default_factory=list, init=False)

    def _sample_once(self) -> None:
        stats = query_visible_gpu_memory_stats()
        if "gpu_mem_gb" in stats:
            self.gpu_mem_samples_gb.append(stats["gpu_mem_gb"])
        if "gpu_total_mem_gb" in stats and self.gpu_total_mem_gb is None:
            self.gpu_total_mem_gb = stats["gpu_total_mem_gb"]
        if "gpu_mem_utilization_perc" in stats:
            self.gpu_mem_utilization_samples.append(stats["gpu_mem_utilization_perc"])

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._sample_once()
            time.sleep(self.sample_interval_sec)

    def start(self) -> None:
        self._stop_event.clear()
        self._sample_once()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.sample_interval_sec * 2)
        self._sample_once()
        return summarize_gpu_monitor_samples(
            gpu_mem_samples_gb=self.gpu_mem_samples_gb,
            gpu_mem_utilization_samples=self.gpu_mem_utilization_samples,
            gpu_total_mem_gb=self.gpu_total_mem_gb,
            sample_interval_sec=self.sample_interval_sec,
        )
