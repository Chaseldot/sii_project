# vLLM 14B Offline

`vllm_14b` 是面向 `Qwen2.5-14B-Instruct` 的离线 vLLM 推理、benchmark 和 accuracy 评测目录。

默认面向新测试集：
- `baseline/test_prompts.jsonl`

核心入口：
- `python -m vllm_14b.inference`
- `python -m vllm_14b.benchmark`
- `python -m vllm_14b.evaluate_accuracy`

脚本入口：
- `bash vllm_14b/bash/smoke_14b_vllm.sh`
- `bash vllm_14b/bash/benchmark_14b_vllm.sh`
- `bash vllm_14b/bash/accuracy_14b_vllm.sh`
- `bash vllm_14b/bash/run_14b_vllm_all.sh`

默认模型路径：
- `/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct`

默认结果目录：
- `results/vllm_14b/`

离线结果默认会带 GPU 显存采样字段：
- `avg_gpu_mem_gb`
- `peak_gpu_mem_gb`
- `avg_gpu_mem_utilization_perc`
- `peak_gpu_mem_utilization_perc`
- `gpu_total_mem_gb`
