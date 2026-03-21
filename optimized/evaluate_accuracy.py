from __future__ import annotations

import argparse
import time

from .common import (
    DEFAULT_EVAL_FILE,
    DEFAULT_MAX_NEW_TOKENS,
    build_ceval_prompt,
    chunked,
    extract_answer,
    load_jsonl,
    print_accuracy_result,
    save_json,
)
from .engine import EngineConfig, VLLMEngine


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM C-Eval 精度评测")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument("--eval_file", type=str, default=str(DEFAULT_EVAL_FILE))
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--baseline_acc", type=float, default=None)
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条，0 表示全部")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--max_new_tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
    parser.add_argument("--dtype", type=str, default="auto")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.9)
    parser.add_argument("--enable_prefix_caching", action="store_true")
    parser.add_argument("--max_model_len", type=int, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    eval_data = load_jsonl(args.eval_file)
    if args.limit > 0:
        eval_data = eval_data[: args.limit]
    print(f"[INFO] 已加载 {len(eval_data)} 道评测题（来自 {args.eval_file}）")

    engine = VLLMEngine(
        EngineConfig(
            model_path=args.model_path,
            tensor_parallel_size=args.tensor_parallel_size,
            dtype=args.dtype,
            gpu_memory_utilization=args.gpu_memory_utilization,
            enable_prefix_caching=args.enable_prefix_caching,
            max_model_len=args.max_model_len,
        )
    )

    correct = 0
    wrong_cases = []
    t_start = time.perf_counter()
    processed = 0
    print(f"\n[Accuracy] 开始精度评测，共 {len(eval_data)} 道题...")
    print("-" * 60)

    for batch in chunked(eval_data, args.batch_size):
        prompts = [build_ceval_prompt(item) for item in batch]
        results = engine.generate_batch(
            prompts=prompts,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
        )
        for item, res in zip(batch, results):
            processed += 1
            pred = extract_answer(res["output"])
            gold = item["answer"].upper()
            if pred == gold:
                correct += 1
            else:
                wrong_cases.append(
                    {
                        "id": item.get("id", processed),
                        "question": item["question"][:60] + "...",
                        "pred": pred,
                        "gold": gold,
                    }
                )

            if processed % 20 == 0 or processed == len(eval_data):
                acc_so_far = correct / processed
                print(
                    f"  [{processed:4d}/{len(eval_data)}]  "
                    f"当前准确率: {acc_so_far*100:.1f}%  "
                    f"正确: {correct}  错误: {processed-correct}"
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
        "wrong_cases": wrong_cases[:10],
    }
    print_accuracy_result(result, args.baseline_acc)

    if args.output:
        out = {k: v for k, v in result.items() if k != "wrong_cases"}
        out["wrong_cases_count"] = result["wrong"]
        save_json(args.output, out)
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()

