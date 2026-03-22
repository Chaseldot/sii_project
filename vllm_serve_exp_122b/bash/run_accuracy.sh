#!/usr/bin/env bash
export RUN_TAG=122b_online
ACCURACY_CONCURRENCY=32

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8100}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3.5-122b-vllm-serve}"
ACCURACY_CONCURRENCY="${ACCURACY_CONCURRENCY:-${CONCURRENCY:-16}}"

RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_122b}"
RUN_TAG="${RUN_TAG:-122b_online}"
ACCURACY_EXP_NAME="${ACCURACY_EXP_NAME:-${RUN_TAG}_accuracy}"
ACCURACY_RUN_NAME="${ACCURACY_RUN_NAME:-${RUN_TAG}_c${ACCURACY_CONCURRENCY}}"
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/$RESULT_NAMESPACE/$ACCURACY_EXP_NAME/$ACCURACY_RUN_NAME}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "${EVAL_LIMIT:-0}" != "0" ]]; then
  LIMIT_ARGS+=(--limit "${EVAL_LIMIT}")
fi

BASELINE_ACC_ARGS=()
if [[ -n "${BASELINE_ACC:-}" ]]; then
  BASELINE_ACC_ARGS+=(--baseline_acc "${BASELINE_ACC}")
fi

python -m vllm_serve_exp_122b.evaluate_accuracy \
  --base_url "$BASE_URL" \
  --model "$SERVED_MODEL_NAME" \
  --eval_file "${EVAL_FILE:-baseline/ceval_subset.jsonl}" \
  --output "$RESULT_DIR/accuracy_online.json" \
  --concurrency "${ACCURACY_CONCURRENCY}" \
  --max_tokens "${ACCURACY_MAX_TOKENS:-16}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --sample_interval_sec "${SAMPLE_INTERVAL_SEC:-0.5}" \
  "${LIMIT_ARGS[@]}" \
  "${BASELINE_ACC_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/accuracy_online.log"
