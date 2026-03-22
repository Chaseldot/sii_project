from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


BENCHMARK_COLUMNS = [
    "experiment",
    "total_prompts",
    "total_output_tokens",
    "wall_time_sec",
    "overall_throughput_tps",
    "avg_latency_ms",
    "p95_latency_ms",
    "avg_ttft_ms",
    "p95_ttft_ms",
    "avg_gpu_mem_gb",
    "peak_gpu_mem_gb",
    "avg_gpu_mem_utilization_perc",
    "peak_gpu_mem_utilization_perc",
    "avg_kv_cache_usage_perc",
    "max_kv_cache_usage_perc",
    "avg_cpu_cache_usage_perc",
    "max_cpu_cache_usage_perc",
    "avg_num_requests_waiting",
    "max_num_requests_waiting",
    "avg_num_requests_running",
    "max_num_requests_running",
    "avg_num_requests_swapped",
    "max_num_requests_swapped",
]

ACCURACY_COLUMNS = [
    "experiment",
    "total",
    "correct",
    "wrong",
    "accuracy",
    "accuracy_pct",
    "eval_time_sec",
    "avg_gpu_mem_gb",
    "peak_gpu_mem_gb",
    "avg_gpu_mem_utilization_perc",
    "peak_gpu_mem_utilization_perc",
    "avg_kv_cache_usage_perc",
    "max_kv_cache_usage_perc",
    "avg_cpu_cache_usage_perc",
    "max_cpu_cache_usage_perc",
]

BENCHMARK_METRIC_DESCRIPTIONS = {
    "total_prompts": "测试 prompt 数",
    "total_output_tokens": "总输出 tokens",
    "wall_time_sec": "总耗时 (sec)",
    "overall_throughput_tps": "整体吞吐率 (tokens/sec)",
    "avg_latency_ms": "平均延迟 (ms)",
    "p95_latency_ms": "P95 延迟 (ms)",
    "avg_ttft_ms": "平均 TTFT (ms)",
    "p95_ttft_ms": "P95 TTFT (ms)",
    "initial_gpu_mem_gb": "初始 GPU 显存占用 (GB)",
    "final_gpu_mem_gb": "结束 GPU 显存占用 (GB)",
    "min_gpu_mem_gb": "最小 GPU 显存占用 (GB)",
    "avg_gpu_mem_gb": "平均 GPU 显存占用 (GB)",
    "peak_gpu_mem_gb": "峰值 GPU 显存占用 (GB)",
    "gpu_total_mem_gb": "GPU 总显存 (GB)",
    "min_gpu_mem_utilization_perc": "最小 GPU 显存占用比例",
    "avg_gpu_mem_utilization_perc": "平均 GPU 显存占用比例",
    "peak_gpu_mem_utilization_perc": "峰值 GPU 显存占用比例",
    "min_kv_cache_usage_perc": "最小 KV Cache 使用率",
    "avg_kv_cache_usage_perc": "平均 KV Cache 使用率",
    "max_kv_cache_usage_perc": "最大 KV Cache 使用率",
    "min_cpu_cache_usage_perc": "最小 CPU Cache 使用率",
    "avg_cpu_cache_usage_perc": "平均 CPU Cache 使用率",
    "max_cpu_cache_usage_perc": "最大 CPU Cache 使用率",
    "min_num_requests_waiting": "最小等待请求数",
    "avg_num_requests_waiting": "平均等待请求数",
    "max_num_requests_waiting": "最大等待请求数",
    "min_num_requests_running": "最小运行请求数",
    "avg_num_requests_running": "平均运行请求数",
    "max_num_requests_running": "最大运行请求数",
    "min_num_requests_swapped": "最小交换请求数",
    "avg_num_requests_swapped": "平均交换请求数",
    "max_num_requests_swapped": "最大交换请求数",
    "monitor_sample_interval_sec": "监控采样间隔 (秒)",
    "monitor_gpu_samples": "GPU 监控采样点数",
    "monitor_kv_samples": "KV Cache 监控采样点数",
    "monitor_cpu_cache_samples": "CPU Cache 监控采样点数",
}

