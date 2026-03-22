from __future__ import annotations

import argparse

from .common import DEFAULT_MAX_NEW_TOKENS, save_json
from .engine import EngineConfig, VLLM122BEngine


def render_result(result: dict, peak_gpu_mem_gb: float) -> str:
    return "\n".join(
        [
            "",
            "=" * 64,
            " vLLM 122B 推理结果",
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
    parser = argparse.ArgumentParser(description="vLLM 122B 单条离线推理验证")
    parser.add_argument("--model_path", type=str, required=True, help="模型本地路径")
    parser.add_argument(
        "--prompt",
        type=str,
        default="请从系统设计角度分析大模型推理中的 KV Cache 与动态 Batch。",
        help="测试 prompt",
    )
    parser.add_argument("--max_new_tokens", type=int, default=DEFAULT_MAX_NEW_TOKENS)
    parser.add_argument("--temperature", type=float, default=0.0)
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
    parser.add_argument("--output", type=str, default=None, help="可选 JSON 输出路径")
    return parser.parse_args()


def main():
    args = parse_args()
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
