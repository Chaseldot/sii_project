from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterator, Sequence


ROOT = Path(__file__).resolve().parent
DEFAULT_PROMPT_FILE = ROOT / "data" / "test_prompts.jsonl"
DEFAULT_EVAL_FILE = ROOT / "data" / "ceval_subset.jsonl"
DEFAULT_MAX_NEW_TOKENS = 256


def load_jsonl(path: str | Path) -> list[dict]:
    items = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_json(path: str | Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def chunked(seq: Sequence, size: int) -> Iterator[Sequence]:
    if size <= 0:
        raise ValueError("size must be > 0")
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def build_ceval_prompt(item: dict) -> str:
    return (
        "以下是一道单选题，请直接回答选项字母（A/B/C/D），不要有任何解释。\n\n"
        f"题目：{item['question']}\n"
        f"A. {item['A']}\n"
        f"B. {item['B']}\n"
        f"C. {item['C']}\n"
        f"D. {item['D']}\n"
        "答案："
    )


def extract_answer(output: str) -> str:
    for ch in output.strip():
        if ch.upper() in ("A", "B", "C", "D"):
            return ch.upper()
    return "X"


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (q / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def compute_benchmark_stats(
    results: list[dict],
    wall_time_sec: float,
    max_new_tokens: int,
    peak_gpu_mem_gb: float,
) -> dict:
    latencies = [item["total_latency_ms"] for item in results]
    ttfts = [item["ttft_ms"] for item in results]
    total_output_tokens = sum(item["output_tokens"] for item in results)
    exact_ttft = sum(1 for item in results if item.get("ttft_source") == "vllm_metrics")
    fallback_ttft = sum(1 for item in results if item.get("ttft_source") != "vllm_metrics")
    exact_latency = sum(1 for item in results if item.get("total_latency_source") == "vllm_metrics")
    fallback_latency = sum(1 for item in results if item.get("total_latency_source") != "vllm_metrics")

    return {
        "total_prompts": len(results),
        "total_output_tokens": total_output_tokens,
        "wall_time_sec": round(wall_time_sec, 2),
        "max_new_tokens_cfg": max_new_tokens,
        "overall_throughput_tps": round(total_output_tokens / wall_time_sec, 2) if wall_time_sec > 0 else 0.0,
        "avg_latency_ms": round(mean(latencies), 2),
        "p50_latency_ms": round(percentile(latencies, 50), 2),
        "p95_latency_ms": round(percentile(latencies, 95), 2),
        "p99_latency_ms": round(percentile(latencies, 99), 2),
        "avg_ttft_ms": round(mean(ttfts), 2),
        "p95_ttft_ms": round(percentile(ttfts, 95), 2),
        "peak_gpu_mem_gb": round(peak_gpu_mem_gb, 3),
        "ttft_exact_requests": exact_ttft,
        "ttft_fallback_requests": fallback_ttft,
        "total_latency_exact_requests": exact_latency,
        "total_latency_fallback_requests": fallback_latency,
    }


def print_benchmark_stats(stats: dict, title: str = "vllm_base") -> None:
    labels = {
        "total_prompts": "测试 prompt 数",
        "total_output_tokens": "总输出 tokens",
        "wall_time_sec": "总耗时 (sec)",
        "max_new_tokens_cfg": "max_new_tokens 配置",
        "overall_throughput_tps": "整体吞吐率 (tokens/sec)  ",
        "avg_latency_ms": "平均延迟 (ms)            ",
        "p50_latency_ms": "P50 延迟 (ms)            ",
        "p95_latency_ms": "P95 延迟 (ms)            ",
        "p99_latency_ms": "P99 延迟 (ms)            ",
        "avg_ttft_ms": "平均 TTFT (ms)            ",
        "p95_ttft_ms": "P95 TTFT (ms)             ",
        "peak_gpu_mem_gb": "峰值显存 (GB)             ",
    }
    print("\n" + "=" * 68)
    print(f" Benchmark 结果汇总（{title}）")
    print("=" * 68)
    for key, label in labels.items():
        print(f"  {label:<40s}: {stats.get(key, 'N/A')}")
    print("=" * 68)


def print_accuracy_result(result: dict, baseline_acc: float | None = None) -> None:
    print("\n" + "=" * 60)
    print(" 精度评测结果")
    print("=" * 60)
    print(f"  总题数       : {result['total']}")
    print(f"  答对题数     : {result['correct']}")
    print(f"  答错题数     : {result['wrong']}")
    print(f"  准确率       : {result['accuracy_pct']:.2f}%")
    print(f"  评测耗时     : {result['eval_time_sec']} sec")
    if baseline_acc is not None:
        drop = baseline_acc - result["accuracy"]
        status = "达标" if drop <= 0.05 else "超标（扣分）"
        print("-" * 60)
        print(f"  基线准确率   : {baseline_acc*100:.2f}%")
        print(f"  精度下降     : {drop*100:.2f}% （上限 5%）")
        print(f"  精度约束状态 : {status}")
    print("=" * 60)
