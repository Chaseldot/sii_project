export CUDA_VISIBLE_DEVICES=0
export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
python - <<'PY'
from vllm import LLM, SamplingParams

model_path = "/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct"
llm = LLM(
    model=model_path,
    trust_remote_code=True,
    tensor_parallel_size=1,
)

params = SamplingParams(
    temperature=0.0,
    max_tokens=256,
)

outputs = llm.generate(
    ["请用三句话解释大语言模型推理中KV Cache的作用。"],
    params,
)

print(outputs[0].outputs[0].text)
PY