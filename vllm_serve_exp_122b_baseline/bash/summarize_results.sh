#!/usr/bin/env bash
# ===== User Config =====
RESULT_ROOT="${RESULT_ROOT:-$PWD/results/vllm_serve_122b_baseline}"
PREFIX="${PREFIX:-}"
OUTPUT="${OUTPUT:-}"
RESULTS_TABLE_OUTPUT="${RESULTS_TABLE_OUTPUT:-}"
BENCHMARK_CSV="${BENCHMARK_CSV:-}"
ACCURACY_CSV="${ACCURACY_CSV:-}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

ARGS=(
  --result_root "$RESULT_ROOT"
  --prefix "$PREFIX"
)

if [[ -n "$OUTPUT" ]]; then
  ARGS+=(--output "$OUTPUT")
fi
if [[ -n "$RESULTS_TABLE_OUTPUT" ]]; then
  ARGS+=(--results_table_output "$RESULTS_TABLE_OUTPUT")
fi
if [[ -n "$BENCHMARK_CSV" ]]; then
  ARGS+=(--benchmark_csv "$BENCHMARK_CSV")
fi
if [[ -n "$ACCURACY_CSV" ]]; then
  ARGS+=(--accuracy_csv "$ACCURACY_CSV")
fi

python -m vllm_serve_exp_122b_baseline.summary "${ARGS[@]}"
