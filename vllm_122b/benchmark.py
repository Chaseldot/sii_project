from __future__ import annotations

import argparse
import time

from .common import (
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_PROMPT_FILE,
    chunked,
    compute_benchmark_stats,
    load_jsonl,
    print_benchmark_stats,
    save_json,
)
from .engine import EngineConfig, VLLM122BEngine
from .monitor import OfflineGpuMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM 122B 离线吞吐 & 延迟基准测试")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument("--prompt_file", type=str, default=str(DEFAULT_PROMPT_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--max_new_tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--tensor_parallel_size", type=int, default=4)
    parser.add_argument("--dtype", type=str, default="bfloat16")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.9)
    parser.add_argument("--enable_prefix_caching", action="store_true")
    parser.add_argument("--max_model_len", type=int, default=8192)
    parser.add_argument("--max_num_seqs", type=int, default=12)
    parser.add_argument("--max_num_batched_tokens", type=int, default=8192)
    parser.add_argument("--load_format", type=str, default="auto")
    parser.add_argument("--quantization", type=str, default="")
    parser.add_argument("--enforce_eager", action="store_true")
    parser.add_argument("--monitor_sample_interval_sec", type=float, default=0.5)
    return parser.parse_args()


def main():
    args = parse_args()
    prompts = load_jsonl(args.prompt_file)
    if args.limit > 0:
        prompts = prompts[: args.limit]
    prompts = [item["prompt"] if isinstance(item, dict) else item for item in prompts]
    print(f"[INFO] 已加载 {len(prompts)} 条 prompt（来自 {args.prompt_file}）")

    engine = VLLM122BEngine(
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
    engine.reset_peak_memory()
    monitor = OfflineGpuMonitor(sample_interval_sec=args.monitor_sample_interval_sec)
    monitor.start()

    results = []
    print(f"\n[Benchmark] 共 {len(prompts)} 条 prompt，开始离线推理...")
    print("-" * 68)
    t_wall_start = time.perf_counter()
    processed = 0
    for batch in chunked(prompts, args.batch_size):
        batch_results = engine.generate_batch(
            prompts=list(batch),
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        for res in batch_results:
            processed += 1
            results.append(res)
            print(
                f"  [{processed:4d}/{len(prompts)}]  "
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
    stats.update(monitor.stop())
    print_benchmark_stats(stats, title="vllm_122b")
    if args.output:
        save_json(args.output, stats)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
