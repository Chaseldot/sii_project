#!/usr/bin/env bash
export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
export SERVED_MODEL_NAME=qwen2.5-14b-vllm-serve

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/model}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
DTYPE="${DTYPE:-auto}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.9}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"

vllm serve "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --dtype "$DTYPE" \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  ${ENABLE_PREFIX_CACHING:+--enable-prefix-caching}

