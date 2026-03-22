#!/usr/bin/env bash
# Quick Config:
# export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
# export PROMPT_FILE=baseline/test_prompts.jsonl
# export PROMPT_LIMIT=32
# export MAX_NEW_TOKENS=1024
# export BATCH_SIZE=1
# bash vllm_base/bash/benchmark_14b_vllm.sh
#
# 常改参数:
# - PROMPT_LIMIT: 先小样本调 batch_size / 显存
# - BATCH_SIZE: vllm_base 的批大小
export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
export CUDA_VISIBLE_DEVICES=0
export MODEL_TAG=14b_bs_default
export BATCH_SIZE="${BATCH_SIZE:-1}"

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
if [[ "${PROMPT_LIMIT:-0}" != "0" ]]; then
  LIMIT_ARGS+=(--limit "${PROMPT_LIMIT}")
fi

python -m vllm_base.benchmark \
  --model_path "$MODEL_PATH" \
  --prompt_file "${PROMPT_FILE:-baseline/test_prompts.jsonl}" \
  --output "$RESULT_DIR/results_optimized.json" \
  --batch_size "${BATCH_SIZE}" \
  --tensor_parallel_size "${TENSOR_PARALLEL_SIZE:-1}" \
  --dtype "${DTYPE:-auto}" \
  --gpu_memory_utilization "${GPU_MEMORY_UTILIZATION:-0.9}" \
  --max_new_tokens "${MAX_NEW_TOKENS:-1024}" \
  --temperature "${TEMPERATURE:-0.0}" \
  "${LIMIT_ARGS[@]}" \
  ${ENABLE_PREFIX_CACHING:+--enable_prefix_caching} \
  | tee "$RESULT_DIR/logs/benchmark.log"
