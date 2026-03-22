from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .metrics import query_vllm_metrics


@dataclass
class AdmissionConfig:
    backend_base_url: str
    kv_cache_high_watermark: float = 0.85
    waiting_high_watermark: int = 128
    running_high_watermark: int = 128
    max_proxy_inflight: int = 128
    poll_interval_sec: float = 0.05
    max_gate_wait_sec: float = 300.0


@dataclass
class AdaptiveAdmissionController:
    config: AdmissionConfig
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _current_inflight: int = field(default=0, init=False)
    _total_requests: int = field(default=0, init=False)
    _delayed_requests: int = field(default=0, init=False)
    _total_gate_wait_sec: float = field(default=0.0, init=False)
    _max_gate_wait_sec: float = field(default=0.0, init=False)
    _last_gate_reason: str = field(default="startup", init=False)
    _last_backend_metrics: dict = field(default_factory=dict, init=False)

    def _gate_reason(self, metrics: dict) -> str | None:
        kv_usage = metrics.get("kv_cache_usage_perc", 0.0)
        waiting = metrics.get("num_requests_waiting", 0.0)
        running = metrics.get("num_requests_running", 0.0)
        if kv_usage >= self.config.kv_cache_high_watermark:
            return "kv_cache_high"
        if waiting >= self.config.waiting_high_watermark:
            return "waiting_queue_high"
        if running >= self.config.running_high_watermark:
            return "running_slots_high"
        if self._current_inflight >= self.config.max_proxy_inflight:
            return "proxy_inflight_high"
        return None

    def acquire(self) -> dict:
        start = time.perf_counter()
        delayed = False
        last_reason = "unknown"
        last_metrics = {}

        while True:
            metrics = query_vllm_metrics(self.config.backend_base_url)
            with self._lock:
                self._last_backend_metrics = metrics
                reason = self._gate_reason(metrics)
                if reason is None:
                    self._current_inflight += 1
                    self._total_requests += 1
                    gate_wait_sec = time.perf_counter() - start
                    if delayed:
                        self._delayed_requests += 1
                    self._total_gate_wait_sec += gate_wait_sec
                    if gate_wait_sec > self._max_gate_wait_sec:
                        self._max_gate_wait_sec = gate_wait_sec
                    self._last_gate_reason = "admitted"
                    return {
                        "gate_wait_ms": round(gate_wait_sec * 1000, 2),
                        "backend_metrics": metrics,
                    }

            delayed = True
            last_reason = reason
            last_metrics = metrics
            if time.perf_counter() - start >= self.config.max_gate_wait_sec:
                raise TimeoutError(
                    f"Admission wait exceeded {self.config.max_gate_wait_sec}s: "
                    f"reason={last_reason}, metrics={last_metrics}"
                )
            time.sleep(self.config.poll_interval_sec)

    def release(self) -> None:
        with self._lock:
            if self._current_inflight > 0:
                self._current_inflight -= 1

    def snapshot(self) -> dict:
        with self._lock:
            avg_gate_wait_sec = 0.0
            if self._total_requests > 0:
                avg_gate_wait_sec = self._total_gate_wait_sec / self._total_requests
            return {
                "scheduler_policy": "kv_aware_admission_control",
                "backend_base_url": self.config.backend_base_url,
                "kv_cache_high_watermark": self.config.kv_cache_high_watermark,
                "waiting_high_watermark": self.config.waiting_high_watermark,
                "running_high_watermark": self.config.running_high_watermark,
                "max_proxy_inflight": self.config.max_proxy_inflight,
                "poll_interval_sec": self.config.poll_interval_sec,
                "max_gate_wait_sec": self.config.max_gate_wait_sec,
                "scheduler_total_requests": self._total_requests,
                "scheduler_delayed_requests": self._delayed_requests,
                "scheduler_delayed_ratio": round(
                    self._delayed_requests / self._total_requests,
                    4,
                )
                if self._total_requests
                else 0.0,
                "scheduler_current_inflight": self._current_inflight,
                "scheduler_avg_gate_wait_ms": round(avg_gate_wait_sec * 1000, 2),
                "scheduler_max_gate_wait_ms": round(self._max_gate_wait_sec * 1000, 2),
                "scheduler_last_gate_reason": self._last_gate_reason,
                "scheduler_last_backend_metrics": self._last_backend_metrics,
            }
