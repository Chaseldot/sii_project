#!/usr/bin/env bash
# ===== User Config =====
RUN_TAG="${RUN_TAG:-14b_length_aware_v3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8050}"
BASE_URL="${BASE_URL:-http://$HOST:$PORT}"
SCHEDULER_STATS_URL="${SCHEDULER_STATS_URL:-$BASE_URL/scheduler_stats}"
POLICY_TAG="${POLICY_TAG:-length_aware_v3}"
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
# 默认与 baseline 共用同一个 served model name，方便复用已经启动的后端服务。
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-length-aware}"
PROMPT_FILE="${PROMPT_FILE:-vllm_serve_exp_14b_length_aware_v3/data/mixed_prompts_30s70l.jsonl}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
TEMPERATURE="${TEMPERATURE:-0.0}"
CONCURRENCY="${CONCURRENCY:-256}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
RESULT_ROOT="${RESULT_ROOT:-$PWD/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_14b_length_aware_v3}"
EXP_NAME="${EXP_NAME:-${RUN_TAG}_${POLICY_TAG}_c${CONCURRENCY}}"
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

python -m vllm_serve_exp_14b_length_aware_v3.client_benchmark \
  --base_url "$BASE_URL" \
  --scheduler_stats_url "$SCHEDULER_STATS_URL" \
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
