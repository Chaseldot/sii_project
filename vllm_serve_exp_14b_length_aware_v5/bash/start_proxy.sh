#!/usr/bin/env bash
# ===== User Config =====
# 这是 queue-aware constrained fair scheduler 版本。
# - POLICY: fifo / length_aware_v5
# - MAX_ACTIVE_REQUESTS: proxy 同时允许多少个请求进入后端；FIFO 和 Length-Aware 应保持一致
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - MAX_CONSECUTIVE_SHORT: 连续 short 放行上限
# - ARRIVAL_WINDOW_SIZE: 近期到达窗口大小
# - TARGET_SHORT_SHARE_BONUS: 在真实 short 比例上额外给 short 的偏置
# - MIN/MAX_SHORT_SHARE: short 目标份额上下界
# - LONG_HEAD_WAIT_GUARD_MS / LONG_QUEUE_LEN_GUARD: long 队列保护阈值
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8070}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
POLICY="${POLICY:-length_aware_v5}"
SHORT_THRESHOLD_CHARS="${SHORT_THRESHOLD_CHARS:-256}"
MAX_CONSECUTIVE_SHORT="${MAX_CONSECUTIVE_SHORT:-4}"
MAX_ACTIVE_REQUESTS="${MAX_ACTIVE_REQUESTS:-64}"
MAX_QUEUE_WAIT_SEC="${MAX_QUEUE_WAIT_SEC:-300}"
ARRIVAL_WINDOW_SIZE="${ARRIVAL_WINDOW_SIZE:-256}"
CONTROL_UPDATE_INTERVAL="${CONTROL_UPDATE_INTERVAL:-64}"
TARGET_SHORT_SHARE_BONUS="${TARGET_SHORT_SHARE_BONUS:-0.2}"
MIN_SHORT_SHARE="${MIN_SHORT_SHARE:-0.5}"
MAX_SHORT_SHARE="${MAX_SHORT_SHARE:-0.75}"
LONG_HEAD_WAIT_GUARD_MS="${LONG_HEAD_WAIT_GUARD_MS:-45000}"
LONG_QUEUE_LEN_GUARD="${LONG_QUEUE_LEN_GUARD:-96}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware_v5.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --policy "$POLICY" \
  --short_threshold_chars "$SHORT_THRESHOLD_CHARS" \
  --max_consecutive_short "$MAX_CONSECUTIVE_SHORT" \
  --max_active_requests "$MAX_ACTIVE_REQUESTS" \
  --max_queue_wait_sec "$MAX_QUEUE_WAIT_SEC" \
  --arrival_window_size "$ARRIVAL_WINDOW_SIZE" \
  --control_update_interval "$CONTROL_UPDATE_INTERVAL" \
  --target_short_share_bonus "$TARGET_SHORT_SHARE_BONUS" \
  --min_short_share "$MIN_SHORT_SHARE" \
  --max_short_share "$MAX_SHORT_SHARE" \
  --long_head_wait_guard_ms "$LONG_HEAD_WAIT_GUARD_MS" \
  --long_queue_len_guard "$LONG_QUEUE_LEN_GUARD"
