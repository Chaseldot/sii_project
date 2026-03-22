#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
RUN_TAG="${RUN_TAG:-14b_online}"
CONCURRENCY_LIST="${CONCURRENCY_LIST:-1 2 4 8 16 32 64 99}"
ACCURACY_EXP_NAME="${ACCURACY_EXP_NAME:-${RUN_TAG}_accuracy}"
SUMMARY_OUTPUT="${SUMMARY_OUTPUT:-$RESULT_ROOT/vllm_serve/${RUN_TAG}_summary.md}"

echo "[INFO] BASE_URL=${BASE_URL:-http://${HOST:-127.0.0.1}:${PORT:-8000}}"
echo "[INFO] SERVED_MODEL_NAME=${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"
echo "[INFO] CONCURRENCY_LIST=${CONCURRENCY_LIST}"
echo "[INFO] EVAL_LIMIT=${EVAL_LIMIT:-0}"
echo "[INFO] RUN_TAG=${RUN_TAG}"

for CONCURRENCY in ${CONCURRENCY_LIST}; do
  export CONCURRENCY
  export EXP_NAME="${RUN_TAG}_c${CONCURRENCY}"
  echo "[INFO] 运行在线 benchmark: EXP_NAME=${EXP_NAME}"
  bash vllm_serve_exp/bash/run_benchmark.sh
done

export EXP_NAME="${ACCURACY_EXP_NAME}"
echo "[INFO] 运行在线 accuracy: EXP_NAME=${EXP_NAME}"
bash vllm_serve_exp/bash/run_accuracy.sh

bash vllm_serve_exp/bash/summarize_results.sh

echo "[INFO] vLLM serve 在线实验完成，汇总已写入 ${SUMMARY_OUTPUT}"
