from __future__ import annotations

import argparse
import json

from .common import DEFAULT_MAX_NEW_TOKENS, save_json
from .engine import EngineConfig, VLLMEngine


def render_result(result: dict, peak_gpu_mem_gb: float) -> str:
    return "\n".join(
        [
            "",
            "=" * 64,
            " vLLM 推理结果",
            "=" * 64,
            f"  输入   : {result['prompt']}",
            f"  输出   : {result['output']}",
            "-" * 64,
            f"  输入 tokens   : {result['input_tokens']}",
            f"  输出 tokens   : {result['output_tokens']}",
            f"  总延迟         : {result['total_latency_ms']} ms",
            f"  TTFT (近似)   : {result['ttft_ms']} ms",
            f"  吞吐率         : {result['throughput_tps']} tokens/sec",
            f"  峰值显存       : {peak_gpu_mem_gb:.3f} GB",
            "=" * 64,
        ]
    )


def parse_args():
    parser = argparse.ArgumentParser(description="vLLM 单条推理验证")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument(
        "--prompt",
        type=str,
        default="请用三句话解释大语言模型推理中KV Cache的作用。",
        help="测试 prompt",
    )
    parser.add_argument("--max_new_tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--tensor_parallel_size", type=int, default=1)
    parser.add_argument("--dtype", type=str, default="auto")
    parser.add_argument("--gpu_memory_utilization", type=float, default=0.9)
    parser.add_argument("--enable_prefix_caching", action="store_true")
    parser.add_argument("--max_model_len", type=int, default=None)
    parser.add_argument("--output", type=str, default=None, help="可选 JSON 输出路径")
    return parser.parse_args()


def main():
    args = parse_args()
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
    engine.reset_peak_memory()
    result = engine.generate_one(
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
    )
    print(render_result(result, engine.peak_gpu_mem_gb()))
    if args.output:
        save_json(
            args.output,
            {
                **result,
                "peak_gpu_mem_gb": round(engine.peak_gpu_mem_gb(), 3),
            },
        )
        print(f"\n[INFO] 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()

