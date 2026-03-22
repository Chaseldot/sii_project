#!/usr/bin/env bash
# ===== User Config =====
# 直接修改下面这些变量即可，无需再到脚本中部找默认值。
MODEL_PATH="${MODEL_PATH:-/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-14b-vllm-serve}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# 模型加载 / 格式 / 量化
LOAD_FORMAT="${LOAD_FORMAT:-auto}"          # auto / safetensors / pt / gguf 等
DTYPE="${DTYPE:-bfloat16}"                  # auto / float16 / bfloat16
QUANTIZATION="${QUANTIZATION:-}"            # 例如 awq / gptq；为空表示不启用
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-1}" # 1 开启，0 关闭

# 动态 Batch / Token 缓存 / 显存相关
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.9}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
# MAX_NUM_SEQS="${MAX_NUM_SEQS:-128}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-0}"  # 1 开启 Prompt Cache / Prefix Cache
# ===== End User Config =====
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

export CUDA_VISIBLE_DEVICES

CMD=(
  vllm serve "$MODEL_PATH"
  --host "$HOST"
  --port "$PORT"
  --served-model-name "$SERVED_MODEL_NAME"
  --load-format "$LOAD_FORMAT"
  --dtype "$DTYPE"
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --max-model-len "$MAX_MODEL_LEN"
  # --max-num-seqs "$MAX_NUM_SEQS"
  --max-num-batched-tokens "$MAX_NUM_BATCHED_TOKENS"
)

if [[ "$TRUST_REMOTE_CODE" == "1" ]]; then
  CMD+=(--trust-remote-code)
fi
if [[ -n "$QUANTIZATION" ]]; then
  CMD+=(--quantization "$QUANTIZATION")
fi
if [[ "$ENABLE_PREFIX_CACHING" == "1" ]]; then
  CMD+=(--enable-prefix-caching)
fi

"${CMD[@]}"
