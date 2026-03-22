#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# 课程相关开关:
# - LOAD_FORMAT: 模型格式加载方式，如 auto / safetensors
# - QUANTIZATION: 量化方式，如空字符串 / int8 / awq / gptq
# - BATCH_SIZE: 离线批大小
# - MAX_NUM_SEQS: 动态 batch 可同时调度的最大序列数
# - MAX_NUM_BATCHED_TOKENS: 单次调度可容纳的总 token 上限
# - ENABLE_PREFIX_CACHING: 是否开启 Prefix Cache / KV 复用
# - MAX_MODEL_LEN: 最大上下文长度
# - SAMPLE_INTERVAL_SEC: 显存采样间隔
MODEL_PATH="${MODEL_PATH:-/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"
MODEL_TAG="${MODEL_TAG:-122b_tp4_bs1024}"
PROMPT_FILE="${PROMPT_FILE:-baseline/test_prompts.jsonl}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"          # 0 表示全量
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
TEMPERATURE="${TEMPERATURE:-0.0}"
BATCH_SIZE="${BATCH_SIZE:-1024}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-4}"
DTYPE="${DTYPE:-bfloat16}"
LOAD_FORMAT="${LOAD_FORMAT:-auto}"
QUANTIZATION="${QUANTIZATION:-}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
# MAX_NUM_SEQS="${MAX_NUM_SEQS:-12}"
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
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/vllm_122b/$MODEL_TAG}"
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

python -m vllm_122b.benchmark \
  --model_path "$MODEL_PATH" \
  --prompt_file "$PROMPT_FILE" \
  --output "$RESULT_DIR/results_optimized.json" \
  --max_new_tokens "$MAX_NEW_TOKENS" \
  --temperature "$TEMPERATURE" \
  --batch_size "$BATCH_SIZE" \
  --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
  --dtype "$DTYPE" \
  --load_format "$LOAD_FORMAT" \
  --gpu_memory_utilization "$GPU_MEMORY_UTILIZATION" \
  --max_model_len "$MAX_MODEL_LEN" \
  # --max_num_seqs "$MAX_NUM_SEQS" \
  --max_num_batched_tokens "$MAX_NUM_BATCHED_TOKENS" \
  --monitor_sample_interval_sec "$SAMPLE_INTERVAL_SEC" \
  "${LIMIT_ARGS[@]}" \
  "${PREFIX_ARGS[@]}" \
  "${QUANT_ARGS[@]}" \
  "${EAGER_ARGS[@]}" \
  | tee "$RESULT_DIR/logs/benchmark.log"
