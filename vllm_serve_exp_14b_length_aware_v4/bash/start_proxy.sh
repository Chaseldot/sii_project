#!/usr/bin/env bash
# ===== User Config =====
# 这是显式约束优化版本。
# - POLICY: fifo / length_aware_v4
# - MAX_ACTIVE_REQUESTS: proxy 同时允许多少个请求进入后端；FIFO 和 Length-Aware 应保持一致
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - SHORT_WEIGHT / LONG_WEIGHT: 初始权重
# - MAX_CONSECUTIVE_SHORT: 初始连续 short 上限
# - OBJECTIVE_SHORT_P95_TTFT_MS: short p95 TTFT 目标值
# - CONSTRAINT_MAX_LONG_P95_LATENCY_MS: long p95 latency 硬约束
# - CONSTRAINT_MAX_OVERALL_P95_LATENCY_MS: overall p95 latency 硬约束
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8060}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
POLICY="${POLICY:-length_aware_v4}"
SHORT_THRESHOLD_CHARS="${SHORT_THRESHOLD_CHARS:-256}"
SHORT_WEIGHT="${SHORT_WEIGHT:-2}"
LONG_WEIGHT="${LONG_WEIGHT:-1}"
MAX_CONSECUTIVE_SHORT="${MAX_CONSECUTIVE_SHORT:-4}"
MAX_ACTIVE_REQUESTS="${MAX_ACTIVE_REQUESTS:-64}"
MAX_QUEUE_WAIT_SEC="${MAX_QUEUE_WAIT_SEC:-300}"
ADAPT_WINDOW_SIZE="${ADAPT_WINDOW_SIZE:-128}"
ADAPT_UPDATE_INTERVAL="${ADAPT_UPDATE_INTERVAL:-64}"
MIN_SHORT_WEIGHT="${MIN_SHORT_WEIGHT:-1}"
MAX_SHORT_WEIGHT="${MAX_SHORT_WEIGHT:-3}"
MIN_MAX_CONSECUTIVE_SHORT="${MIN_MAX_CONSECUTIVE_SHORT:-2}"
MAX_MAX_CONSECUTIVE_SHORT="${MAX_MAX_CONSECUTIVE_SHORT:-6}"
OBJECTIVE_SHORT_P95_TTFT_MS="${OBJECTIVE_SHORT_P95_TTFT_MS:-45000}"
CONSTRAINT_MAX_LONG_P95_LATENCY_MS="${CONSTRAINT_MAX_LONG_P95_LATENCY_MS:-110000}"
CONSTRAINT_MAX_OVERALL_P95_LATENCY_MS="${CONSTRAINT_MAX_OVERALL_P95_LATENCY_MS:-110000}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware_v4.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --policy "$POLICY" \
  --short_threshold_chars "$SHORT_THRESHOLD_CHARS" \
  --short_weight "$SHORT_WEIGHT" \
  --long_weight "$LONG_WEIGHT" \
  --max_consecutive_short "$MAX_CONSECUTIVE_SHORT" \
  --max_active_requests "$MAX_ACTIVE_REQUESTS" \
  --max_queue_wait_sec "$MAX_QUEUE_WAIT_SEC" \
  --adapt_window_size "$ADAPT_WINDOW_SIZE" \
  --adapt_update_interval "$ADAPT_UPDATE_INTERVAL" \
  --min_short_weight "$MIN_SHORT_WEIGHT" \
  --max_short_weight "$MAX_SHORT_WEIGHT" \
  --min_max_consecutive_short "$MIN_MAX_CONSECUTIVE_SHORT" \
  --max_max_consecutive_short "$MAX_MAX_CONSECUTIVE_SHORT" \
  --objective_short_p95_ttft_ms "$OBJECTIVE_SHORT_P95_TTFT_MS" \
  --constraint_max_long_p95_latency_ms "$CONSTRAINT_MAX_LONG_P95_LATENCY_MS" \
  --constraint_max_overall_p95_latency_ms "$CONSTRAINT_MAX_OVERALL_P95_LATENCY_MS"
