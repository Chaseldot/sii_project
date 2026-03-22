#!/usr/bin/env bash
# ===== User Config =====
RUN_TAG="${RUN_TAG:-122b_adaptive_accuracy}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8110}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3.5-122b-vllm-serve}"
EVAL_FILE="${EVAL_FILE:-baseline/ceval_subset.jsonl}"
EVAL_LIMIT="${EVAL_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-16}"
TEMPERATURE="${TEMPERATURE:-0.0}"
CONCURRENCY="${CONCURRENCY:-128}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
BASELINE_ACC="${BASELINE_ACC:-}"
RESULT_ROOT="${RESULT_ROOT:-}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_adaptive_122b}"
EXP_NAME="${EXP_NAME:-${RUN_TAG}_c${CONCURRENCY}}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "$RESULT_ROOT" ]]; then
  RESULT_ROOT="$ROOT_DIR/results"
fi

RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/$RESULT_NAMESPACE/$EXP_NAME}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "$EVAL_LIMIT" != "0" ]]; then
  LIMIT_ARGS+=(--limit "$EVAL_LIMIT")
fi
BASELINE_ARGS=()
if [[ -n "$BASELINE_ACC" ]]; then
  BASELINE_ARGS+=(--baseline_acc "$BASELINE_ACC")
fi

python -m vllm_serve_exp_122b.evaluate_accuracy \
  --base_url "$BASE_URL" \
  --model "$SERVED_MODEL_NAME" \
  --eval_file "$EVAL_FILE" \
  --output "$RESULT_DIR/accuracy_online.json" \
  --max_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --concurrency "$CONCURRENCY" \
  --sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  "${LIMIT_ARGS[@]}" \
  "${BASELINE_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/accuracy_online.log"

python -m vllm_serve_exp_adaptive.stats_client \
  --base_url "$BASE_URL" \
  --output "$RESULT_DIR/scheduler_stats.json" \
  > "$RESULT_DIR/logs/scheduler_stats.log"
