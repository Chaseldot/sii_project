#!/usr/bin/env bash
# ===== User Config =====
# 这是纯双队列版本，不做额外 inflight 限制。
# - SHORT_THRESHOLD_CHARS: 长短请求分界线
# - SHORT_WEIGHT / LONG_WEIGHT: 加权轮询比例
# - MAX_CONSECUTIVE_SHORT: 最多连续放行多少个 short，防止 long 饿死
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8030}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8020}"
SHORT_THRESHOLD_CHARS="${SHORT_THRESHOLD_CHARS:-256}"
SHORT_WEIGHT="${SHORT_WEIGHT:-3}"
LONG_WEIGHT="${LONG_WEIGHT:-1}"
MAX_CONSECUTIVE_SHORT="${MAX_CONSECUTIVE_SHORT:-6}"
MAX_QUEUE_WAIT_SEC="${MAX_QUEUE_WAIT_SEC:-300}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_14b_length_aware.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --short_threshold_chars "$SHORT_THRESHOLD_CHARS" \
  --short_weight "$SHORT_WEIGHT" \
  --long_weight "$LONG_WEIGHT" \
  --max_consecutive_short "$MAX_CONSECUTIVE_SHORT" \
  --max_queue_wait_sec "$MAX_QUEUE_WAIT_SEC"
