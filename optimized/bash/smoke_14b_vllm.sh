#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/Qwen2.5-14B-Instruct}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_NAME="${MODEL_NAME:-$(basename "$MODEL_PATH")}"
RESULT_DIR="${RESULT_DIR:-$ROOT_DIR/results/optimized/$MODEL_NAME}"
mkdir -p "$RESULT_DIR/logs"

python -m optimized.inference \
  --model_path "$MODEL_PATH" \
  --tensor_parallel_size "${TENSOR_PARALLEL_SIZE:-1}" \
  --dtype "${DTYPE:-auto}" \
  --gpu_memory_utilization "${GPU_MEMORY_UTILIZATION:-0.9}" \
  --max_new_tokens "${MAX_NEW_TOKENS:-256}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --output "$RESULT_DIR/inference_result.json" \
  | tee "$RESULT_DIR/logs/inference.log"

