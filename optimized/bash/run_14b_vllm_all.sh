#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

: "${MODEL_PATH:?Please export MODEL_PATH=/path/to/Qwen2.5-14B-Instruct}"

echo "[INFO] ROOT_DIR=$ROOT_DIR"
echo "[INFO] MODEL_PATH=$MODEL_PATH"
echo "[INFO] CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}"
echo "[INFO] BATCH_SIZE=${BATCH_SIZE:-1}"
echo "[INFO] EVAL_LIMIT=${EVAL_LIMIT:-0}"

bash optimized/bash/smoke_14b_vllm.sh
bash optimized/bash/benchmark_14b_vllm.sh
bash optimized/bash/accuracy_14b_vllm.sh

echo "[INFO] vLLM 14B 全流程完成"
