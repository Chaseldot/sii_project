from __future__ import annotations

import argparse
import time

from .common import (
    DEFAULT_EVAL_FILE,
    build_ceval_prompt,
    extract_answer,
    load_jsonl,
    print_accuracy_result,
    save_json,
)
from .engine import EngineConfig, VLLM14BLengthAwareV6OfflineEngine
from .planner import OfflineLengthAwarePlanner, PlannerConfig
from vllm_14b.monitor import OfflineGpuMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM 14B length-aware v6 C-Eval 精度评测")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument("--eval_file", type=str, default=str(DEFAULT_EVAL_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--baseline_acc", type=float, default=None)
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条，0 表示全部")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--max_new_tokens", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
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


def main():
    args = parse_args()
    eval_data = load_jsonl(args.eval_file)
    if args.limit > 0:
        eval_data = eval_data[: args.limit]
    prompts = [build_ceval_prompt(item) for item in eval_data]
    print(f"[INFO] 已加载 {len(eval_data)} 道评测题（来自 {args.eval_file}）")

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
    planned_requests = planner.build_requests(prompts=prompts, estimated_tokens=estimated_tokens, payloads=eval_data)
    planned_batches = planner.plan(planned_requests)
    planner_stats = planner.snapshot()

    monitor = OfflineGpuMonitor(sample_interval_sec=args.monitor_sample_interval_sec)
    monitor.start()

    predictions: dict[int, dict] = {}
    t_start = time.perf_counter()
    inferred = 0
    print(f"\n[Accuracy] 开始 length-aware 精度评测，共 {len(eval_data)} 道题...")
    print("-" * 72)

    for batch_idx, batch in enumerate(planned_batches, start=1):
        results = engine.generate_batch(
            prompts=[item.prompt for item in batch],
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        for planned, res in zip(batch, results):
            inferred += 1
            predictions[planned.original_index] = {
                "pred": extract_answer(res["output"]),
                "bucket": planned.bucket,
            }
        if inferred % 20 == 0 or inferred == len(eval_data):
            print(
                f"  [batch {batch_idx:4d}/{len(planned_batches)}] "
                f"已推理: {inferred:4d}/{len(eval_data)}"
            )

    correct = 0
    bucket_total = {"short": 0, "long": 0}
    bucket_correct = {"short": 0, "long": 0}
    wrong_cases = []
    for idx, item in enumerate(eval_data, start=1):
        pred_info = predictions[idx - 1]
        pred = pred_info["pred"]
        bucket = pred_info["bucket"]
        gold = item["answer"].upper()
        bucket_total[bucket] += 1
        if pred == gold:
            correct += 1
            bucket_correct[bucket] += 1
        else:
            wrong_cases.append(
                {
                    "id": item.get("id", idx),
                    "question": item["question"][:60] + "...",
                    "pred": pred,
                    "gold": gold,
                    "bucket": bucket,
                }
            )

        if idx % 20 == 0 or idx == len(eval_data):
            acc_so_far = correct / idx
            print(
                f"  [{idx:4d}/{len(eval_data)}]  "
                f"当前准确率: {acc_so_far*100:.1f}%  "
                f"正确: {correct}  错误: {idx-correct}"
            )

    t_end = time.perf_counter()
    accuracy = correct / len(eval_data)
    result = {
        "total": len(eval_data),
        "correct": correct,
        "wrong": len(eval_data) - correct,
        "accuracy": round(accuracy, 4),
        "accuracy_pct": round(accuracy * 100, 2),
        "eval_time_sec": round(t_end - t_start, 2),
        "short_total": bucket_total["short"],
        "long_total": bucket_total["long"],
        "short_accuracy": round(bucket_correct["short"] / bucket_total["short"], 4) if bucket_total["short"] else None,
        "long_accuracy": round(bucket_correct["long"] / bucket_total["long"], 4) if bucket_total["long"] else None,
        "wrong_cases": wrong_cases[:10],
    }
    result.update(monitor.stop())
    result.update(planner_stats)
    print_accuracy_result(result, args.baseline_acc)

    if args.output:
        out = {k: v for k, v in result.items() if k != "wrong_cases"}
        out["wrong_cases_count"] = result["wrong"]
        save_json(args.output, out)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
