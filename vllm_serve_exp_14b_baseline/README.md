# vLLM Serve 14B Baseline

`vllm_serve_exp_14b_baseline` 是独立的 14B 在线基线目录，用来先确定：

- 在新数据上何时开始出现明显瓶颈
- baseline 的 `CONCURRENCY / MAX_NUM_SEQS / MAX_NUM_BATCHED_TOKENS` 取值

它复用现有 `vllm_serve_exp` 的 Python 实现，但单独维护：

- 服务启动脚本
- benchmark / accuracy 脚本
- 结果目录和命名

默认配置：

- 模型：`Qwen2.5-14B-Instruct`
- `MAX_NEW_TOKENS=1024`
- `MAX_NUM_SEQS=64`
- `MAX_NUM_BATCHED_TOKENS=8192`
- `CONCURRENCY_LIST=64 128 256 512 1024`

核心脚本：

- `bash vllm_serve_exp_14b_baseline/bash/start_server.sh`
- `bash vllm_serve_exp_14b_baseline/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_baseline/bash/run_accuracy.sh`
- `bash vllm_serve_exp_14b_baseline/bash/run_all.sh`
