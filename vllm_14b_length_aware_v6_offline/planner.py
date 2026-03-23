from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class PlannerConfig:
    policy: str = "length_aware_v6"
    batch_size: int = 1
    lookahead_size: int = 64
    short_threshold_tokens: int = 256
    max_consecutive_short: int = 4
    arrival_window_size: int = 256
    control_update_interval: int = 64
    target_short_share_bonus: float = 0.2
    min_short_share: float = 0.5
    max_short_share: float = 0.75
    queue_ratio_control_gain: float = 1.0
    queue_ratio_margin: float = 0.08
    max_ratio_adjustment: float = 0.2
    sort_within_batch: bool = True


@dataclass
class PlannedRequest:
    request_id: int
    original_index: int
    prompt: str
    estimated_tokens: int
    bucket: str
    payload: object | None = None


@dataclass
class ArrivalRecord:
    bucket: str
    estimated_tokens: int


@dataclass
class OfflineLengthAwarePlanner:
    config: PlannerConfig
    _short_queue: deque[PlannedRequest] = field(default_factory=deque, init=False)
    _long_queue: deque[PlannedRequest] = field(default_factory=deque, init=False)
    _fifo_queue: deque[PlannedRequest] = field(default_factory=deque, init=False)
    _recent_arrivals: deque[ArrivalRecord] = field(default_factory=deque, init=False)
    _consecutive_short: int = field(default=0, init=False)
    _short_credit: float = field(default=0.0, init=False)
    _long_credit: float = field(default=0.0, init=False)
    _total_requests: int = field(default=0, init=False)
    _total_selected: int = field(default=0, init=False)
    _bucket_enqueued: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
    _bucket_selected: dict[str, int] = field(default_factory=lambda: {"short": 0, "long": 0}, init=False)
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
    _policy_updates: list[dict] = field(default_factory=list, init=False)
    _last_arrival_metrics: dict = field(default_factory=dict, init=False)
    _last_queue_metrics: dict = field(default_factory=dict, init=False)
    _planned_batches: int = field(default=0, init=False)
    _planned_batch_size_sum: int = field(default=0, init=False)
    _planned_batch_prompt_tokens_sum: int = field(default=0, init=False)
    _planned_batch_max_prompt_tokens_sum: int = field(default=0, init=False)

    def build_requests(
        self,
        prompts: list[str],
        estimated_tokens: list[int],
        payloads: list[object] | None = None,
    ) -> list[PlannedRequest]:
        if len(prompts) != len(estimated_tokens):
            raise ValueError("prompts and estimated_tokens must have the same length")
        if payloads is None:
            payloads = [None] * len(prompts)
        if len(prompts) != len(payloads):
            raise ValueError("prompts and payloads must have the same length")

        requests = []
        for idx, (prompt, estimate, payload) in enumerate(zip(prompts, estimated_tokens, payloads), start=1):
            requests.append(
                PlannedRequest(
                    request_id=idx,
                    original_index=idx - 1,
                    prompt=prompt,
                    estimated_tokens=estimate,
                    bucket=self.classify_tokens(estimate),
                    payload=payload,
                )
            )
        return requests

    def classify_tokens(self, estimated_tokens: int) -> str:
        return "short" if estimated_tokens <= self.config.short_threshold_tokens else "long"

    def plan(self, requests: list[PlannedRequest]) -> list[list[PlannedRequest]]:
        self._reset_state()
        batches: list[list[PlannedRequest]] = []
        cursor = 0
        total = len(requests)
        window_capacity = max(self.config.lookahead_size, self.config.batch_size)

        while cursor < total or self._fifo_queue:
            while cursor < total and self._current_total_queue() < window_capacity:
                self._enqueue(requests[cursor])
                cursor += 1

            if not self._fifo_queue:
                continue

            batch = self._collect_batch()
            if not batch:
                break
            if self.config.sort_within_batch:
                batch = sorted(batch, key=lambda item: (item.estimated_tokens, item.original_index))

            self._planned_batches += 1
            self._planned_batch_size_sum += len(batch)
            self._planned_batch_prompt_tokens_sum += sum(item.estimated_tokens for item in batch)
            self._planned_batch_max_prompt_tokens_sum += max(item.estimated_tokens for item in batch)
            batches.append(batch)

        return batches

    def snapshot(self) -> dict:
        arrival_metrics = self._compute_arrival_metrics()
        queue_metrics = self._compute_queue_metrics()
        total_selected = self._bucket_selected["short"] + self._bucket_selected["long"]

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
        if total_selected > 0:
            actual_short_share = self._bucket_selected["short"] / total_selected

        avg_batch_size = 0.0
        avg_batch_prompt_tokens = 0.0
        avg_batch_max_prompt_tokens = 0.0
        if self._planned_batches > 0:
            avg_batch_size = self._planned_batch_size_sum / self._planned_batches
            avg_batch_prompt_tokens = self._planned_batch_prompt_tokens_sum / self._planned_batches
            avg_batch_max_prompt_tokens = self._planned_batch_max_prompt_tokens_sum / self._planned_batches

        return {
            "planner_policy": self.config.policy,
            "planner_batch_size": self.config.batch_size,
            "planner_lookahead_size": self.config.lookahead_size,
            "planner_short_threshold_tokens": self.config.short_threshold_tokens,
            "planner_max_consecutive_short": self.config.max_consecutive_short,
            "planner_arrival_window_size": self.config.arrival_window_size,
            "planner_control_update_interval": self.config.control_update_interval,
            "planner_target_short_share_bonus": self.config.target_short_share_bonus,
            "planner_min_short_share": self.config.min_short_share,
            "planner_max_short_share": self.config.max_short_share,
            "planner_queue_ratio_control_gain": self.config.queue_ratio_control_gain,
            "planner_queue_ratio_margin": self.config.queue_ratio_margin,
            "planner_max_ratio_adjustment": self.config.max_ratio_adjustment,
            "planner_sort_within_batch": self.config.sort_within_batch,
            "planner_total_requests": self._total_requests,
            "planner_total_selected": self._total_selected,
            "planner_short_enqueued": self._bucket_enqueued["short"],
            "planner_long_enqueued": self._bucket_enqueued["long"],
            "planner_short_selected": self._bucket_selected["short"],
            "planner_long_selected": self._bucket_selected["long"],
            "planner_max_short_queue": self._max_queue_depth["short"],
            "planner_max_long_queue": self._max_queue_depth["long"],
            "planner_max_total_queue": self._max_total_queue,
            "planner_last_dispatch_bucket": self._last_dispatch_bucket,
            "planner_last_dispatch_reason": self._last_dispatch_reason,
            "planner_recent_arrival_short_ratio": round(arrival_metrics["short_ratio"], 4),
            "planner_recent_arrival_short_count": arrival_metrics["short_count"],
            "planner_recent_arrival_long_count": arrival_metrics["long_count"],
            "planner_current_queue_short_ratio": round(queue_metrics["short_ratio"], 4),
            "planner_current_queue_short_count": queue_metrics["short_count"],
            "planner_current_queue_long_count": queue_metrics["long_count"],
            "planner_target_short_share_current": round(self._target_short_share_current, 4),
            "planner_target_short_share_avg": round(target_short_share_avg, 4),
            "planner_actual_short_share": round(actual_short_share, 4),
            "planner_ratio_adjustment_current": round(self._ratio_adjustment_current, 4),
            "planner_ratio_adjustment_avg": round(ratio_adjustment_avg, 4),
            "planner_short_credit": round(self._short_credit, 4),
            "planner_long_credit": round(self._long_credit, 4),
            "planner_ratio_bias_to_short_dispatches": self._ratio_bias_to_short_dispatches,
            "planner_ratio_bias_to_long_dispatches": self._ratio_bias_to_long_dispatches,
            "planner_short_queue_len_avg": round(avg_queue(self._queue_short_len_sum), 2),
            "planner_long_queue_len_avg": round(avg_queue(self._queue_long_len_sum), 2),
            "planner_total_batches": self._planned_batches,
            "planner_avg_batch_size": round(avg_batch_size, 2),
            "planner_avg_batch_prompt_tokens": round(avg_batch_prompt_tokens, 2),
            "planner_avg_batch_max_prompt_tokens": round(avg_batch_max_prompt_tokens, 2),
            "planner_last_arrival_metrics": self._last_arrival_metrics,
            "planner_last_queue_metrics": self._last_queue_metrics,
            "planner_policy_updates": self._policy_updates[-20:],
        }

    def _reset_state(self) -> None:
        self._short_queue.clear()
        self._long_queue.clear()
        self._fifo_queue.clear()
        self._recent_arrivals.clear()
        self._consecutive_short = 0
        self._short_credit = 0.0
        self._long_credit = 0.0
        self._total_requests = 0
        self._total_selected = 0
        self._bucket_enqueued = {"short": 0, "long": 0}
        self._bucket_selected = {"short": 0, "long": 0}
        self._max_queue_depth = {"short": 0, "long": 0}
        self._max_total_queue = 0
        self._last_dispatch_bucket = "startup"
        self._last_dispatch_reason = "startup"
        self._target_short_share_current = 0.5
        self._target_short_share_sum = 0.0
        self._target_short_share_samples = 0
        self._ratio_adjustment_current = 0.0
        self._ratio_adjustment_sum = 0.0
        self._ratio_adjustment_samples = 0
        self._ratio_bias_to_short_dispatches = 0
        self._ratio_bias_to_long_dispatches = 0
        self._queue_snapshot_samples = 0
        self._queue_short_len_sum = 0.0
        self._queue_long_len_sum = 0.0
        self._policy_updates = []
        self._last_arrival_metrics = {}
        self._last_queue_metrics = {}
        self._planned_batches = 0
        self._planned_batch_size_sum = 0
        self._planned_batch_prompt_tokens_sum = 0
        self._planned_batch_max_prompt_tokens_sum = 0

    def _enqueue(self, request: PlannedRequest) -> None:
        self._total_requests += 1
        self._bucket_enqueued[request.bucket] += 1
        self._fifo_queue.append(request)
        if request.bucket == "short":
            self._short_queue.append(request)
        else:
            self._long_queue.append(request)
        self._recent_arrivals.append(
            ArrivalRecord(
                bucket=request.bucket,
                estimated_tokens=request.estimated_tokens,
            )
        )
        while len(self._recent_arrivals) > self.config.arrival_window_size:
            self._recent_arrivals.popleft()
        self._max_queue_depth[request.bucket] = max(
            self._max_queue_depth[request.bucket],
            len(self._short_queue if request.bucket == "short" else self._long_queue),
        )
        self._max_total_queue = max(self._max_total_queue, self._current_total_queue())
        self._record_queue_snapshot()

    def _collect_batch(self) -> list[PlannedRequest]:
        batch: list[PlannedRequest] = []
        while len(batch) < self.config.batch_size and self._fifo_queue:
            self._record_queue_snapshot()
            request = self._select_next_request()
            if request is None:
                break
            batch.append(request)
        return batch

    def _current_total_queue(self) -> int:
        return len(self._fifo_queue)

    def _select_next_request(self) -> PlannedRequest | None:
        if self.config.policy == "fifo":
            request = self._fifo_queue.popleft() if self._fifo_queue else None
            if request is None:
                return None
            self._remove_from_bucket_queue(request)
            if request.bucket == "short":
                self._consecutive_short += 1
            else:
                self._consecutive_short = 0
            self._after_select(request.bucket, "fifo")
            return request
        return self._select_length_aware_request()

    def _select_length_aware_request(self) -> PlannedRequest | None:
        has_short = bool(self._short_queue)
        has_long = bool(self._long_queue)
        if not has_short and not has_long:
            return None
        if has_long and not has_short:
            return self._dispatch_long("only_long")
        if has_short and not has_long:
            return self._dispatch_short("only_short")

        if self._consecutive_short >= self.config.max_consecutive_short:
            return self._dispatch_long("max_consecutive_short")

        arrival_metrics = self._compute_arrival_metrics()
        queue_metrics = self._compute_queue_metrics()
        target_short_share, ratio_adjustment, bias_reason = self._compute_target_short_share(
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
            return self._dispatch_short(bias_reason or "fair_share_short")

        if ratio_adjustment < 0:
            self._ratio_bias_to_long_dispatches += 1
        return self._dispatch_long(bias_reason or "fair_share_long")

    def _dispatch_short(self, reason: str) -> PlannedRequest:
        request = self._short_queue.popleft()
        self._remove_from_fifo(request)
        self._consecutive_short += 1
        self._short_credit -= 1.0
        self._normalize_credits()
        self._after_select("short", reason)
        return request

    def _dispatch_long(self, reason: str) -> PlannedRequest:
        request = self._long_queue.popleft()
        self._remove_from_fifo(request)
        self._consecutive_short = 0
        self._long_credit -= 1.0
        self._normalize_credits()
        self._after_select("long", reason)
        return request

    def _after_select(self, bucket: str, reason: str) -> None:
        self._bucket_selected[bucket] += 1
        self._total_selected += 1
        self._last_dispatch_bucket = bucket
        self._last_dispatch_reason = reason
        if self._total_selected % self.config.control_update_interval == 0:
            self._record_control_update()

    def _remove_from_fifo(self, request: PlannedRequest) -> None:
        for idx, queued in enumerate(self._fifo_queue):
            if queued.request_id == request.request_id:
                del self._fifo_queue[idx]
                return

    def _remove_from_bucket_queue(self, request: PlannedRequest) -> None:
        queue = self._short_queue if request.bucket == "short" else self._long_queue
        for idx, queued in enumerate(queue):
            if queued.request_id == request.request_id:
                del queue[idx]
                return

    def _compute_arrival_metrics(self) -> dict:
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

    def _compute_queue_metrics(self) -> dict:
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

    def _compute_target_short_share(self, arrival_metrics: dict, queue_metrics: dict) -> tuple[float, float, str]:
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

    def _record_queue_snapshot(self) -> None:
        self._queue_snapshot_samples += 1
        self._queue_short_len_sum += len(self._short_queue)
        self._queue_long_len_sum += len(self._long_queue)

    def _record_control_update(self) -> None:
        arrival_metrics = self._compute_arrival_metrics()
        queue_metrics = self._compute_queue_metrics()
        target_short_share, ratio_adjustment, bias_reason = self._compute_target_short_share(
            arrival_metrics,
            queue_metrics,
        )
        total_selected = self._bucket_selected["short"] + self._bucket_selected["long"]
        actual_short_share = 0.0
        if total_selected > 0:
            actual_short_share = self._bucket_selected["short"] / total_selected
        self._policy_updates.append(
            {
                "selected_requests": self._total_selected,
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
                "short_credit": round(self._short_credit, 4),
                "long_credit": round(self._long_credit, 4),
                "last_dispatch_bucket": self._last_dispatch_bucket,
                "last_dispatch_reason": self._last_dispatch_reason,
            }
        )

    def _normalize_credits(self) -> None:
        self._short_credit = self._clamp_float(self._short_credit, -4.0, 4.0)
        self._long_credit = self._clamp_float(self._long_credit, -4.0, 4.0)

    def _clamp_float(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))
