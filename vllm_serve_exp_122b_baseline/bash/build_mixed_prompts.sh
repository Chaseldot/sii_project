#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# 默认生成 512 条混合数据；short 不够时会自动重复采样。
SHORT_FILE="${SHORT_FILE:-baseline/prompts.jsonl}"
LONG_FILE="${LONG_FILE:-baseline/test_prompts.jsonl}"
OUTPUT="${OUTPUT:-vllm_serve_exp_122b_baseline/data/mixed_prompts_30s70l.jsonl}"
MODE="${MODE:-fixed_total}"                # preserve_short / fixed_total
SHORT_RATIO="${SHORT_RATIO:-0.3}"
TOTAL_SAMPLES="${TOTAL_SAMPLES:-512}"      # 仅 fixed_total 模式使用
SHUFFLE="${SHUFFLE:-1}"
SEED="${SEED:-42}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

SHUFFLE_ARGS=()
if [[ "$SHUFFLE" == "1" ]]; then
  SHUFFLE_ARGS+=(--shuffle)
fi

python3 -m vllm_serve_exp_122b_baseline.build_mixed_prompts \
  --short_file "$SHORT_FILE" \
  --long_file "$LONG_FILE" \
  --output "$OUTPUT" \
  --mode "$MODE" \
  --short_ratio "$SHORT_RATIO" \
  --total_samples "$TOTAL_SAMPLES" \
  --seed "$SEED" \
  "${SHUFFLE_ARGS[@]}"
