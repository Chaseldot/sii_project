# vLLM Serve 14B Official Tuned

`vllm_serve_exp_14b_official_tuned` 是独立的 14B 在线实验目录，用来测试：

- 在保持 baseline 容量参数不变时，vLLM 官方长短相关参数是否有效
- 这些官方参数是否能作为后续叠加外部调度的基础

它复用现有 `vllm_serve_exp` 的 Python 实现，但单独维护：

- 服务启动脚本
- benchmark / accuracy 脚本
- 结果目录和命名

默认配置：

- 模型：`Qwen2.5-14B-Instruct`
- benchmark 数据：`vllm_serve_exp_14b_official_tuned/data/mixed_prompts_30s70l.jsonl`
- `MAX_NEW_TOKENS=1024`
- `MAX_NUM_SEQS=64`
- `MAX_NUM_BATCHED_TOKENS=8192`
- `ENABLE_CHUNKED_PREFILL=1`
- `MAX_NUM_PARTIAL_PREFILLS=4`
- `MAX_LONG_PARTIAL_PREFILLS=1`
- `LONG_PREFILL_TOKEN_THRESHOLD=1024`
- `CONCURRENCY_LIST=128 256 512`

核心脚本：

- `bash vllm_serve_exp_14b_official_tuned/bash/start_server.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_accuracy.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_all.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/build_mixed_prompts.sh`
