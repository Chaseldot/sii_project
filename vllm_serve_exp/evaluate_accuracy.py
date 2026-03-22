from __future__ import annotations

import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import (
    combine_result_with_mem_metrics,
    DEFAULT_EVAL_FILE,
    build_ceval_prompt,
    extract_answer,
    load_jsonl,
    print_accuracy_result,
    save_json,
)
from .monitor import OnlineExperimentMonitor


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM serve online accuracy evaluation")
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--model", type=str, required=True, help="served model name")
    parser.add_argument("--eval_file", type=str, default=str(DEFAULT_EVAL_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--baseline_acc", type=float, default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max_tokens", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--sample_interval_sec", type=float, default=0.5)
    return parser.parse_args()


def complete_one(base_url: str, model: str, prompt: str, max_tokens: int, temperature: float) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/v1/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("text", "")


def evaluate_online_accuracy(
    eval_data: list[dict],
    base_url: str,
    model: str,
    max_tokens: int,
    temperature: float,
    concurrency: int,
) -> tuple[int, list[dict]]:
    correct = 0
    wrong_cases = []
    completed = 0
    total = len(eval_data)
    indexed_results: list[tuple[str, str] | None] = [None] * total

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(
                complete_one,
                base_url,
                model,
                build_ceval_prompt(item),
                max_tokens,
                temperature,
            ): (i, item)
            for i, item in enumerate(eval_data)
        }

        for future in as_completed(futures):
            i, item = futures[future]
            output = future.result()
            pred = extract_answer(output)
            gold = item["answer"].upper()
            indexed_results[i] = (pred, gold)
            completed += 1
            if pred == gold:
                correct += 1
            if completed % 20 == 0 or completed == total:
                acc_so_far = correct / completed
                print(
                    f"  [{completed:4d}/{total}]  "
                    f"当前准确率: {acc_so_far*100:.1f}%  "
                    f"正确: {correct}  错误: {completed-correct}"
                )

    for i, item in enumerate(eval_data):
        pair = indexed_results[i]
        if pair is None:
            raise RuntimeError(f"Missing evaluation result for item {i}")
        pred, gold = pair
        if pred != gold:
            wrong_cases.append(
                {
                    "id": item.get("id", i),
                    "question": item["question"][:60] + "...",
                    "pred": pred,
                    "gold": gold,
                }
            )
    return correct, wrong_cases


def main():
    args = parse_args()
    eval_data = load_jsonl(args.eval_file)
    if args.limit > 0:
        eval_data = eval_data[: args.limit]
    print(f"[INFO] 已加载 {len(eval_data)} 道评测题（来自 {args.eval_file}）")
    print(f"[INFO] 开始在线 accuracy | concurrency={args.concurrency}")

    monitor = OnlineExperimentMonitor(
        base_url=args.base_url,
        sample_interval_sec=args.sample_interval_sec,
    )
    monitor.start()
    t_start = time.perf_counter()
    print(f"\n[Accuracy] 开始在线精度评测，共 {len(eval_data)} 道题...")
    print("-" * 60)

    correct, wrong_cases = evaluate_online_accuracy(
        eval_data=eval_data,
        base_url=args.base_url,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        concurrency=args.concurrency,
    )

    t_end = time.perf_counter()
    mem_metrics = monitor.stop()
    accuracy = correct / len(eval_data)
    result = {
        "total": len(eval_data),
        "correct": correct,
        "wrong": len(eval_data) - correct,
        "accuracy": round(accuracy, 4),
        "accuracy_pct": round(accuracy * 100, 2),
        "eval_time_sec": round(t_end - t_start, 2),
        "wrong_cases": wrong_cases[:10],
    }
    merged_result = combine_result_with_mem_metrics(result, mem_metrics)
    print_accuracy_result(merged_result, args.baseline_acc)
    if args.output:
        out = {k: v for k, v in merged_result.items() if k != "wrong_cases"}
        out["wrong_cases_count"] = merged_result["wrong"]
        save_json(args.output, out)
        save_json(str(args.output).replace(".json", "_mem.json"), mem_metrics)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
