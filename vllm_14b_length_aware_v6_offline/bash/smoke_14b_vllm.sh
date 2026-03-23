#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_TAG="${MODEL_TAG:-14b_length_aware_v6_offline_smoke}"
PROMPT="${PROMPT:-请系统说明离线批量推理中，长度感知 batch 规划为什么会影响吞吐、尾延迟和显存利用。}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-256}"
TEMPERATURE="${TEMPERATURE:-0.0}"
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
RESULT_ROOT="${RESULT_ROOT:-}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "$RESULT_ROOT" ]]; then
  RESULT_ROOT="$ROOT_DIR/results"
fi

export CUDA_VISIBLE_DEVICES
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/vllm_14b_length_aware_v6_offline/$MODEL_TAG}"
mkdir -p "$RESULT_DIR/logs"

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

python -m vllm_14b_length_aware_v6_offline.inference \
  --model_path "$MODEL_PATH" \
  --prompt "$PROMPT" \
  --max_new_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
  --dtype "$DTYPE" \
  --load_format "$LOAD_FORMAT" \
  --gpu_memory_utilization "$GPU_MEMORY_UTILIZATION" \
  --max_model_len "$MAX_MODEL_LEN" \
  --max_num_seqs "$MAX_NUM_SEQS" \
  --max_num_batched_tokens "$MAX_NUM_BATCHED_TOKENS" \
  --monitor_sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  "${PREFIX_ARGS[@]}" \
  "${QUANT_ARGS[@]}" \
  "${EAGER_ARGS[@]}" \
  --output "$RESULT_DIR/inference_result.json" \
  | tee "$RESULT_DIR/logs/inference.log"
