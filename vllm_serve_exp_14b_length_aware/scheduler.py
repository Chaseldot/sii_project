from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class SchedulerConfig:
    short_threshold_chars: int = 256
    short_weight: int = 3
    long_weight: int = 1
    max_consecutive_short: int = 6
    max_queue_wait_sec: float = 300.0


@dataclass
class QueueTicket:
    ticket_id: int
    bucket: str
    prompt_chars: int
    enqueue_time: float
    granted: bool = False
    gate_wait_sec: float = 0.0


@dataclass
class LengthAwareScheduler:
    config: SchedulerConfig
    _condition: threading.Condition = field(
        default_factory=lambda: threading.Condition(threading.Lock()),
        init=False,
    )
    _short_queue: deque[QueueTicket] = field(default_factory=deque, init=False)
    _long_queue: deque[QueueTicket] = field(default_factory=deque, init=False)
    _ticket_seq: int = field(default=0, init=False)
    _current_inflight: int = field(default=0, init=False)
    _max_inflight: int = field(default=0, init=False)
    _consecutive_short: int = field(default=0, init=False)
    _dispatch_cycle: tuple[str, ...] = field(default=tuple(), init=False)
    _dispatch_cycle_index: int = field(default=0, init=False)
    _total_requests: int = field(default=0, init=False)
    _bucket_enqueued: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_dispatched: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _bucket_max_gate_wait_sec: dict[str, float] = field(default_factory=lambda: {"short": 0.0, "long": 0.0}, init=False)
    _max_queue_depth: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _forced_long_dispatches: int = field(default=0, init=False)
    _last_dispatch_bucket: str = field(default="startup", init=False)

    def __post_init__(self) -> None:
        short_weight = max(1, int(self.config.short_weight))
        long_weight = max(1, int(self.config.long_weight))
        self._dispatch_cycle = tuple(["short"] * short_weight + ["long"] * long_weight)

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
            queue = self._queue_for(bucket)
            queue.append(ticket)
            self._total_requests += 1
            self._bucket_enqueued[bucket] += 1
            self._max_queue_depth[bucket] = max(self._max_queue_depth[bucket], len(queue))

            deadline = enqueue_time + self.config.max_queue_wait_sec
            while not ticket.granted:
                self._maybe_grant_locked()
                if ticket.granted:
                    break
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    self._remove_ticket_locked(ticket)
                    raise TimeoutError(
                        f"Length-aware scheduler wait exceeded {self.config.max_queue_wait_sec}s "
                        f"for bucket={bucket}"
                    )
                self._condition.wait(timeout=remaining)

            self._current_inflight += 1
            self._max_inflight = max(self._max_inflight, self._current_inflight)
            return {
                "bucket": bucket,
                "prompt_chars": prompt_chars,
                "gate_wait_ms": round(ticket.gate_wait_sec * 1000, 2),
            }

    def release(self) -> None:
        with self._condition:
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

            current_short = len(self._short_queue)
            current_long = len(self._long_queue)
            return {
                "scheduler_policy": "length_aware_weighted_round_robin",
                "short_threshold_chars": self.config.short_threshold_chars,
                "short_weight": self.config.short_weight,
                "long_weight": self.config.long_weight,
                "max_consecutive_short": self.config.max_consecutive_short,
                "max_queue_wait_sec": self.config.max_queue_wait_sec,
                "scheduler_total_requests": self._total_requests,
                "scheduler_short_enqueued": self._bucket_enqueued["short"],
                "scheduler_long_enqueued": self._bucket_enqueued["long"],
                "scheduler_short_dispatched": self._bucket_dispatched["short"],
                "scheduler_long_dispatched": self._bucket_dispatched["long"],
                "scheduler_short_avg_gate_wait_ms": round(avg_wait("short"), 2),
                "scheduler_long_avg_gate_wait_ms": round(avg_wait("long"), 2),
                "scheduler_short_max_gate_wait_ms": round(self._bucket_max_gate_wait_sec["short"] * 1000, 2),
                "scheduler_long_max_gate_wait_ms": round(self._bucket_max_gate_wait_sec["long"] * 1000, 2),
                "scheduler_current_short_queue": current_short,
                "scheduler_current_long_queue": current_long,
                "scheduler_max_short_queue": self._max_queue_depth["short"],
                "scheduler_max_long_queue": self._max_queue_depth["long"],
                "scheduler_current_inflight": self._current_inflight,
                "scheduler_max_inflight": self._max_inflight,
                "scheduler_forced_long_dispatches": self._forced_long_dispatches,
                "scheduler_last_dispatch_bucket": self._last_dispatch_bucket,
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

    def _queue_for(self, bucket: str) -> deque[QueueTicket]:
        return self._short_queue if bucket == "short" else self._long_queue

    def _remove_ticket_locked(self, ticket: QueueTicket) -> None:
        queue = self._queue_for(ticket.bucket)
        for idx, queued in enumerate(queue):
            if queued.ticket_id == ticket.ticket_id:
                del queue[idx]
                break

    def _maybe_grant_locked(self) -> None:
        if not self._short_queue and not self._long_queue:
            return

        bucket, forced_long = self._pick_next_bucket_locked()
        if bucket is None:
            return

        queue = self._queue_for(bucket)
        if not queue:
            return

        ticket = queue.popleft()
        ticket.granted = True
        ticket.gate_wait_sec = time.perf_counter() - ticket.enqueue_time
        self._bucket_dispatched[bucket] += 1
        self._bucket_gate_wait_sec[bucket] += ticket.gate_wait_sec
        self._bucket_max_gate_wait_sec[bucket] = max(
            self._bucket_max_gate_wait_sec[bucket],
            ticket.gate_wait_sec,
        )
        self._last_dispatch_bucket = bucket
        if forced_long:
            self._forced_long_dispatches += 1
        self._condition.notify_all()

    def _pick_next_bucket_locked(self) -> tuple[str | None, bool]:
        has_short = bool(self._short_queue)
        has_long = bool(self._long_queue)
        if has_long and not has_short:
            self._consecutive_short = 0
            return "long", False
        if has_short and not has_long:
            self._consecutive_short += 1
            return "short", False
        if not has_short and not has_long:
            return None, False

        if self._consecutive_short >= self.config.max_consecutive_short:
            self._consecutive_short = 0
            return "long", True

        cycle_len = len(self._dispatch_cycle)
        for offset in range(cycle_len):
            idx = (self._dispatch_cycle_index + offset) % cycle_len
            bucket = self._dispatch_cycle[idx]
            if self._queue_for(bucket):
                self._dispatch_cycle_index = (idx + 1) % cycle_len
                if bucket == "short":
                    self._consecutive_short += 1
                else:
                    self._consecutive_short = 0
                return bucket, False

        return None, False
