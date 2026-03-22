#!/usr/bin/env bash
# Quick Config:
# export RESULT_ROOT=/path/to/results
# export RESULT_NAMESPACE=vllm_serve_122b
# export RUN_TAG=122b_online
# bash vllm_serve_exp_122b/bash/summarize_results.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/results}"
RESULT_NAMESPACE="${RESULT_NAMESPACE:-vllm_serve_122b}"
RUN_TAG="${RUN_TAG:-122b_online}"
SUMMARY_OUTPUT="${SUMMARY_OUTPUT:-$RESULT_ROOT/$RESULT_NAMESPACE/${RUN_TAG}_summary.md}"
RESULTS_TABLE_OUTPUT="${RESULTS_TABLE_OUTPUT:-$RESULT_ROOT/$RESULT_NAMESPACE/${RUN_TAG}_results.md}"
BENCHMARK_CSV="${BENCHMARK_CSV:-$RESULT_ROOT/$RESULT_NAMESPACE/${RUN_TAG}_benchmark_summary.csv}"
ACCURACY_CSV="${ACCURACY_CSV:-$RESULT_ROOT/$RESULT_NAMESPACE/${RUN_TAG}_accuracy_summary.csv}"

python -m vllm_serve_exp_122b.summary \
  --result_root "$RESULT_ROOT/$RESULT_NAMESPACE" \
  --prefix "${RUN_TAG}_" \
  --output "$SUMMARY_OUTPUT" \
  --results_table_output "$RESULTS_TABLE_OUTPUT" \
  --benchmark_csv "$BENCHMARK_CSV" \
  --accuracy_csv "$ACCURACY_CSV"
