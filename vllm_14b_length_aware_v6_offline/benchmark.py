from __future__ import annotations

import argparse
import time

from .common import (
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_PROMPT_FILE,
    compute_benchmark_stats,
    load_jsonl,
    mean,
    percentile,
    print_benchmark_stats,
    save_json,
)
from .engine import EngineConfig, VLLM14BLengthAwareV6OfflineEngine
from .planner import OfflineLengthAwarePlanner, PlannerConfig
from .monitor import OfflineGpuMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM 14B length-aware v6 离线吞吐 & 延迟基准测试")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument("--prompt_file", type=str, default=str(DEFAULT_PROMPT_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--max_new_tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
    parser.add_argument("--dtype", type=str, default="bfloat16")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.9)
    parser.add_argument("--enable_prefix_caching", action="store_true")
    parser.add_argument("--max_model_len", type=int, default=8192)
    parser.add_argument("--max_num_seqs", type=int, default=None)
    parser.add_argument("--max_num_batched_tokens", type=int, default=8192)
    parser.add_argument("--load_format", type=str, default="auto")
    parser.add_argument("--quantization", type=str, default="")
    parser.add_argument("--enforce_eager", action="store_true")
    parser.add_argument("--monitor_sample_interval_sec", type=float, default=0.5)
    parser.add_argument("--planner_policy", type=str, default="length_aware_v6", choices=["fifo", "length_aware_v6"])
    parser.add_argument("--planner_lookahead_size", type=int, default=64)
    parser.add_argument("--planner_short_threshold_tokens", type=int, default=256)
    parser.add_argument("--planner_max_consecutive_short", type=int, default=4)
    parser.add_argument("--planner_arrival_window_size", type=int, default=256)
    parser.add_argument("--planner_control_update_interval", type=int, default=64)
    parser.add_argument("--planner_target_short_share_bonus", type=float, default=0.2)
    parser.add_argument("--planner_min_short_share", type=float, default=0.5)
    parser.add_argument("--planner_max_short_share", type=float, default=0.75)
    parser.add_argument("--planner_queue_ratio_control_gain", type=float, default=1.0)
    parser.add_argument("--planner_queue_ratio_margin", type=float, default=0.08)
    parser.add_argument("--planner_max_ratio_adjustment", type=float, default=0.2)
    parser.add_argument("--disable_sort_within_batch", action="store_true")
    return parser.parse_args()


def add_bucket_stats(stats: dict, results: list[dict]) -> None:
    for bucket in ("short", "long"):
        bucket_results = [item for item in results if item["planner_bucket"] == bucket]
        stats[f"{bucket}_requests"] = len(bucket_results)
        if not bucket_results:
            continue
        latencies = [item["total_latency_ms"] for item in bucket_results]
        ttfts = [item["ttft_ms"] for item in bucket_results]
        stats[f"{bucket}_avg_latency_ms"] = round(mean(latencies), 2)
        stats[f"{bucket}_p95_latency_ms"] = round(percentile(latencies, 95), 2)
        stats[f"{bucket}_avg_ttft_ms"] = round(mean(ttfts), 2)
        stats[f"{bucket}_p95_ttft_ms"] = round(percentile(ttfts, 95), 2)


