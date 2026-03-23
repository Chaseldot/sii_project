from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class SchedulerConfig:
    policy: str = "length_aware_v6_1"
    short_threshold_chars: int = 256
    max_consecutive_short: int = 4
    max_active_requests: int = 64
    max_queue_wait_sec: float = 300.0
    arrival_window_size: int = 256
    control_update_interval: int = 64
    target_short_share_bonus: float = 0.18
    min_short_share: float = 0.42
    max_short_share: float = 0.72
    queue_ratio_control_gain: float = 0.8
    queue_ratio_margin: float = 0.12
    max_ratio_adjustment: float = 0.12


@dataclass
class QueueTicket:
    ticket_id: int
    bucket: str
    prompt_chars: int
    enqueue_time: float
    granted: bool = False
    gate_wait_sec: float = 0.0


@dataclass
class ArrivalRecord:
    bucket: str
    prompt_chars: int
    arrived_at: float


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
    _recent_arrivals: deque[ArrivalRecord] = field(default_factory=deque, init=False)
    _ticket_seq: int = field(default=0, init=False)
    _current_inflight: int = field(default=0, init=False)
    _max_inflight: int = field(default=0, init=False)
    _consecutive_short: int = field(default=0, init=False)
    _short_credit: float = field(default=0.0, init=False)
    _long_credit: float = field(default=0.0, init=False)
    _total_requests: int = field(default=0, init=False)
    _completed_requests: int = field(default=0, init=False)
    _total_dispatched: int = field(default=0, init=False)
    _bucket_enqueued: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_dispatched: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_completed: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _bucket_max_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _max_queue_depth: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _max_total_queue: int = field(default=0, init=False)
    _last_dispatch_bucket: str = field(default="startup", init=False)
    _last_dispatch_reason: str = field(default="startup", init=False)
    _target_short_share_current: float = field(default=0.5, init=False)
    _target_short_share_sum: float = field(default=0.0, init=False)
    _target_short_share_samples: int = field(default=0, init=False)
    _ratio_adjustment_current: float = field(default=0.0, init=False)
    _ratio_adjustment_sum: float = field(default=0.0, init=False)
    _ratio_adjustment_samples: int = field(default=0, init=False)
    _ratio_bias_to_short_dispatches: int = field(default=0, init=False)
    _ratio_bias_to_long_dispatches: int = field(default=0, init=False)
    _queue_snapshot_samples: int = field(default=0, init=False)
    _queue_short_len_sum: float = field(default=0.0, init=False)
    _queue_long_len_sum: float = field(default=0.0, init=False)
    _queue_short_head_wait_ms_sum: float = field(default=0.0, init=False)
    _queue_long_head_wait_ms_sum: float = field(default=0.0, init=False)
    _policy_updates: list[dict] = field(default_factory=list, init=False)
    _last_arrival_metrics: dict = field(default_factory=dict, init=False)
    _last_queue_metrics: dict = field(default_factory=dict, init=False)

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
            if ticket:
                bucket = str(ticket.get("bucket", "long"))
                if bucket in self._bucket_completed:
                    self._bucket_completed[bucket] += 1
                self._completed_requests += 1
            if self._current_inflight > 0:
                self._current_inflight -= 1
            self._record_queue_snapshot_locked()
            self._maybe_grant_locked()
            self._condition.notify_all()

    def snapshot(self) -> dict:
        with self._condition:
            arrival_metrics = self._compute_arrival_metrics_locked()
            queue_metrics = self._compute_queue_metrics_locked()
            total_dispatched = self._bucket_dispatched["short"] + self._bucket_dispatched["long"]

            def avg_wait(bucket: str) -> float:
                dispatched = self._bucket_dispatched[bucket]
                if dispatched == 0:
                    return 0.0
                return self._bucket_gate_wait_sec[bucket] / dispatched * 1000

            def avg_queue(metric_sum: float) -> float:
                if self._queue_snapshot_samples == 0:
                    return 0.0
                return metric_sum / self._queue_snapshot_samples

            target_short_share_avg = 0.0
            if self._target_short_share_samples > 0:
                target_short_share_avg = self._target_short_share_sum / self._target_short_share_samples

            ratio_adjustment_avg = 0.0
            if self._ratio_adjustment_samples > 0:
                ratio_adjustment_avg = self._ratio_adjustment_sum / self._ratio_adjustment_samples

            actual_short_share = 0.0
            if total_dispatched > 0:
                actual_short_share = self._bucket_dispatched["short"] / total_dispatched

            return {
                "scheduler_policy": self.config.policy,
                "short_threshold_chars": self.config.short_threshold_chars,
                "max_consecutive_short": self.config.max_consecutive_short,
                "max_active_requests": self.config.max_active_requests,
                "arrival_window_size": self.config.arrival_window_size,
                "control_update_interval": self.config.control_update_interval,
                "target_short_share_bonus": self.config.target_short_share_bonus,
                "min_short_share": self.config.min_short_share,
                "max_short_share": self.config.max_short_share,
                "queue_ratio_control_gain": self.config.queue_ratio_control_gain,
                "queue_ratio_margin": self.config.queue_ratio_margin,
                "max_ratio_adjustment": self.config.max_ratio_adjustment,
                "scheduler_total_requests": self._total_requests,
                "scheduler_completed_requests": self._completed_requests,
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
                "scheduler_last_dispatch_reason": self._last_dispatch_reason,
                "scheduler_recent_arrival_short_ratio": round(arrival_metrics["short_ratio"], 4),
                "scheduler_recent_arrival_short_count": arrival_metrics["short_count"],
                "scheduler_recent_arrival_long_count": arrival_metrics["long_count"],
                "scheduler_current_queue_short_ratio": round(queue_metrics["short_ratio"], 4),
                "scheduler_current_queue_short_count": queue_metrics["short_count"],
                "scheduler_current_queue_long_count": queue_metrics["long_count"],
                "scheduler_target_short_share_current": round(self._target_short_share_current, 4),
                "scheduler_target_short_share_avg": round(target_short_share_avg, 4),
                "scheduler_actual_short_share": round(actual_short_share, 4),
                "scheduler_ratio_adjustment_current": round(self._ratio_adjustment_current, 4),
                "scheduler_ratio_adjustment_avg": round(ratio_adjustment_avg, 4),
                "scheduler_short_credit": round(self._short_credit, 4),
                "scheduler_long_credit": round(self._long_credit, 4),
                "scheduler_ratio_bias_to_short_dispatches": self._ratio_bias_to_short_dispatches,
                "scheduler_ratio_bias_to_long_dispatches": self._ratio_bias_to_long_dispatches,
                "scheduler_short_queue_len_avg": round(avg_queue(self._queue_short_len_sum), 2),
                "scheduler_long_queue_len_avg": round(avg_queue(self._queue_long_len_sum), 2),
                "scheduler_short_head_wait_ms_avg": round(avg_queue(self._queue_short_head_wait_ms_sum), 2),
                "scheduler_long_head_wait_ms_avg": round(avg_queue(self._queue_long_head_wait_ms_sum), 2),
                "scheduler_last_arrival_metrics": self._last_arrival_metrics,
                "scheduler_last_queue_metrics": self._last_queue_metrics,
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
        self._recent_arrivals.append(
            ArrivalRecord(
                bucket=ticket.bucket,
                prompt_chars=ticket.prompt_chars,
                arrived_at=ticket.enqueue_time,
            )
        )
        while len(self._recent_arrivals) > self.config.arrival_window_size:
            self._recent_arrivals.popleft()
        self._max_queue_depth[ticket.bucket] = max(
            self._max_queue_depth[ticket.bucket],
            len(self._short_queue if ticket.bucket == "short" else self._long_queue),
        )
        self._max_total_queue = max(self._max_total_queue, self._current_total_queue_locked())
        self._record_queue_snapshot_locked()
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
            self._record_queue_snapshot_locked()
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
            self._last_dispatch_bucket = ticket.bucket
            self._last_dispatch_reason = "fifo"
            self._after_dispatch_locked()
            return ticket
        return self._select_length_aware_ticket_locked()

    def _select_length_aware_ticket_locked(self) -> QueueTicket | None:
        has_short = bool(self._short_queue)
        has_long = bool(self._long_queue)
        if not has_short and not has_long:
            return None
        if has_long and not has_short:
            return self._dispatch_long_locked(reason="only_long")
        if has_short and not has_long:
            return self._dispatch_short_locked(reason="only_short")

        if self._consecutive_short >= self.config.max_consecutive_short:
            return self._dispatch_long_locked(reason="max_consecutive_short")

        arrival_metrics = self._compute_arrival_metrics_locked()
        queue_metrics = self._compute_queue_metrics_locked()
        target_short_share, ratio_adjustment, bias_reason = self._compute_target_short_share_locked(
            arrival_metrics,
            queue_metrics,
        )
        self._target_short_share_current = target_short_share
        self._target_short_share_sum += target_short_share
        self._target_short_share_samples += 1
        self._ratio_adjustment_current = ratio_adjustment
        self._ratio_adjustment_sum += ratio_adjustment
        self._ratio_adjustment_samples += 1
        self._last_arrival_metrics = {
            **arrival_metrics,
            "target_short_share": round(target_short_share, 4),
        }
        self._last_queue_metrics = {
            **queue_metrics,
            "ratio_adjustment": round(ratio_adjustment, 4),
            "bias_reason": bias_reason,
        }

        self._short_credit += target_short_share
        self._long_credit += 1.0 - target_short_share

        if self._short_credit >= self._long_credit:
            if ratio_adjustment > 0:
                self._ratio_bias_to_short_dispatches += 1
            return self._dispatch_short_locked(reason=bias_reason or "fair_share_short")

        if ratio_adjustment < 0:
            self._ratio_bias_to_long_dispatches += 1
        return self._dispatch_long_locked(reason=bias_reason or "fair_share_long")

    def _dispatch_short_locked(self, reason: str) -> QueueTicket:
        ticket = self._short_queue.popleft()
        self._remove_from_fifo_locked(ticket)
        self._consecutive_short += 1
        self._last_dispatch_bucket = "short"
        self._last_dispatch_reason = reason
        self._short_credit -= 1.0
        self._normalize_credits_locked()
        self._after_dispatch_locked()
        return ticket

    def _dispatch_long_locked(self, reason: str) -> QueueTicket:
        ticket = self._long_queue.popleft()
        self._remove_from_fifo_locked(ticket)
        self._consecutive_short = 0
        self._last_dispatch_bucket = "long"
        self._last_dispatch_reason = reason
        self._long_credit -= 1.0
        self._normalize_credits_locked()
        self._after_dispatch_locked()
        return ticket

    def _after_dispatch_locked(self) -> None:
        self._total_dispatched += 1
        if self._total_dispatched % self.config.control_update_interval == 0:
            self._record_control_update_locked()

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

    def _compute_arrival_metrics_locked(self) -> dict:
        short_count = 0
        long_count = 0
        for row in self._recent_arrivals:
            if row.bucket == "short":
                short_count += 1
            else:
                long_count += 1
        total = short_count + long_count
        short_ratio = short_count / total if total > 0 else 0.0
        return {
            "window_size": total,
            "short_count": short_count,
            "long_count": long_count,
            "short_ratio": short_ratio,
        }

    def _compute_queue_metrics_locked(self) -> dict:
        short_count = len(self._short_queue)
        long_count = len(self._long_queue)
        total = short_count + long_count
        short_ratio = short_count / total if total > 0 else 0.0
        return {
            "window_size": total,
            "short_count": short_count,
            "long_count": long_count,
            "short_ratio": short_ratio,
        }

    def _compute_target_short_share_locked(self, arrival_metrics: dict, queue_metrics: dict) -> tuple[float, float, str]:
        base_target = arrival_metrics["short_ratio"] + self.config.target_short_share_bonus
        ratio_delta = queue_metrics["short_ratio"] - arrival_metrics["short_ratio"]
        adjustment = 0.0
        reason = ""
        if ratio_delta > self.config.queue_ratio_margin:
            adjustment = min(
                self.config.max_ratio_adjustment,
                ratio_delta * self.config.queue_ratio_control_gain,
            )
            reason = "queue_ratio_bias_short"
        elif ratio_delta < -self.config.queue_ratio_margin:
            adjustment = max(
                -self.config.max_ratio_adjustment,
                ratio_delta * self.config.queue_ratio_control_gain,
            )
            reason = "queue_ratio_bias_long"
        target = self._clamp_float(
            base_target + adjustment,
            self.config.min_short_share,
            self.config.max_short_share,
        )
        return target, adjustment, reason

    def _record_queue_snapshot_locked(self) -> None:
        self._queue_snapshot_samples += 1
        short_len = len(self._short_queue)
        long_len = len(self._long_queue)
        self._queue_short_len_sum += short_len
        self._queue_long_len_sum += long_len
        self._queue_short_head_wait_ms_sum += self._head_wait_ms_locked(self._short_queue)
        self._queue_long_head_wait_ms_sum += self._head_wait_ms_locked(self._long_queue)

    def _record_control_update_locked(self) -> None:
        arrival_metrics = self._compute_arrival_metrics_locked()
        queue_metrics = self._compute_queue_metrics_locked()
        target_short_share, ratio_adjustment, bias_reason = self._compute_target_short_share_locked(
            arrival_metrics,
            queue_metrics,
        )
        total_dispatched = self._bucket_dispatched["short"] + self._bucket_dispatched["long"]
        actual_short_share = 0.0
        if total_dispatched > 0:
            actual_short_share = self._bucket_dispatched["short"] / total_dispatched
        self._policy_updates.append(
            {
                "dispatched_requests": self._total_dispatched,
                "arrival_window_size": arrival_metrics["window_size"],
                "arrival_short_ratio": round(arrival_metrics["short_ratio"], 4),
                "queue_window_size": queue_metrics["window_size"],
                "queue_short_ratio": round(queue_metrics["short_ratio"], 4),
                "target_short_share": round(target_short_share, 4),
                "actual_short_share": round(actual_short_share, 4),
                "ratio_adjustment": round(ratio_adjustment, 4),
                "bias_reason": bias_reason,
                "short_queue_len": len(self._short_queue),
                "long_queue_len": len(self._long_queue),
                "short_head_wait_ms": round(self._head_wait_ms_locked(self._short_queue), 2),
                "long_head_wait_ms": round(self._head_wait_ms_locked(self._long_queue), 2),
                "short_credit": round(self._short_credit, 4),
                "long_credit": round(self._long_credit, 4),
                "last_dispatch_bucket": self._last_dispatch_bucket,
                "last_dispatch_reason": self._last_dispatch_reason,
            }
        )

    def _head_wait_ms_locked(self, queue: deque[QueueTicket]) -> float:
        if not queue:
            return 0.0
        return (time.perf_counter() - queue[0].enqueue_time) * 1000

    def _normalize_credits_locked(self) -> None:
        self._short_credit = self._clamp_float(self._short_credit, -4.0, 4.0)
        self._long_credit = self._clamp_float(self._long_credit, -4.0, 4.0)

    def _clamp_float(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))
