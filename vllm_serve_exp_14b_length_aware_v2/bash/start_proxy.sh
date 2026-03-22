#!/usr/bin/env bash
# ===== User Config =====
# 这是 active-dispatch 版本。
# - POLICY: fifo / length_aware_v2
# - MAX_ACTIVE_REQUESTS: proxy 同时允许多少个请求进入后端；FIFO 和 Length-Aware 应保持一致
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - SHORT_WEIGHT / LONG_WEIGHT: length_aware_v2 下的加权轮询比例
# - MAX_CONSECUTIVE_SHORT: 最多连续放行多少个 short，防止 long 饿死
# - LONG_AGING_WAIT_MS: long 在队列里等待多久后强制提升优先级
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8040}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
POLICY="${POLICY:-length_aware_v2}"
SHORT_THRESHOLD_CHARS="${SHORT_THRESHOLD_CHARS:-256}"
SHORT_WEIGHT="${SHORT_WEIGHT:-2}"
LONG_WEIGHT="${LONG_WEIGHT:-1}"
MAX_CONSECUTIVE_SHORT="${MAX_CONSECUTIVE_SHORT:-4}"
MAX_ACTIVE_REQUESTS="${MAX_ACTIVE_REQUESTS:-64}"
LONG_AGING_WAIT_MS="${LONG_AGING_WAIT_MS:-30000}"
MAX_QUEUE_WAIT_SEC="${MAX_QUEUE_WAIT_SEC:-300}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware_v2.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --policy "$POLICY" \
  --short_threshold_chars "$SHORT_THRESHOLD_CHARS" \
  --short_weight "$SHORT_WEIGHT" \
  --long_weight "$LONG_WEIGHT" \
  --max_consecutive_short "$MAX_CONSECUTIVE_SHORT" \
  --max_active_requests "$MAX_ACTIVE_REQUESTS" \
  --long_aging_wait_ms "$LONG_AGING_WAIT_MS" \
  --max_queue_wait_sec "$MAX_QUEUE_WAIT_SEC"