def main():
    args = parse_args()
    rows = load_jsonl(args.prompt_file)
    if args.limit > 0:
        rows = rows[: args.limit]
    prompts = [item["prompt"] if isinstance(item, dict) else item for item in rows]
    print(f"[INFO] 已加载 {len(prompts)} 条 prompt（来自 {args.prompt_file}）")

    engine = VLLM14BLengthAwareV6OfflineEngine(
        EngineConfig(
            model_path=args.model_path,
            tensor_parallel_size=args.tensor_parallel_size,
            dtype=args.dtype,
            gpu_memory_utilization=args.gpu_memory_utilization,
            enable_prefix_caching=args.enable_prefix_caching,
            max_model_len=args.max_model_len,
            max_num_seqs=args.max_num_seqs,
            max_num_batched_tokens=args.max_num_batched_tokens,
            load_format=args.load_format,
            quantization=args.quantization or None,
            enforce_eager=args.enforce_eager,
        )
    )
    estimated_tokens = engine.estimate_input_tokens(prompts)
    planner = OfflineLengthAwarePlanner(
        PlannerConfig(
            policy=args.planner_policy,
            batch_size=args.batch_size,
            lookahead_size=args.planner_lookahead_size,
            short_threshold_tokens=args.planner_short_threshold_tokens,
            max_consecutive_short=args.planner_max_consecutive_short,
            arrival_window_size=args.planner_arrival_window_size,
            control_update_interval=args.planner_control_update_interval,
            target_short_share_bonus=args.planner_target_short_share_bonus,
            min_short_share=args.planner_min_short_share,
            max_short_share=args.planner_max_short_share,
            queue_ratio_control_gain=args.planner_queue_ratio_control_gain,
            queue_ratio_margin=args.planner_queue_ratio_margin,
            max_ratio_adjustment=args.planner_max_ratio_adjustment,
            sort_within_batch=not args.disable_sort_within_batch,
        )
    )
    planned_requests = planner.build_requests(prompts=prompts, estimated_tokens=estimated_tokens, payloads=rows)
    planned_batches = planner.plan(planned_requests)
    planner_stats = planner.snapshot()

    print(
        "[INFO] planner="
        f"{planner_stats['planner_policy']} "
        f"batches={planner_stats['planner_total_batches']} "
        f"short_share={planner_stats['planner_actual_short_share']} "
        f"avg_batch_prompt_tokens={planner_stats['planner_avg_batch_prompt_tokens']}"
    )

    engine.reset_peak_memory()
    monitor = OfflineGpuMonitor(sample_interval_sec=args.monitor_sample_interval_sec)
    monitor.start()

    results = []
    print(f"\n[Benchmark] 共 {len(prompts)} 条 prompt，开始 length-aware 离线推理...")
    print("-" * 80)
    t_wall_start = time.perf_counter()
    processed = 0
    total_batches = len(planned_batches)
    for batch_idx, batch in enumerate(planned_batches, start=1):
        batch_prompts = [item.prompt for item in batch]
        batch_results = engine.generate_batch(
            prompts=batch_prompts,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        batch_min_tokens = min(item.estimated_tokens for item in batch)
        batch_max_tokens = max(item.estimated_tokens for item in batch)
        batch_short = sum(1 for item in batch if item.bucket == "short")
        batch_long = len(batch) - batch_short
        print(
            f"[batch {batch_idx:4d}/{total_batches}] "
            f"size={len(batch):2d} "
            f"est_tokens={batch_min_tokens:4d}-{batch_max_tokens:4d} "
            f"short={batch_short:2d} long={batch_long:2d}"
        )
        for planned, res in zip(batch, batch_results):
            processed += 1
            results.append(
                {
                    **res,
                    "planner_bucket": planned.bucket,
                    "planner_estimated_input_tokens": planned.estimated_tokens,
                    "planner_original_index": planned.original_index,
                    "planner_batch_index": batch_idx,
                }
            )
            print(
                f"  [{processed:4d}/{len(prompts)}]  "
                f"bucket={planned.bucket:5s}  "
                f"est_in={planned.estimated_tokens:4d}  "
                f"latency={res['total_latency_ms']:8.1f} ms  "
                f"ttft={res['ttft_ms']:8.1f} ms  "
                f"throughput={res['throughput_tps']:7.1f} token/s "
                f"output={res['output_tokens']:4d} tokens"
            )
    t_wall_end = time.perf_counter()

    stats = compute_benchmark_stats(
        results=results,
        wall_time_sec=t_wall_end - t_wall_start,
        max_new_tokens=args.max_new_tokens,
        peak_gpu_mem_gb=engine.peak_gpu_mem_gb(),
    )
    add_bucket_stats(stats, results)
    stats.update(monitor.stop())
    stats.update(planner_stats)
    print_benchmark_stats(stats, title="vllm_14b_length_aware_v6_offline")
    if args.output:
        save_json(args.output, stats)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
