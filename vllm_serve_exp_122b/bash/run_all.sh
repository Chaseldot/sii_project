#!/usr/bin/env bash
export RUN_TAG=122b_online
export CONCURRENCY_LIST="1 2 4 8 12 16"
export ACCURACY_CONCURRENCY="${ACCURACY_CONCURRENCY:-16}"

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_122b}"
RUN_TAG="${RUN_TAG:-122b_online}"
CONCURRENCY_LIST="${CONCURRENCY_LIST:-1 2 4 8 12 16}"
ACCURACY_EXP_NAME="${ACCURACY_EXP_NAME:-${RUN_TAG}_accuracy}"
SUMMARY_OUTPUT="${SUMMARY_OUTPUT:-$RESULT_ROOT/$RESULT_NAMESPACE/${RUN_TAG}_summary.md}"

echo "[INFO] BASE_URL=${BASE_URL:-http://${HOST:-127.0.0.1}:${PORT:-8100}}"
echo "[INFO] SERVED_MODEL_NAME=${SERVED_MODEL_NAME:-qwen3.5-122b-vllm-serve}"
echo "[INFO] RESULT_NAMESPACE=${RESULT_NAMESPACE}"
echo "[INFO] CONCURRENCY_LIST=${CONCURRENCY_LIST}"
echo "[INFO] ACCURACY_CONCURRENCY=${ACCURACY_CONCURRENCY}"
echo "[INFO] RUN_TAG=${RUN_TAG}"

for CONCURRENCY in ${CONCURRENCY_LIST}; do
  export CONCURRENCY
  export EXP_NAME="${RUN_TAG}_c${CONCURRENCY}"
  echo "[INFO] 运行 122B 在线 benchmark: EXP_NAME=${EXP_NAME}"
  bash vllm_serve_exp_122b/bash/run_benchmark.sh
done

export ACCURACY_EXP_NAME
echo "[INFO] 运行 122B 在线 accuracy: ACCURACY_EXP_NAME=${ACCURACY_EXP_NAME}"
bash vllm_serve_exp_122b/bash/run_accuracy.sh

bash vllm_serve_exp_122b/bash/summarize_results.sh

echo "[INFO] 122B vLLM serve 在线实验完成，汇总已写入 ${SUMMARY_OUTPUT}"
