#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
# 这个脚本会顺序跑 smoke / benchmark / accuracy。
# - MAX_NUM_SEQS 和 MAX_NUM_BATCHED_TOKENS 控制动态 batch
# - ENABLE_PREFIX_CACHING 控制 Prefix Cache / KV 复用
# - MAX_MODEL_LEN 控制上下文长度
MODEL_PATH="${MODEL_PATH:-/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"
MODEL_TAG="${MODEL_TAG:-122b_tp4_bs1}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
EVAL_LIMIT="${EVAL_LIMIT:-0}"
BATCH_SIZE="${BATCH_SIZE:-1}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-12}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"
RESULT_ROOT="${RESULT_ROOT:-}"
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[INFO] ROOT_DIR=$ROOT_DIR"
echo "[INFO] MODEL_PATH=$MODEL_PATH"
echo "[INFO] CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
echo "[INFO] MODEL_TAG=$MODEL_TAG"
echo "[INFO] BATCH_SIZE=$BATCH_SIZE"
echo "[INFO] PROMPT_LIMIT=$PROMPT_LIMIT"
echo "[INFO] EVAL_LIMIT=$EVAL_LIMIT"

bash vllm_122b/bash/smoke_122b_vllm.sh
bash vllm_122b/bash/benchmark_122b_vllm.sh
bash vllm_122b/bash/accuracy_122b_vllm.sh

echo "[INFO] vLLM 122B 离线全流程完成"
