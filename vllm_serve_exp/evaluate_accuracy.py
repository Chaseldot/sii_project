from __future__ import annotations

import argparse
import json
import time
import urllib.request

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


def main():
    args = parse_args()
    eval_data = load_jsonl(args.eval_file)
    if args.limit > 0:
        eval_data = eval_data[: args.limit]
    print(f"[INFO] 已加载 {len(eval_data)} 道评测题（来自 {args.eval_file}）")

    correct = 0
    wrong_cases = []
    monitor = OnlineExperimentMonitor(
        base_url=args.base_url,
        sample_interval_sec=args.sample_interval_sec,
    )
    monitor.start()
    t_start = time.perf_counter()
    print(f"\n[Accuracy] 开始在线精度评测，共 {len(eval_data)} 道题...")
    print("-" * 60)

    for i, item in enumerate(eval_data):
        prompt = build_ceval_prompt(item)
        output = complete_one(args.base_url, args.model, prompt, args.max_tokens, args.temperature)
        pred = extract_answer(output)
        gold = item["answer"].upper()
        if pred == gold:
            correct += 1
        else:
            wrong_cases.append(
                {
                    "id": item.get("id", i),
                    "question": item["question"][:60] + "...",
                    "pred": pred,
                    "gold": gold,
                }
            )
        if (i + 1) % 20 == 0 or (i + 1) == len(eval_data):
            acc_so_far = correct / (i + 1)
            print(
                f"  [{i+1:4d}/{len(eval_data)}]  "
                f"当前准确率: {acc_so_far*100:.1f}%  "
                f"正确: {correct}  错误: {i+1-correct}"
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
