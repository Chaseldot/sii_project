#!/usr/bin/env bash
# ===== User Config =====
# 这是自适应 active-dispatch 版本。
# - POLICY: fifo / length_aware_v3
# - MAX_ACTIVE_REQUESTS: proxy 同时允许多少个请求进入后端；FIFO 和 Length-Aware 应保持一致
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - SHORT_WEIGHT / LONG_WEIGHT: 自适应策略的初始权重
# - MAX_CONSECUTIVE_SHORT: 自适应策略的初始连续 short 上限
# - ADAPT_WINDOW_SIZE / ADAPT_UPDATE_INTERVAL: 近期统计窗口与更新周期
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8050}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
POLICY="${POLICY:-length_aware_v3}"
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
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware_v3.proxy \
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
  --max_max_consecutive_short "$MAX_MAX_CONSECUTIVE_SHORT"
