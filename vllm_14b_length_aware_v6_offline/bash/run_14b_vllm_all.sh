#!/usr/bin/env bash
# ===== User Config =====
# 直接改下面这些变量即可。
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
MODEL_TAG="${MODEL_TAG:-14b_length_aware_v6_offline_bs8}"
PROMPT_LIMIT="${PROMPT_LIMIT:-0}"
EVAL_LIMIT="${EVAL_LIMIT:-0}"
BATCH_SIZE="${BATCH_SIZE:-8}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-1024}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-12}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"
SAMPLE_INTERVAL_SEC="${SAMPLE_INTERVAL_SEC:-0.5}"
PLANNER_POLICY="${PLANNER_POLICY:-length_aware_v6}"
PLANNER_LOOKAHEAD_SIZE="${PLANNER_LOOKAHEAD_SIZE:-64}"
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
echo "[INFO] PLANNER_POLICY=$PLANNER_POLICY"
echo "[INFO] PLANNER_LOOKAHEAD_SIZE=$PLANNER_LOOKAHEAD_SIZE"

bash vllm_14b_length_aware_v6_offline/bash/smoke_14b_vllm.sh
bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh
bash vllm_14b_length_aware_v6_offline/bash/accuracy_14b_vllm.sh

echo "[INFO] vLLM 14B length-aware v6 离线全流程完成"
