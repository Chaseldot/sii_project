from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class SchedulerConfig:
    policy: str = "length_aware_v4"
    short_threshold_chars: int = 256
    short_weight: int = 2
    long_weight: int = 1
    max_consecutive_short: int = 4
    max_active_requests: int = 64
    max_queue_wait_sec: float = 300.0
    adapt_window_size: int = 128
    adapt_update_interval: int = 64
    min_short_weight: int = 1
    max_short_weight: int = 3
    min_max_consecutive_short: int = 2
    max_max_consecutive_short: int = 6
    objective_short_p95_ttft_ms: float = 45000.0
    constraint_max_long_p95_latency_ms: float = 110000.0
    constraint_max_overall_p95_latency_ms: float = 110000.0


@dataclass
class QueueTicket:
    ticket_id: int
    bucket: str
    prompt_chars: int
    enqueue_time: float
    granted: bool = False
    gate_wait_sec: float = 0.0


@dataclass
class CompletedRecord:
    bucket: str
    prompt_chars: int
    gate_wait_ms: float
    ttft_ms: float
    latency_ms: float
    completed_at: float


@dataclass
class LengthAwareScheduler:
    config: SchedulerConfig
    _condition: threading.Condition = field(
        default_factory=lambda: threading.Condition(threading.Lock()),
        init=False,
    )
    _short_queue: deque[QueueTicket] = field(default_factory=deque, init=False)
    _long_queue: deque[QueueTicket] = field(default_factory=deque, init=False)
    _fifo_queue: deque[QueueTicket] = field(default_factory=deque, init=False)
    _ticket_seq: int = field(default=0, init=False)
    _current_inflight: int = field(default=0, init=False)
    _max_inflight: int = field(default=0, init=False)
    _consecutive_short: int = field(default=0, init=False)
    _dispatch_cycle: tuple[str, ...] = field(default=tuple(), init=False)
    _dispatch_cycle_index: int = field(default=0, init=False)
    _total_requests: int = field(default=0, init=False)
    _bucket_enqueued: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_dispatched: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_completed: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _bucket_max_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _max_queue_depth: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _max_total_queue: int = field(default=0, init=False)
    _last_dispatch_bucket: str = field(default="startup", init=False)
    _current_short_weight: int = field(default=2, init=False)
    _current_max_consecutive_short: int = field(default=4, init=False)
    _recent_completed: deque[CompletedRecord] = field(default_factory=deque, init=False)
    _completed_count: int = field(default=0, init=False)
    _last_window_metrics: dict = field(default_factory=dict, init=False)
    _policy_updates: list[dict] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._current_short_weight = self._clamp(
            int(self.config.short_weight),
            self.config.min_short_weight,
            self.config.max_short_weight,
        )
        self._current_max_consecutive_short = self._clamp(
            int(self.config.max_consecutive_short),
            self.config.min_max_consecutive_short,
            self.config.max_max_consecutive_short,
        )
        self._refresh_dispatch_cycle()

    def classify_prompt(self, prompt: str | list | None) -> tuple[str, int]:
        prompt_chars = self._count_prompt_chars(prompt)
        bucket = "short" if prompt_chars <= self.config.short_threshold_chars else "long"
        return bucket, prompt_chars

    def acquire(self, prompt: str | list | None) -> dict:
        bucket, prompt_chars = self.classify_prompt(prompt)
        enqueue_time = time.perf_counter()
        with self._condition:
            self._ticket_seq += 1
            ticket = QueueTicket(
                ticket_id=self._ticket_seq,
                bucket=bucket,
                prompt_chars=prompt_chars,
                enqueue_time=enqueue_time,
            )
            self._enqueue_locked(ticket)

            deadline = enqueue_time + self.config.max_queue_wait_sec
            while not ticket.granted:
                self._maybe_grant_locked()
                if ticket.granted:
                    break
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    self._remove_ticket_locked(ticket)
                    raise TimeoutError(
                        f"Scheduler wait exceeded {self.config.max_queue_wait_sec}s "
                        f"for policy={self.config.policy}, bucket={bucket}"
                    )
                self._condition.wait(timeout=remaining)

            return {
                "ticket_id": ticket.ticket_id,
                "bucket": bucket,
                "prompt_chars": prompt_chars,
                "gate_wait_ms": round(ticket.gate_wait_sec * 1000, 2),
            }

    def release(
        self,
        ticket: dict | None = None,
        ttft_ms: float | None = None,
        latency_ms: float | None = None,
    ) -> None:
        with self._condition:
            if ticket and ttft_ms is not None and latency_ms is not None:
                self._record_completion_locked(ticket, ttft_ms, latency_ms)
            if self._current_inflight > 0:
                self._current_inflight -= 1
            self._maybe_grant_locked()
            self._condition.notify_all()

    def snapshot(self) -> dict:
        with self._condition:
            def avg_wait(bucket: str) -> float:
                dispatched = self._bucket_dispatched[bucket]
                if dispatched == 0:
                    return 0.0
                return self._bucket_gate_wait_sec[bucket] / dispatched * 1000

            return {
                "scheduler_policy": self.config.policy,
                "short_threshold_chars": self.config.short_threshold_chars,
                "base_short_weight": self.config.short_weight,
                "base_long_weight": self.config.long_weight,
                "base_max_consecutive_short": self.config.max_consecutive_short,
                "current_short_weight": self._current_short_weight,
                "current_long_weight": self.config.long_weight,
                "current_max_consecutive_short": self._current_max_consecutive_short,
                "max_active_requests": self.config.max_active_requests,
                "adapt_window_size": self.config.adapt_window_size,
                "adapt_update_interval": self.config.adapt_update_interval,
                "objective_short_p95_ttft_ms": self.config.objective_short_p95_ttft_ms,
                "constraint_max_long_p95_latency_ms": self.config.constraint_max_long_p95_latency_ms,
                "constraint_max_overall_p95_latency_ms": self.config.constraint_max_overall_p95_latency_ms,
                "scheduler_total_requests": self._total_requests,
                "scheduler_completed_requests": self._completed_count,
                "scheduler_short_enqueued": self._bucket_enqueued["short"],
                "scheduler_long_enqueued": self._bucket_enqueued["long"],
                "scheduler_short_dispatched": self._bucket_dispatched["short"],
                "scheduler_long_dispatched": self._bucket_dispatched["long"],
                "scheduler_short_completed": self._bucket_completed["short"],
                "scheduler_long_completed": self._bucket_completed["long"],
                "scheduler_short_avg_gate_wait_ms": round(avg_wait("short"), 2),
                "scheduler_long_avg_gate_wait_ms": round(avg_wait("long"), 2),
                "scheduler_short_max_gate_wait_ms": round(self._bucket_max_gate_wait_sec["short"] * 1000, 2),
                "scheduler_long_max_gate_wait_ms": round(self._bucket_max_gate_wait_sec["long"] * 1000, 2),
                "scheduler_current_short_queue": len(self._short_queue),
                "scheduler_current_long_queue": len(self._long_queue),
                "scheduler_current_total_queue": self._current_total_queue_locked(),
                "scheduler_max_short_queue": self._max_queue_depth["short"],
                "scheduler_max_long_queue": self._max_queue_depth["long"],
                "scheduler_max_total_queue": self._max_total_queue,
                "scheduler_current_inflight": self._current_inflight,
                "scheduler_max_inflight": self._max_inflight,
                "scheduler_last_dispatch_bucket": self._last_dispatch_bucket,
                "scheduler_last_window_metrics": self._last_window_metrics,
                "scheduler_policy_updates": self._policy_updates[-20:],
            }

    def _count_prompt_chars(self, prompt: str | list | None) -> int:
        if prompt is None:
            return 0
        if isinstance(prompt, str):
            return len(prompt)
        if isinstance(prompt, list):
            total = 0
            for item in prompt:
                if isinstance(item, str):
                    total += len(item)
                elif isinstance(item, dict):
                    total += len(str(item.get("content", "")))
                else:
                    total += len(str(item))
            return total
        return len(str(prompt))

    def _enqueue_locked(self, ticket: QueueTicket) -> None:
        self._total_requests += 1
        self._bucket_enqueued[ticket.bucket] += 1
        self._fifo_queue.append(ticket)
        if ticket.bucket == "short":
            self._short_queue.append(ticket)
        else:
            self._long_queue.append(ticket)
        self._max_queue_depth[ticket.bucket] = max(
            self._max_queue_depth[ticket.bucket],
            len(self._short_queue if ticket.bucket == "short" else self._long_queue),
        )
        self._max_total_queue = max(self._max_total_queue, self._current_total_queue_locked())
        self._maybe_grant_locked()
        self._condition.notify_all()

    def _remove_ticket_locked(self, ticket: QueueTicket) -> None:
        for queue in (self._fifo_queue, self._short_queue, self._long_queue):
            for idx, queued in enumerate(queue):
                if queued.ticket_id == ticket.ticket_id:
                    del queue[idx]
                    break

    def _current_total_queue_locked(self) -> int:
        return len(self._fifo_queue)

    def _maybe_grant_locked(self) -> None:
        while self._current_inflight < self.config.max_active_requests and self._fifo_queue:
            ticket = self._select_next_ticket_locked()
            if ticket is None:
                return
            ticket.granted = True
            ticket.gate_wait_sec = time.perf_counter() - ticket.enqueue_time
            self._bucket_dispatched[ticket.bucket] += 1
            self._bucket_gate_wait_sec[ticket.bucket] += ticket.gate_wait_sec
            self._bucket_max_gate_wait_sec[ticket.bucket] = max(
                self._bucket_max_gate_wait_sec[ticket.bucket],
                ticket.gate_wait_sec,
            )
            self._current_inflight += 1
            self._max_inflight = max(self._max_inflight, self._current_inflight)
            self._last_dispatch_bucket = ticket.bucket
            self._condition.notify_all()

    def _select_next_ticket_locked(self) -> QueueTicket | None:
        if self.config.policy == "fifo":
            ticket = self._fifo_queue.popleft() if self._fifo_queue else None
            if ticket is None:
                return None
            self._remove_from_bucket_queue_locked(ticket)
            if ticket.bucket == "short":
                self._consecutive_short += 1
            else:
                self._consecutive_short = 0
            return ticket
        return self._select_length_aware_ticket_locked()

    def _select_length_aware_ticket_locked(self) -> QueueTicket | None:
        has_short = bool(self._short_queue)
        has_long = bool(self._long_queue)
        if not has_short and not has_long:
            return None
        if has_long and not has_short:
            self._consecutive_short = 0
            ticket = self._long_queue.popleft()
            self._remove_from_fifo_locked(ticket)
            return ticket
        if has_short and not has_long:
            self._consecutive_short += 1
            ticket = self._short_queue.popleft()
            self._remove_from_fifo_locked(ticket)
            return ticket

        if self._consecutive_short >= self._current_max_consecutive_short:
            self._consecutive_short = 0
            ticket = self._long_queue.popleft()
            self._remove_from_fifo_locked(ticket)
            return ticket

        cycle_len = len(self._dispatch_cycle)
        for offset in range(cycle_len):
            idx = (self._dispatch_cycle_index + offset) % cycle_len
            bucket = self._dispatch_cycle[idx]
            queue = self._short_queue if bucket == "short" else self._long_queue
            if queue:
                self._dispatch_cycle_index = (idx + 1) % cycle_len
                ticket = queue.popleft()
                self._remove_from_fifo_locked(ticket)
                if bucket == "short":
                    self._consecutive_short += 1
                else:
                    self._consecutive_short = 0
                return ticket
        return None

    def _remove_from_fifo_locked(self, ticket: QueueTicket) -> None:
        for idx, queued in enumerate(self._fifo_queue):
            if queued.ticket_id == ticket.ticket_id:
                del self._fifo_queue[idx]
                return

    def _remove_from_bucket_queue_locked(self, ticket: QueueTicket) -> None:
        queue = self._short_queue if ticket.bucket == "short" else self._long_queue
        for idx, queued in enumerate(queue):
            if queued.ticket_id == ticket.ticket_id:
                del queue[idx]
                return

    def _record_completion_locked(self, ticket: dict, ttft_ms: float, latency_ms: float) -> None:
        bucket = ticket["bucket"]
        record = CompletedRecord(
            bucket=bucket,
            prompt_chars=int(ticket.get("prompt_chars", 0)),
            gate_wait_ms=float(ticket.get("gate_wait_ms", 0.0)),
            ttft_ms=float(ttft_ms),
            latency_ms=float(latency_ms),
            completed_at=time.perf_counter(),
        )
        self._bucket_completed[bucket] += 1
        self._recent_completed.append(record)
        self._completed_count += 1
        while len(self._recent_completed) > self.config.adapt_window_size:
            self._recent_completed.popleft()

        if self.config.policy != "length_aware_v4":
            return
        if len(self._recent_completed) < self.config.adapt_window_size:
            return
        if self._completed_count % self.config.adapt_update_interval != 0:
            return

        metrics = self._compute_window_metrics_locked()
        self._last_window_metrics = metrics
        self._apply_constraints_locked(metrics)

    def _compute_window_metrics_locked(self) -> dict:
        rows = list(self._recent_completed)
        short_rows = [row for row in rows if row.bucket == "short"]
        long_rows = [row for row in rows if row.bucket == "long"]

        def pct(values: list[float], q: float) -> float:
            if not values:
                return 0.0
            values = sorted(values)
            idx = (len(values) - 1) * q / 100
            lo = math.floor(idx)
            hi = math.ceil(idx)
            if lo == hi:
                return float(values[lo])
            return float(values[lo] + (values[hi] - values[lo]) * (idx - lo))

        def avg(rows_: list[CompletedRecord], field: str) -> float:
            if not rows_:
                return 0.0
            return sum(getattr(row, field) for row in rows_) / len(rows_)

        all_ttft = [row.ttft_ms for row in rows]
        all_latency = [row.latency_ms for row in rows]
        short_ratio = len(short_rows) / len(rows) if rows else 0.0
        return {
            "window_size": len(rows),
            "short_ratio": round(short_ratio, 4),
            "short_count": len(short_rows),
            "long_count": len(long_rows),
            "overall_p95_ttft_ms": round(pct(all_ttft, 95), 2),
            "overall_p95_latency_ms": round(pct(all_latency, 95), 2),
            "short_p95_ttft_ms": round(pct([r.ttft_ms for r in short_rows], 95), 2),
            "long_p95_ttft_ms": round(pct([r.ttft_ms for r in long_rows], 95), 2),
            "short_p95_latency_ms": round(pct([r.latency_ms for r in short_rows], 95), 2),
            "long_p95_latency_ms": round(pct([r.latency_ms for r in long_rows], 95), 2),
            "short_avg_gate_wait_ms": round(avg(short_rows, "gate_wait_ms"), 2),
            "long_avg_gate_wait_ms": round(avg(long_rows, "gate_wait_ms"), 2),
        }

    def _apply_constraints_locked(self, metrics: dict) -> None:
        old_weight = self._current_short_weight
        old_consecutive = self._current_max_consecutive_short
        new_weight = old_weight
        new_consecutive = old_consecutive
        action = "hold"
        reason = "within_bounds"

        long_constraint_violated = (
            metrics["long_p95_latency_ms"] > self.config.constraint_max_long_p95_latency_ms
            if metrics["long_count"] > 0
            else False
        )
        overall_constraint_violated = (
            metrics["overall_p95_latency_ms"] > self.config.constraint_max_overall_p95_latency_ms
        )

        if long_constraint_violated or overall_constraint_violated:
            new_weight -= 1
            new_consecutive -= 1
            action = "relax_short_bias"
            reason = "constraint_violation"
        elif (
            metrics["short_count"] > 0
            and metrics["short_p95_ttft_ms"] > self.config.objective_short_p95_ttft_ms
        ):
            new_weight += 1
            new_consecutive += 1
            action = "increase_short_bias"
            reason = "short_objective_not_met"

        new_weight = self._clamp(
            new_weight,
            self.config.min_short_weight,
            self.config.max_short_weight,
        )
        new_consecutive = self._clamp(
            new_consecutive,
            self.config.min_max_consecutive_short,
            self.config.max_max_consecutive_short,
        )

        if new_weight == old_weight and new_consecutive == old_consecutive:
            self._policy_updates.append(
                {
                    "completed_requests": self._completed_count,
                    "action": "hold",
                    "reason": reason,
                    "old_short_weight": old_weight,
                    "new_short_weight": new_weight,
                    "old_max_consecutive_short": old_consecutive,
                    "new_max_consecutive_short": new_consecutive,
                    "window_short_p95_ttft_ms": metrics["short_p95_ttft_ms"],
                    "window_long_p95_latency_ms": metrics["long_p95_latency_ms"],
                    "window_overall_p95_latency_ms": metrics["overall_p95_latency_ms"],
                }
            )
            return

        self._current_short_weight = new_weight
        self._current_max_consecutive_short = new_consecutive
        self._refresh_dispatch_cycle()
        self._policy_updates.append(
            {
                "completed_requests": self._completed_count,
                "action": action,
                "reason": reason,
                "old_short_weight": old_weight,
                "new_short_weight": new_weight,
                "old_max_consecutive_short": old_consecutive,
                "new_max_consecutive_short": new_consecutive,
                "window_short_p95_ttft_ms": metrics["short_p95_ttft_ms"],
                "window_long_p95_latency_ms": metrics["long_p95_latency_ms"],
                "window_overall_p95_latency_ms": metrics["overall_p95_latency_ms"],
            }
        )

    def _refresh_dispatch_cycle(self) -> None:
        short_weight = max(1, int(self._current_short_weight))
        long_weight = max(1, int(self.config.long_weight))
        self._dispatch_cycle = tuple(["short"] * short_weight + ["long"] * long_weight)
        self._dispatch_cycle_index = 0

    def _clamp(self, value: int, lower: int, upper: int) -> int:
        return max(lower, min(upper, value))
