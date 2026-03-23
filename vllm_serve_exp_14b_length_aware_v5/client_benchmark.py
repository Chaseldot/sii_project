from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from transformers import AutoTokenizer

from .common import (
    combine_result_with_mem_metrics,
    compute_length_bucket_stats,
    DEFAULT_PROMPT_FILE,
    compute_online_benchmark_stats,
    load_jsonl,
    parse_stream_event,
    print_benchmark_stats,
    print_length_bucket_stats,
    save_json,
)
from .monitor import OnlineExperimentMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM serve online benchmark")
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--model", type=str, required=True, help="served model name")
    parser.add_argument("--model_path", type=str, required=True, help="local model path for tokenizer")
    parser.add_argument("--prompt_file", type=str, default=str(DEFAULT_PROMPT_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sample_interval_sec", type=float, default=0.5)
    parser.add_argument("--scheduler_stats_url", type=str, default=None)
    return parser.parse_args()


def fetch_json(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def stream_one(
    base_url: str,
    model: str,
    prompt_id,
    prompt: str,
    prompt_chars: int,
    length_bucket: str | None,
    source_prompt_file: str | None,
    source_id,
    mixed_id,
    max_tokens: int,
    temperature: float,
    tokenizer,
) -> dict:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/v1/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    text_chunks = []
    first_token_time = None
    start = time.perf_counter()
    with urllib.request.urlopen(request) as resp:
        for raw_line in resp:
            chunk_text, done = parse_stream_event(raw_line)
            now = time.perf_counter()
            if chunk_text:
                text_chunks.append(chunk_text)
                if first_token_time is None:
                    first_token_time = now
            if done:
                break
    end = time.perf_counter()

    output_text = "".join(text_chunks)
    output_tokens = len(tokenizer.encode(output_text, add_special_tokens=False))
    if first_token_time is None:
        first_token_time = end

    return {
        "prompt_id": prompt_id,
        "prompt": prompt,
        "prompt_chars": prompt_chars,
        "length_bucket": length_bucket,
        "source_prompt_file": source_prompt_file,
        "source_id": source_id,
        "mixed_id": mixed_id,
        "output": output_text,
        "output_tokens": output_tokens,
        "ttft_ms": round((first_token_time - start) * 1000, 2),
        "latency_ms": round((end - start) * 1000, 2),
    }


def main():
    args = parse_args()
    prompts_data = load_jsonl(args.prompt_file)
    if args.limit > 0:
        prompts_data = prompts_data[: args.limit]

    prompt_records = []
    for i, item in enumerate(prompts_data, start=1):
        if isinstance(item, dict):
            prompt = item["prompt"]
            prompt_records.append(
                {
                    "id": item.get("id", i),
                    "prompt": prompt,
                    "prompt_chars": item.get("prompt_chars", len(prompt)),
                    "length_bucket": item.get("length_bucket"),
                    "source_prompt_file": item.get("source_prompt_file"),
                    "source_id": item.get("source_id"),
                    "mixed_id": item.get("mixed_id"),
                }
            )
        else:
            prompt_records.append(
                {
                    "id": i,
                    "prompt": item,
                    "prompt_chars": len(item),
                    "length_bucket": None,
                    "source_prompt_file": None,
                    "source_id": None,
                    "mixed_id": None,
                }
            )
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)

    print(f"[INFO] 已加载 {len(prompt_records)} 条 prompt（来自 {args.prompt_file}）")
    print(f"[INFO] 开始在线 benchmark | concurrency={args.concurrency}")

    results = []
    monitor = OnlineExperimentMonitor(
        base_url=args.base_url,
        sample_interval_sec=args.sample_interval_sec,
    )
    monitor.start()
    t_wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                stream_one,
                args.base_url,
                args.model,
                item["id"],
                item["prompt"],
                item["prompt_chars"],
                item["length_bucket"],
                item["source_prompt_file"],
                item["source_id"],
                item["mixed_id"],
                args.max_tokens,
                args.temperature,
                tokenizer,
            )
            for item in prompt_records
        ]
        for i, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            results.append(res)
            print(
                f"  [{i:3d}/{len(prompt_records)}] "
                f"ttft={res['ttft_ms']:8.1f} ms  "
                f"latency={res['latency_ms']:8.1f} ms  "
                f"output={res['output_tokens']:4d} tokens"
            )
    t_wall_end = time.perf_counter()
    mem_metrics = monitor.stop()

    stats = compute_online_benchmark_stats(results, wall_time_sec=t_wall_end - t_wall_start)
    stats = combine_result_with_mem_metrics(stats, mem_metrics)
    length_bucket_stats = compute_length_bucket_stats(results)
    if length_bucket_stats:
        stats["length_bucket_stats"] = length_bucket_stats
    scheduler_stats = None
    if args.scheduler_stats_url:
        scheduler_stats = fetch_json(args.scheduler_stats_url)
        if scheduler_stats:
            stats["scheduler_stats"] = scheduler_stats
    print_benchmark_stats(stats)
    print_length_bucket_stats(length_bucket_stats)
    if args.output:
        save_json(args.output, stats)
        save_json(str(args.output).replace(".json", "_details.json"), {"requests": results})
        save_json(str(args.output).replace(".json", "_mem.json"), mem_metrics)
        if length_bucket_stats:
            save_json(str(args.output).replace(".json", "_length_stats.json"), length_bucket_stats)
        if scheduler_stats:
            save_json(str(args.output).replace(".json", "_scheduler_stats.json"), scheduler_stats)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
