# vLLM Serve 14B Length-Aware

`vllm_serve_exp_14b_length_aware` 是独立的 14B 在线调度实验目录。

这版不改 vLLM 源码，只在前面加一个外部双队列 proxy：

- `short queue`
- `long queue`
- `SHORT_WEIGHT:LONG_WEIGHT` 加权轮询
- `MAX_CONSECUTIVE_SHORT` 防止 long 饿死

第一版不把 `inflight` 作为主要变量，目标是先验证：

- 在混合长短请求场景下
- 仅靠 request-level 重排顺序
- 能否改善 short 请求的 `TTFT / latency`

核心脚本：

- `bash vllm_serve_exp_14b_length_aware/bash/start_server.sh`
- `bash vllm_serve_exp_14b_length_aware/bash/start_proxy.sh`
- `bash vllm_serve_exp_14b_length_aware/bash/run_benchmark.sh`
- `bash vllm_serve_exp_14b_length_aware/bash/run_all.sh`

关键结果文件：

- `benchmark_online.json`
- `benchmark_online_length_stats.json`
- `benchmark_online_scheduler_stats.json`
