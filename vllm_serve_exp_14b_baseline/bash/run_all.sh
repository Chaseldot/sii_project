#!/usr/bin/env bash
# ===== User Config =====
RUN_TAG="${RUN_TAG:-14b_baseline}"
CONCURRENCY_LIST="${CONCURRENCY_LIST:-64 128 256 512 1024}"
# baseline 默认先跑混合数据，后续可以直接改这里切换数据集。
PROMPT_FILE="${PROMPT_FILE:-vllm_serve_exp_14b_baseline/data/mixed_prompts_30s70l.jsonl}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
RESULT_ROOT="${RESULT_ROOT:-$PWD/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_14b_baseline}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

for concurrency in $CONCURRENCY_LIST; do
  echo "[INFO] Running benchmark at concurrency=$concurrency"
  CONCURRENCY="$concurrency" \
  RUN_TAG="$RUN_TAG" \
  PROMPT_FILE="$PROMPT_FILE" \
  PROMPT_LIMIT="$PROMPT_LIMIT" \
  MAX_NEW_TOKENS="$MAX_NEW_TOKENS" \
  RESULT_ROOT="$RESULT_ROOT" \
  RESULT_NAMESPACE="$RESULT_NAMESPACE" \
  bash vllm_serve_exp_14b_baseline/bash/run_benchmark.sh
done
