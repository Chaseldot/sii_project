# vLLM Serve 14B Length-Aware V5

`vllm_serve_exp_14b_length_aware_v5` 是独立的 14B 在线调度实验目录。

这版不改 vLLM 源码，只在前面加一个外部 active-dispatch proxy，并改成 queue-aware constrained fair scheduling：

- `fifo`
- `short queue`
- `long queue`
- `arrival window` 估计真实 short/long 到达比例
- `target_short_share` 作为 short 应得服务份额
- `credit/debt` 决定下一次优先 dispatch `short` 还是 `long`
- `MAX_CONSECUTIVE_SHORT` 限制连续 short
- `LONG_HEAD_WAIT_GUARD_MS` / `LONG_QUEUE_LEN_GUARD` 保护 long 队列
- `MAX_ACTIVE_REQUESTS` 统一控制进入后端的活动请求数

后端服务复用约定：

- 默认继续复用 baseline 已经启动的 `8020` 服务
- 默认 `SERVED_MODEL_NAME=qwen2.5-14b-vllm-length-aware`
- 迭代新版本时优先只重启 proxy，不重复起 server

推荐做三组对照：

- `client -> vLLM`
- `client -> FIFO proxy -> vLLM`
- `client -> Length-Aware proxy -> vLLM`

核心脚本：

- `bash vllm_serve_exp_14b_length_aware_v5/bash/start_server.sh`
- `bash vllm_serve_exp_14b_length_aware_v5/bash/start_proxy.sh`
- `bash vllm_serve_exp_14b_length_aware_v5/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_length_aware_v5/bash/run_all.sh`

当前实验进展和结果沉淀见：

- `vllm_serve_exp_14b_length_aware_v5/docs/INDEX.md`

关键结果文件：

- `benchmark_online.json`
- `benchmark_online_length_stats.json`
- `benchmark_online_scheduler_stats.json`
