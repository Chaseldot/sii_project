#!/usr/bin/env bash
# ===== User Config =====
RUN_TAG="${RUN_TAG:-122b_length_aware_v6}"
CONCURRENCY_LIST="${CONCURRENCY_LIST:-128 256 512}"
POLICY_TAG="${POLICY_TAG:-length_aware_v6}"
PROMPT_FILE="${PROMPT_FILE:-vllm_serve_exp_122b_length_aware_v6/data/mixed_prompts_30s70l.jsonl}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
RESULT_ROOT="${RESULT_ROOT:-$PWD/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_122b_length_aware_v6}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

for concurrency in $CONCURRENCY_LIST; do
  echo "[INFO] Running length-aware benchmark at concurrency=$concurrency"
  CONCURRENCY="$concurrency" \
  RUN_TAG="$RUN_TAG" \
  POLICY_TAG="$POLICY_TAG" \
  PROMPT_FILE="$PROMPT_FILE" \
  PROMPT_LIMIT="$PROMPT_LIMIT" \
  MAX_NEW_TOKENS="$MAX_NEW_TOKENS" \
  RESULT_ROOT="$RESULT_ROOT" \
  RESULT_NAMESPACE="$RESULT_NAMESPACE" \
  bash vllm_serve_exp_122b_length_aware_v6/bash/run_benchmark.sh
done
