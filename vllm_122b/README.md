# vLLM 122B Offline

`vllm_122b` 是面向 `Qwen3.5-122B + 4x H100` 的离线 vLLM 推理、benchmark 和 accuracy 评测目录。

核心入口：
- `python -m vllm_122b.inference`
- `python -m vllm_122b.benchmark`
- `python -m vllm_122b.evaluate_accuracy`

脚本入口：
- `bash vllm_122b/bash/smoke_122b_vllm.sh`
- `bash vllm_122b/bash/benchmark_122b_vllm.sh`
- `bash vllm_122b/bash/accuracy_122b_vllm.sh`
- `bash vllm_122b/bash/run_122b_vllm_all.sh`

默认模型路径：
- `/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B`

默认结果目录：
- `results/vllm_122b/`

离线结果默认会带 GPU 显存采样字段：
- `avg_gpu_mem_gb`
- `peak_gpu_mem_gb`
- `avg_gpu_mem_utilization_perc`
- `peak_gpu_mem_utilization_perc`
- `gpu_total_mem_gb`
