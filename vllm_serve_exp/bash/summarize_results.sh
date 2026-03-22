#!/usr/bin/env bash
# Quick Config:
# export RESULT_ROOT=/path/to/results
# export RUN_TAG=14b_online
# bash vllm_serve_exp/bash/summarize_results.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
RUN_TAG="${RUN_TAG:-14b_online}"
SUMMARY_OUTPUT="${SUMMARY_OUTPUT:-$RESULT_ROOT/vllm_serve/${RUN_TAG}_summary.md}"
RESULTS_TABLE_OUTPUT="${RESULTS_TABLE_OUTPUT:-$RESULT_ROOT/vllm_serve/${RUN_TAG}_results.md}"
BENCHMARK_CSV="${BENCHMARK_CSV:-$RESULT_ROOT/vllm_serve/${RUN_TAG}_benchmark_summary.csv}"
ACCURACY_CSV="${ACCURACY_CSV:-$RESULT_ROOT/vllm_serve/${RUN_TAG}_accuracy_summary.csv}"

python -m vllm_serve_exp.summary \
  --result_root "$RESULT_ROOT/vllm_serve" \
  --prefix "${RUN_TAG}_" \
  --output "$SUMMARY_OUTPUT" \
  --results_table_output "$RESULTS_TABLE_OUTPUT" \
  --benchmark_csv "$BENCHMARK_CSV" \
  --accuracy_csv "$ACCURACY_CSV"