ACCURACY_METRIC_DESCRIPTIONS = {
    "total": "评测题目数",
    "correct": "答对题数",
    "wrong": "答错题数",
    "accuracy": "准确率",
    "accuracy_pct": "准确率 (%)",
    "eval_time_sec": "评测耗时 (sec)",
    "initial_gpu_mem_gb": "初始 GPU 显存占用 (GB)",
    "final_gpu_mem_gb": "结束 GPU 显存占用 (GB)",
    "min_gpu_mem_gb": "最小 GPU 显存占用 (GB)",
    "avg_gpu_mem_gb": "平均 GPU 显存占用 (GB)",
    "peak_gpu_mem_gb": "峰值 GPU 显存占用 (GB)",
    "gpu_total_mem_gb": "GPU 总显存 (GB)",
    "min_gpu_mem_utilization_perc": "最小 GPU 显存占用比例",
    "avg_gpu_mem_utilization_perc": "平均 GPU 显存占用比例",
    "peak_gpu_mem_utilization_perc": "峰值 GPU 显存占用比例",
    "min_kv_cache_usage_perc": "最小 KV Cache 使用率",
    "avg_kv_cache_usage_perc": "平均 KV Cache 使用率",
    "max_kv_cache_usage_perc": "最大 KV Cache 使用率",
    "min_cpu_cache_usage_perc": "最小 CPU Cache 使用率",
    "avg_cpu_cache_usage_perc": "平均 CPU Cache 使用率",
    "max_cpu_cache_usage_perc": "最大 CPU Cache 使用率",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize vLLM serve experiment results")
    parser.add_argument(
        "--result_root",
        type=str,
        default="/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results/vllm_serve",
    )
    parser.add_argument("--prefix", type=str, default="")
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--results_table_output", type=str, default=None)
    parser.add_argument("--benchmark_csv", type=str, default=None)
    parser.add_argument("--accuracy_csv", type=str, default=None)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def experiment_sort_key(name: str) -> tuple[int, int | str]:
    if "_c" in name:
        suffix = name.rsplit("_c", maxsplit=1)[-1]
        if suffix.isdigit():
            return (0, int(suffix))
    return (1, name)


def collect_rows(result_root: Path, filename: str, prefix: str = "") -> list[dict]:
    rows = []
    if not result_root.exists():
        return rows

    for exp_dir in result_root.iterdir():
        if not exp_dir.is_dir():
            continue
        if prefix and not exp_dir.name.startswith(prefix):
            continue
        result_file = exp_dir / filename
        if not result_file.exists():
            continue
        payload = load_json(result_file)
        row = {"experiment": exp_dir.name}
        row.update(payload)
        rows.append(row)

    return sorted(rows, key=lambda row: experiment_sort_key(row["experiment"]))


def collect_benchmark_rows(result_root: Path, prefix: str = "") -> list[dict]:
    return collect_rows(result_root, "benchmark_online.json", prefix=prefix)


def collect_accuracy_rows(result_root: Path, prefix: str = "") -> list[dict]:
    return collect_rows(result_root, "accuracy_online.json", prefix=prefix)


def format_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def render_markdown_table(rows: list[dict], columns: list[str] | None = None) -> str:
    if not rows:
        return "_No data_"
    if columns is None:
        columns = list(rows[0].keys())

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(format_cell(row.get(column, "")) for column in columns) + " |")
    return "\n".join([header, separator, *body])


def render_transposed_markdown_table(
    rows: list[dict],
    metrics: list[str],
    descriptions: dict[str, str],
) -> str:
    if not rows:
        return "_No data_"

    header = ["指标", "含义", *[row["experiment"] for row in rows]]
    separator = ["---"] * len(header)
    body = []
    for metric in metrics:
        if metric == "experiment":
            continue
        values = [metric, descriptions.get(metric, "")]
        for row in rows:
            values.append(format_cell(row.get(metric, "")))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join(
        [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
            *body,
        ]
    )


def save_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def build_report(result_root: Path, prefix: str = "") -> str:
    benchmark_rows = collect_benchmark_rows(result_root, prefix=prefix)
    accuracy_rows = collect_accuracy_rows(result_root, prefix=prefix)

    sections = [
        "# vLLM Serve Experiment Summary",
        "",
        f"- result_root: `{result_root}`",
        f"- prefix: `{prefix or '*'}`",
        "",
        "## Benchmark",
        "",
        render_markdown_table(benchmark_rows, BENCHMARK_COLUMNS),
        "",
        "## Accuracy",
        "",
        render_markdown_table(accuracy_rows, ACCURACY_COLUMNS),
        "",
    ]
    return "\n".join(sections)


def build_results_table_report(result_root: Path, prefix: str = "") -> str:
    benchmark_rows = collect_benchmark_rows(result_root, prefix=prefix)
    accuracy_rows = collect_accuracy_rows(result_root, prefix=prefix)

    sections = [
        "# vLLM Serve Results Table",
        "",
        f"- result_root: `{result_root}`",
        f"- prefix: `{prefix or '*'}`",
        "",
        "## Benchmark",
        "",
        render_transposed_markdown_table(
            benchmark_rows,
            BENCHMARK_COLUMNS,
            BENCHMARK_METRIC_DESCRIPTIONS,
        ),
        "",
        "## Accuracy",
        "",
        render_transposed_markdown_table(
            accuracy_rows,
            ACCURACY_COLUMNS,
            ACCURACY_METRIC_DESCRIPTIONS,
        ),
        "",
    ]
    return "\n".join(sections)


def main():
    args = parse_args()
    result_root = Path(args.result_root)
    report = build_report(result_root, prefix=args.prefix)
    results_table_report = build_results_table_report(result_root, prefix=args.prefix)

    benchmark_rows = collect_benchmark_rows(result_root, prefix=args.prefix)
    accuracy_rows = collect_accuracy_rows(result_root, prefix=args.prefix)

    output = Path(args.output) if args.output else result_root / "summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")

    results_table_output = (
        Path(args.results_table_output)
        if args.results_table_output
        else result_root / "results_table.md"
    )
    results_table_output.parent.mkdir(parents=True, exist_ok=True)
    results_table_output.write_text(results_table_report, encoding="utf-8")

    benchmark_csv = Path(args.benchmark_csv) if args.benchmark_csv else result_root / "benchmark_summary.csv"
    accuracy_csv = Path(args.accuracy_csv) if args.accuracy_csv else result_root / "accuracy_summary.csv"
    save_csv(benchmark_csv, benchmark_rows, BENCHMARK_COLUMNS)
    save_csv(accuracy_csv, accuracy_rows, ACCURACY_COLUMNS)

    print(f"[INFO] 汇总 Markdown 已保存至: {output}")
    print(f"[INFO] 转置结果表已保存至: {results_table_output}")
    print(f"[INFO] Benchmark CSV 已保存至: {benchmark_csv}")
    print(f"[INFO] Accuracy CSV 已保存至: {accuracy_csv}")


if __name__ == "__main__":
    main()
