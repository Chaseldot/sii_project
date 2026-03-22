#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# 课程相关开关:
# - LOAD_FORMAT: 模型格式加载方式，如 auto / safetensors
# - QUANTIZATION: 量化方式，如空字符串 / int8 / awq / gptq
# - BATCH_SIZE: 离线评测批大小
# - MAX_NUM_SEQS: 动态 batch 可同时调度的最大序列数
# - MAX_NUM_BATCHED_TOKENS: 单次调度可容纳的总 token 上限
# - ENABLE_PREFIX_CACHING: 是否开启 Prefix Cache / KV 复用
# - MAX_MODEL_LEN: 最大上下文长度
# - SAMPLE_INTERVAL_SEC: 显存采样间隔
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_TAG="${MODEL_TAG:-14b_accuracy_bs1}"
EVAL_FILE="${EVAL_FILE:-baseline/ceval_subset.jsonl}"
EVAL_LIMIT="${EVAL_LIMIT:-0}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-16}"
TEMPERATURE="${TEMPERATURE:-0.0}"
BATCH_SIZE="${BATCH_SIZE:-1}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
DTYPE="${DTYPE:-bfloat16}"
LOAD_FORMAT="${LOAD_FORMAT:-auto}"
QUANTIZATION="${QUANTIZATION:-}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-12}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"
ENFORCE_EAGER="${ENFORCE_EAGER:-0}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
BASELINE_ACC="${BASELINE_ACC:-}"
RESULT_ROOT="${RESULT_ROOT:-}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "$RESULT_ROOT" ]]; then
  RESULT_ROOT="$ROOT_DIR/results"
fi

export CUDA_VISIBLE_DEVICES
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/vllm_14b/$MODEL_TAG}"
mkdir -p "$RESULT_DIR/logs"

LIMIT_ARGS=()
if [[ "$EVAL_LIMIT" != "0" ]]; then
  LIMIT_ARGS+=(--limit "$EVAL_LIMIT")
fi
BASELINE_ACC_ARGS=()
if [[ -n "$BASELINE_ACC" ]]; then
  BASELINE_ACC_ARGS+=(--baseline_acc "$BASELINE_ACC")
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

python -m vllm_14b.evaluate_accuracy \
  --model_path "$MODEL_PATH" \
  --eval_file "$EVAL_FILE" \
  --output "$RESULT_DIR/accuracy_optimized.json" \
  --max_new_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --batch_size "$BATCH_SIZE" \
  --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
  --dtype "$DTYPE" \
  --load_format "$LOAD_FORMAT" \
  --gpu_memory_utilization "$GPU_MEMORY_UTILIZATION" \
  --max_model_len "$MAX_MODEL_LEN" \
  --max_num_seqs "$MAX_NUM_SEQS" \
  --max_num_batched_tokens "$MAX_NUM_BATCHED_TOKENS" \
  --monitor_sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  "${LIMIT_ARGS[@]}" \
  "${BASELINE_ACC_ARGS[@]}" \
  "${PREFIX_ARGS[@]}" \
  "${QUANT_ARGS[@]}" \
  "${EAGER_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/accuracy.log"
