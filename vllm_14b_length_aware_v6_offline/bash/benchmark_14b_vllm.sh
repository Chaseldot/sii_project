#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# CUDA_VISIBLE_DEVICES=0 BATCH_SIZE=32 MODEL_TAG=bs32 bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh &
# CUDA_VISIBLE_DEVICES=1 BATCH_SIZE=64 MODEL_TAG=bs64 bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh &
# CUDA_VISIBLE_DEVICES=2 BATCH_SIZE=128 MODEL_TAG=bs128 bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh &
# CUDA_VISIBLE_DEVICES=3 BATCH_SIZE=256 MODEL_TAG=bs256 bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh &

# CUDA_VISIBLE_DEVICES=0 BATCH_SIZE=1024 MODEL_TAG=bs1024 bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh &


MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_TAG="${MODEL_TAG:-14b_length_aware_v6_offline_bs8}"
PROMPT_FILE="${PROMPT_FILE:-}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
TEMPERATURE="${TEMPERATURE:-0.0}"
BATCH_SIZE="${BATCH_SIZE:-128}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
DTYPE="${DTYPE:-bfloat16}"
LOAD_FORMAT="${LOAD_FORMAT:-auto}"
QUANTIZATION="${QUANTIZATION:-}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"
ENFORCE_EAGER="${ENFORCE_EAGER:-0}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
PLANNER_POLICY="${PLANNER_POLICY:-length_aware_v6}"
PLANNER_LOOKAHEAD_SIZE="${PLANNER_LOOKAHEAD_SIZE:-64}"
PLANNER_SHORT_THRESHOLD_TOKENS="${PLANNER_SHORT_THRESHOLD_TOKENS:-256}"
PLANNER_MAX_CONSECUTIVE_SHORT="${PLANNER_MAX_CONSECUTIVE_SHORT:-4}"
PLANNER_ARRIVAL_WINDOW_SIZE="${PLANNER_ARRIVAL_WINDOW_SIZE:-256}"
PLANNER_CONTROL_UPDATE_INTERVAL="${PLANNER_CONTROL_UPDATE_INTERVAL:-64}"
PLANNER_TARGET_SHORT_SHARE_BONUS="${PLANNER_TARGET_SHORT_SHARE_BONUS:-0.2}"
PLANNER_MIN_SHORT_SHARE="${PLANNER_MIN_SHORT_SHARE:-0.5}"
PLANNER_MAX_SHORT_SHARE="${PLANNER_MAX_SHORT_SHARE:-0.75}"
PLANNER_QUEUE_RATIO_CONTROL_GAIN="${PLANNER_QUEUE_RATIO_CONTROL_GAIN:-1.0}"
PLANNER_QUEUE_RATIO_MARGIN="${PLANNER_QUEUE_RATIO_MARGIN:-0.08}"
PLANNER_MAX_RATIO_ADJUSTMENT="${PLANNER_MAX_RATIO_ADJUSTMENT:-0.2}"
SORT_WITHIN_BATCH="${SORT_WITHIN_BATCH:-1}"
RESULT_ROOT="${RESULT_ROOT:-}"
# ===== End User Config =====
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(dirname "$PACKAGE_DIR")"
cd "$WORK_DIR"

if [[ -z "$RESULT_ROOT" ]]; then
  RESULT_ROOT="$PACKAGE_DIR/results"
fi

if [[ -z "$PROMPT_FILE" ]]; then
  PROMPT_FILE="$PACKAGE_DIR/data/test_prompts.jsonl"
fi

export CUDA_VISIBLE_DEVICES
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/$MODEL_TAG}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "$PROMPT_LIMIT" != "0" ]]; then
  LIMIT_ARGS+=(--limit "$PROMPT_LIMIT")
fi
PREFIX_ARGS=()
if [[ "$ENABLE_PREFIX_CACHING" == "1" ]]; then
  PREFIX_ARGS+=(--enable_prefix_caching)
fi
QUANT_ARGS=()
if [[ -n "$QUANTIZATION" ]]; then
  QUANT_ARGS+=(--quantization "$QUANTIZATION")
fi
EAGER_ARGS=()
if [[ "$ENFORCE_EAGER" == "1" ]]; then
  EAGER_ARGS+=(--enforce_eager)
fi
SEQ_ARGS=()
if [[ -n "$MAX_NUM_SEQS" ]]; then
  SEQ_ARGS+=(--max_num_seqs "$MAX_NUM_SEQS")
fi
SORT_ARGS=()
if [[ "$SORT_WITHIN_BATCH" != "1" ]]; then
  SORT_ARGS+=(--disable_sort_within_batch)
fi

python -m vllm_14b_length_aware_v6_offline.benchmark \
  --model_path "$MODEL_PATH" \
  --prompt_file "$PROMPT_FILE" \
  --output "$RESULT_DIR/results_length_aware_v6_offline.json" \
  --max_new_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --batch_size "$BATCH_SIZE" \
  --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
  --dtype "$DTYPE" \
  --load_format "$LOAD_FORMAT" \
  --gpu_memory_utilization "$GPU_MEMORY_UTILIZATION" \
  --max_model_len "$MAX_MODEL_LEN" \
  --max_num_batched_tokens "$MAX_NUM_BATCHED_TOKENS" \
  --monitor_sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  --planner_policy "$PLANNER_POLICY" \
  --planner_lookahead_size "$PLANNER_LOOKAHEAD_SIZE" \
  --planner_short_threshold_tokens "$PLANNER_SHORT_THRESHOLD_TOKENS" \
  --planner_max_consecutive_short "$PLANNER_MAX_CONSECUTIVE_SHORT" \
  --planner_arrival_window_size "$PLANNER_ARRIVAL_WINDOW_SIZE" \
  --planner_control_update_interval "$PLANNER_CONTROL_UPDATE_INTERVAL" \
  --planner_target_short_share_bonus "$PLANNER_TARGET_SHORT_SHARE_BONUS" \
  --planner_min_short_share "$PLANNER_MIN_SHORT_SHARE" \
  --planner_max_short_share "$PLANNER_MAX_SHORT_SHARE" \
  --planner_queue_ratio_control_gain "$PLANNER_QUEUE_RATIO_CONTROL_GAIN" \
  --planner_queue_ratio_margin "$PLANNER_QUEUE_RATIO_MARGIN" \
  --planner_max_ratio_adjustment "$PLANNER_MAX_RATIO_ADJUSTMENT" \
  "${LIMIT_ARGS[@]}" \
  "${PREFIX_ARGS[@]}" \
  "${QUANT_ARGS[@]}" \
  "${EAGER_ARGS[@]}" \
  "${SEQ_ARGS[@]}" \
  "${SORT_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/benchmark.log"
