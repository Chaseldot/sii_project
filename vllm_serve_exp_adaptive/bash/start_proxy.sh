#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# 这是优化版前置调度层，不改 vLLM 内核。
# - KV_CACHE_HIGH_WATERMARK: KV 使用率超过阈值就暂缓放流
# - WAITING_HIGH_WATERMARK: 后端等待队列过大就暂缓放流
# - RUNNING_HIGH_WATERMARK: 后端执行中的请求数过大就暂缓放流
# - MAX_PROXY_INFLIGHT: 代理层允许同时放行的最大请求数
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8010}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
KV_CACHE_HIGH_WATERMARK="${KV_CACHE_HIGH_WATERMARK:-0.85}"
WAITING_HIGH_WATERMARK="${WAITING_HIGH_WATERMARK:-128}"
RUNNING_HIGH_WATERMARK="${RUNNING_HIGH_WATERMARK:-128}"
MAX_PROXY_INFLIGHT="${MAX_PROXY_INFLIGHT:-1024}"
POLL_INTERVAL_SEC="${POLL_INTERVAL_SEC:-0.05}"
MAX_GATE_WAIT_SEC="${MAX_GATE_WAIT_SEC:-300}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python -m vllm_serve_exp_adaptive.proxy \
  --host "$HOST" \
  --port "$PORT" \
  --backend_base_url "$BACKEND_BASE_URL" \
  --kv_cache_high_watermark "$KV_CACHE_HIGH_WATERMARK" \
  --waiting_high_watermark "$WAITING_HIGH_WATERMARK" \
  --running_high_watermark "$RUNNING_HIGH_WATERMARK" \
  --max_proxy_inflight "$MAX_PROXY_INFLIGHT" \
  --poll_interval_sec "$POLL_INTERVAL_SEC" \
  --max_gate_wait_sec "$MAX_GATE_WAIT_SEC"
