#!/usr/bin/env bash
export RUN_TAG=122b_online
CONCURRENCY=1

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8100}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
MODEL_PATH="${MODEL_PATH:-/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen3.5-122b-vllm-serve}"
CONCURRENCY="${CONCURRENCY:-8}"

RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_122b}"
RUN_TAG="${RUN_TAG:-122b_online}"
EXP_NAME="${EXP_NAME:-${RUN_TAG}_c${CONCURRENCY}}"
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/$RESULT_NAMESPACE/$EXP_NAME}"
mkdir -p "$RESULT_DIR/logs"

python -m vllm_serve_exp_122b.client_benchmark \
  --base_url "$BASE_URL" \
  --model "$SERVED_MODEL_NAME" \
  --model_path "$MODEL_PATH" \
  --prompt_file "${PROMPT_FILE:-baseline/prompts.jsonl}" \
  --output "$RESULT_DIR/benchmark_online.json" \
  --max_tokens "${MAX_NEW_TOKENS:-1024}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --concurrency "${CONCURRENCY}" \
  --sample_interval_sec "${SAMPLE_INTERVAL_SEC:-0.5}" \
  | tee "$RESULT_DIR/logs/benchmark_online.log"
