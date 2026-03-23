from __future__ import annotations

import time
from dataclasses import dataclass

import torch

from .common import DEFAULT_MAX_NEW_TOKENS


@dataclass
class EngineConfig:
    model_path: str
    tensor_parallel_size: int = 1
    dtype: str = "bfloat16"
    gpu_memory_utilization: float = 0.9
    trust_remote_code: bool = True
    enable_prefix_caching: bool = True
    max_model_len: int | None = 8192
    max_num_seqs: int | None = None
    max_num_batched_tokens: int | None = 8192
    load_format: str = "auto"
    quantization: str | None = None
    enforce_eager: bool = False


class VLLM14BLengthAwareV6OfflineEngine:
    def __init__(self, config: EngineConfig):
        from vllm import LLM

        llm_kwargs = {
            "model": config.model_path,
            "tensor_parallel_size": config.tensor_parallel_size,
            "dtype": config.dtype,
            "gpu_memory_utilization": config.gpu_memory_utilization,
            "trust_remote_code": config.trust_remote_code,
            "enable_prefix_caching": config.enable_prefix_caching,
            "load_format": config.load_format,
            "enforce_eager": config.enforce_eager,
        }
        if config.max_model_len is not None:
            llm_kwargs["max_model_len"] = config.max_model_len
        if config.max_num_seqs is not None:
            llm_kwargs["max_num_seqs"] = config.max_num_seqs
        if config.max_num_batched_tokens is not None:
            llm_kwargs["max_num_batched_tokens"] = config.max_num_batched_tokens
        if config.quantization:
            llm_kwargs["quantization"] = config.quantization

        self._config = config
        self._llm = LLM(**llm_kwargs)
        self._tokenizer = self._llm.get_tokenizer()

    def reset_peak_memory(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

    def peak_gpu_mem_gb(self) -> float:
        if not torch.cuda.is_available():
            return 0.0
        return torch.cuda.max_memory_allocated() / 1e9

    def _input_token_lens(self, prompts: list[str]) -> list[int]:
        encoded = self._tokenizer(prompts, add_special_tokens=True)
        return [len(ids) for ids in encoded["input_ids"]]

    def estimate_input_tokens(self, prompts: list[str]) -> list[int]:
        return self._input_token_lens(prompts)

    def _extract_request_timings(self, request_output, batch_latency_ms: float) -> tuple[float, float, str, str]:
        metrics = getattr(request_output, "metrics", None)
        if metrics is None:
            return round(batch_latency_ms, 2), round(batch_latency_ms, 2), "batch_latency_fallback", "batch_latency_fallback"

        arrival_time = getattr(metrics, "arrival_time", None)
        first_token_time = getattr(metrics, "first_token_time", None)
        finished_time = getattr(metrics, "finished_time", None)
        last_token_time = getattr(metrics, "last_token_time", None)

        ttft_ms = None
        total_latency_ms = None
        ttft_source = "batch_latency_fallback"
        total_latency_source = "batch_latency_fallback"

        if arrival_time is not None and first_token_time is not None:
            ttft_ms = max(0.0, (first_token_time - arrival_time) * 1000)
            ttft_source = "vllm_metrics"

        end_time = finished_time if finished_time is not None else last_token_time
        if arrival_time is not None and end_time is not None:
            total_latency_ms = max(0.0, (end_time - arrival_time) * 1000)
            total_latency_source = "vllm_metrics"

        if ttft_ms is None:
            ttft_ms = batch_latency_ms
        if total_latency_ms is None:
            total_latency_ms = batch_latency_ms

        return round(ttft_ms, 2), round(total_latency_ms, 2), ttft_source, total_latency_source

    def generate_batch(
        self,
        prompts: list[str],
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        temperature: float = 0.0,
    ) -> list[dict]:
        from vllm import SamplingParams

        input_lens = self._input_token_lens(prompts)
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_new_tokens,
        )

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_start = time.perf_counter()
        outputs = self._llm.generate(prompts, sampling_params, use_tqdm=False)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t_end = time.perf_counter()

        batch_latency_ms = (t_end - t_start) * 1000
        results = []
        for prompt, input_len, request_output in zip(prompts, input_lens, outputs):
            first = request_output.outputs[0] if request_output.outputs else None
            output_text = first.text if first is not None else ""
            output_tokens = len(first.token_ids) if first is not None else 0
            ttft_ms, total_latency_ms, ttft_source, total_latency_source = self._extract_request_timings(
                request_output,
                batch_latency_ms=batch_latency_ms,
            )
            throughput_tps = 0.0
            if total_latency_ms > 0:
                throughput_tps = output_tokens / total_latency_ms * 1000
            results.append(
                {
                    "prompt": prompt,
                    "output": output_text,
                    "input_tokens": input_len,
                    "output_tokens": output_tokens,
                    "total_latency_ms": total_latency_ms,
                    "ttft_ms": ttft_ms,
                    "approx_batch_latency_ms": round(batch_latency_ms, 2),
                    "ttft_source": ttft_source,
                    "total_latency_source": total_latency_source,
                    "throughput_tps": round(throughput_tps, 2),
                }
            )
        return results

    def generate_one(
        self,
        prompt: str,
        max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
        temperature: float = 0.0,
    ) -> dict:
        return self.generate_batch(
            prompts=[prompt],
            max_new_tokens=max_new_tokens,
            temperature=temperature,
        )[0]
