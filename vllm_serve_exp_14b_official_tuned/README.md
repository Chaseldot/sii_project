# vLLM Serve 14B Official Tuned

`vllm_serve_exp_14b_official_tuned` 是独立的 14B 在线实验目录，用来测试：

- 在当前安装版 vLLM 0.18.0 的可用参数范围内，官方长序列相关调度参数是否有效
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
- `MAX_NUM_BATCHED_TOKENS=4096`
- `ENABLE_CHUNKED_PREFILL=1`
- `CONCURRENCY_LIST=128 256 512`

说明：

- 当前运行环境下，`Concurrent Partial Prefill` 不受支持，因此这里不启用
  `max_num_partial_prefills / max_long_partial_prefills / long_prefill_token_threshold`
- 这版官方 tuned 的主要有效参数是：
  - `enable_chunked_prefill`
  - `max_num_batched_tokens`

核心脚本：

- `bash vllm_serve_exp_14b_official_tuned/bash/start_server.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_accuracy.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/run_all.sh`
- `bash vllm_serve_exp_14b_official_tuned/bash/build_mixed_prompts.sh`
