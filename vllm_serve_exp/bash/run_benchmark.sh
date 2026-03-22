#!/usr/bin/env bash
export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
export SERVED_MODEL_NAME=qwen2.5-14b-vllm-serve
export CONCURRENCY=4

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/model}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"

RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
EXP_NAME="${EXP_NAME:-14b_online_c${CONCURRENCY:-8}}"
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/vllm_serve/$EXP_NAME}"
mkdir -p "$RESULT_DIR/logs"

python -m vllm_serve_exp.client_benchmark \
  --base_url "$BASE_URL" \
  --model "$SERVED_MODEL_NAME" \
  --model_path "$MODEL_PATH" \
  --prompt_file "${PROMPT_FILE:-baseline/prompts.jsonl}" \
  --output "$RESULT_DIR/benchmark_online.json" \
  --max_tokens "${MAX_NEW_TOKENS:-256}" \
  --temperature "${TEMPERATURE:-0.0}" \
  --concurrency "${CONCURRENCY:-8}" \
  | tee "$RESULT_DIR/logs/benchmark_online.log"

