# vLLM Serve 14B Length-Aware V2

`vllm_serve_exp_14b_length_aware_v2` 是独立的 14B 在线调度实验目录。

这版不改 vLLM 源码，只在前面加一个外部 active-dispatch proxy：

- `fifo`
- `short queue`
- `long queue`
- `SHORT_WEIGHT:LONG_WEIGHT` 更温和的加权轮询
- `LONG_AGING_WAIT_MS` 让等待过久的 long 请求提升优先级
- `MAX_CONSECUTIVE_SHORT` 防止 long 饿死
- `MAX_ACTIVE_REQUESTS` 统一控制进入后端的活动请求数

后端服务复用约定：

- 默认继续复用 baseline 已经启动的 `8020` 服务
- 默认 `SERVED_MODEL_NAME=qwen2.5-14b-vllm-baseline`
- 迭代新版本时优先只重启 proxy，不重复起 server

推荐做三组对照：

- `client -> vLLM`
- `client -> FIFO proxy -> vLLM`
- `client -> Length-Aware proxy -> vLLM`

核心脚本：

- `bash vllm_serve_exp_14b_length_aware_v2/bash/start_server.sh`
- `bash vllm_serve_exp_14b_length_aware_v2/bash/start_proxy.sh`
- `bash vllm_serve_exp_14b_length_aware_v2/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_length_aware_v2/bash/run_all.sh`

当前实验进展和结果沉淀见：

- `vllm_serve_exp_14b_length_aware_v2/docs/INDEX.md`

关键结果文件：

- `benchmark_online.json`
- `benchmark_online_length_stats.json`
- `benchmark_online_scheduler_stats.json`
