#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/Qwen2.5-14B-Instruct}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_NAME="${MODEL_NAME:-$(basename "$MODEL_PATH")}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/vllm_base/$MODEL_NAME}"
mkdir -p "$RESULT_DIR/logs"

python -m vllm_base.benchmark \
  --model_path "$MODEL_PATH" \
  --prompt_file "${PROMPT_FILE:-baseline/prompts.jsonl}" \
  --output "$RESULT_DIR/results_optimized.json" \
  --tensor_parallel_size "${TENSOR_PARALLEL_SIZE:-1}" \
  --dtype "${DTYPE:-auto}" \
  --gpu_memory_utilization "${GPU_MEMORY_UTILIZATION:-0.9}" \
  --max_new_tokens "${MAX_NEW_TOKENS:-256}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --batch_size "${BATCH_SIZE:-1}" \
  ${ENABLE_PREFIX_CACHING:+--enable_prefix_caching} \
  | tee "$RESULT_DIR/logs/benchmark.log"
