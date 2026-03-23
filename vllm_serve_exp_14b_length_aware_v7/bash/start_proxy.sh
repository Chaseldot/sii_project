#!/usr/bin/env bash
# ===== User Config =====
# 这是 pressure-aware fair scheduler 版本。
# - POLICY: fifo / length_aware_v7
# - MAX_ACTIVE_REQUESTS: proxy 同时允许多少个请求进入后端；FIFO 和 Length-Aware 应保持一致
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - MAX_CONSECUTIVE_SHORT: 连续 short 放行上限
# - MAX_CONSECUTIVE_LONG: 连续 long 放行上限
# - ARRIVAL_WINDOW_SIZE: 近期到达窗口大小
# - TARGET_SHORT_SHARE_BONUS: 在真实 short 比例上额外给 short 的偏置
# - MIN/MAX_SHORT_SHARE: short 目标份额上下界
# - PRESSURE_EPS: 压力归一化下限
# - PRESSURE_GAIN: pressure gap 映射到份额修正的强度
# - PRESSURE_MARGIN: pressure gap 死区
# - MAX_PRESSURE_ADJUSTMENT: 单次份额最大修正量
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8087}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
POLICY="${POLICY:-length_aware_v7}"
SHORT_THRESHOLD_CHARS="${SHORT_THRESHOLD_CHARS:-256}"
MAX_CONSECUTIVE_SHORT="${MAX_CONSECUTIVE_SHORT:-4}"
MAX_CONSECUTIVE_LONG="${MAX_CONSECUTIVE_LONG:-4}"
MAX_ACTIVE_REQUESTS="${MAX_ACTIVE_REQUESTS:-64}"
MAX_QUEUE_WAIT_SEC="${MAX_QUEUE_WAIT_SEC:-300}"
ARRIVAL_WINDOW_SIZE="${ARRIVAL_WINDOW_SIZE:-256}"
CONTROL_UPDATE_INTERVAL="${CONTROL_UPDATE_INTERVAL:-64}"
TARGET_SHORT_SHARE_BONUS="${TARGET_SHORT_SHARE_BONUS:-0.1}"
MIN_SHORT_SHARE="${MIN_SHORT_SHARE:-0.35}"
MAX_SHORT_SHARE="${MAX_SHORT_SHARE:-0.65}"
PRESSURE_EPS="${PRESSURE_EPS:-0.05}"
PRESSURE_GAIN="${PRESSURE_GAIN:-0.6}"
PRESSURE_MARGIN="${PRESSURE_MARGIN:-0.15}"
MAX_PRESSURE_ADJUSTMENT="${MAX_PRESSURE_ADJUSTMENT:-0.15}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware_v7.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --policy "$POLICY" \
  --short_threshold_chars "$SHORT_THRESHOLD_CHARS" \
  --max_consecutive_short "$MAX_CONSECUTIVE_SHORT" \
  --max_consecutive_long "$MAX_CONSECUTIVE_LONG" \
  --max_active_requests "$MAX_ACTIVE_REQUESTS" \
  --max_queue_wait_sec "$MAX_QUEUE_WAIT_SEC" \
  --arrival_window_size "$ARRIVAL_WINDOW_SIZE" \
  --control_update_interval "$CONTROL_UPDATE_INTERVAL" \
  --target_short_share_bonus "$TARGET_SHORT_SHARE_BONUS" \
  --min_short_share "$MIN_SHORT_SHARE" \
  --max_short_share "$MAX_SHORT_SHARE" \
  --pressure_eps "$PRESSURE_EPS" \
  --pressure_gain "$PRESSURE_GAIN" \
  --pressure_margin "$PRESSURE_MARGIN" \
  --max_pressure_adjustment "$MAX_PRESSURE_ADJUSTMENT"
