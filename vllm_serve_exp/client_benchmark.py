from __future__ import annotations

import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from transformers import AutoTokenizer

from .common import (
    combine_result_with_mem_metrics,
    DEFAULT_PROMPT_FILE,
    compute_online_benchmark_stats,
    load_jsonl,
    parse_stream_event,
    print_benchmark_stats,
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
    parser.add_argument("--max_tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--sample_interval_sec", type=float, default=0.5)
    return parser.parse_args()


def stream_one(base_url: str, model: str, prompt: str, max_tokens: int, temperature: float, tokenizer) -> dict:
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
        "prompt": prompt,
        "output": output_text,
        "output_tokens": output_tokens,
        "ttft_ms": round((first_token_time - start) * 1000, 2),
        "latency_ms": round((end - start) * 1000, 2),
    }


def main():
    args = parse_args()
    prompts_data = load_jsonl(args.prompt_file)
    prompts = [item["prompt"] if isinstance(item, dict) else item for item in prompts_data]
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)

    print(f"[INFO] 已加载 {len(prompts)} 条 prompt（来自 {args.prompt_file}）")
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
                prompt,
                args.max_tokens,
                args.temperature,
                tokenizer,
            )
            for prompt in prompts
        ]
        for i, future in enumerate(as_completed(futures), start=1):
            res = future.result()
            results.append(res)
            print(
                f"  [{i:3d}/{len(prompts)}] "
                f"ttft={res['ttft_ms']:8.1f} ms  "
                f"latency={res['latency_ms']:8.1f} ms  "
                f"output={res['output_tokens']:4d} tokens"
            )
    t_wall_end = time.perf_counter()
    mem_metrics = monitor.stop()

    stats = compute_online_benchmark_stats(results, wall_time_sec=t_wall_end - t_wall_start)
    stats = combine_result_with_mem_metrics(stats, mem_metrics)
    print_benchmark_stats(stats)
    if args.output:
        save_json(args.output, stats)
        save_json(str(args.output).replace(".json", "_details.json"), {"requests": results})
        save_json(str(args.output).replace(".json", "_mem.json"), mem_metrics)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
