#!/usr/bin/env bash
# ===== User Config =====
RUN_TAG="${RUN_TAG:-14b_adaptive}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8010}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"
PROMPT_FILE="${PROMPT_FILE:-baseline/test_prompts.jsonl}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
TEMPERATURE="${TEMPERATURE:-0.0}"
CONCURRENCY="${CONCURRENCY:-1024}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_adaptive}"
EXP_NAME="${EXP_NAME:-${RUN_TAG}_c${CONCURRENCY}}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/$RESULT_NAMESPACE/$EXP_NAME}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "$PROMPT_LIMIT" != "0" ]]; then
  LIMIT_ARGS+=(--limit "$PROMPT_LIMIT")
fi

python -m vllm_serve_exp.client_benchmark \
  --base_url "$BASE_URL" \
  --model "$SERVED_MODEL_NAME" \
  --model_path "$MODEL_PATH" \
  --prompt_file "$PROMPT_FILE" \
  --output "$RESULT_DIR/benchmark_online.json" \
  --max_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --concurrency "$CONCURRENCY" \
  --sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  "${LIMIT_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/benchmark_online.log"

python -m vllm_serve_exp_adaptive.stats_client \
  --base_url "$BASE_URL" \
  --output "$RESULT_DIR/scheduler_stats.json" \
  > "$RESULT_DIR/logs/scheduler_stats.log"
