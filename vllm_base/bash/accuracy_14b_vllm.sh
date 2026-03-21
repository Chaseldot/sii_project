#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/Qwen2.5-14B-Instruct}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
MODEL_TAG="${MODEL_TAG:-14b}"
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/vllm_base/$MODEL_TAG}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "${EVAL_LIMIT:-0}" != "0" ]]; then
  LIMIT_ARGS+=(--limit "${EVAL_LIMIT}")
fi

BASELINE_ACC_ARGS=()
if [[ -n "${BASELINE_ACC:-}" ]]; then
  BASELINE_ACC_ARGS+=(--baseline_acc "${BASELINE_ACC}")
fi

python -m vllm_base.evaluate_accuracy \
  --model_path "$MODEL_PATH" \
  --eval_file "${EVAL_FILE:-baseline/ceval_subset.jsonl}" \
  --output "$RESULT_DIR/accuracy_optimized.json" \
  --tensor_parallel_size "${TENSOR_PARALLEL_SIZE:-1}" \
  --dtype "${DTYPE:-auto}" \
  --gpu_memory_utilization "${GPU_MEMORY_UTILIZATION:-0.9}" \
  --max_new_tokens "${MAX_NEW_TOKENS:-256}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --batch_size "${BATCH_SIZE:-1}" \
  "${LIMIT_ARGS[@]}" \
  "${BASELINE_ACC_ARGS[@]}" \
  ${ENABLE_PREFIX_CACHING:+--enable_prefix_caching} \
  | tee "$RESULT_DIR/logs/accuracy.log"
