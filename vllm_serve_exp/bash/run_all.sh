#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[INFO] BASE_URL=${BASE_URL:-http://${HOST:-127.0.0.1}:${PORT:-8000}}"
echo "[INFO] SERVED_MODEL_NAME=${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"
echo "[INFO] CONCURRENCY=${CONCURRENCY:-8}"
echo "[INFO] EVAL_LIMIT=${EVAL_LIMIT:-0}"

bash vllm_serve_exp/bash/run_benchmark.sh
bash vllm_serve_exp/bash/run_accuracy.sh

echo "[INFO] vLLM serve 在线实验完成"
