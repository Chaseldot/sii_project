# vLLM Serve Adaptive

`vllm_serve_exp_adaptive` 是独立于原始基线目录的优化实验目录。

核心思路：
- 不改 vLLM 内核
- 在 vLLM 前面增加一个轻量代理层
- 代理基于 `KV Cache 使用率 / waiting queue / running requests` 做 admission control

核心文件：
- `python -m vllm_serve_exp_adaptive.proxy`
- `python -m vllm_serve_exp_adaptive.stats_client`
- `bash/start_proxy.sh`
- `bash/run_benchmark_14b.sh`
- `bash/run_benchmark_122b.sh`
- `bash/run_accuracy_14b.sh`
- `bash/run_accuracy_122b.sh`

推荐实验方式：
1. 先启动原始 vLLM 服务
2. 再启动 adaptive proxy
3. benchmark / accuracy 全部打到 proxy，而不是直接打 vLLM

结果目录里除了原有 `benchmark_online.json` / `accuracy_online.json` 外，还会多一份：
- `scheduler_stats.json`

可以重点观察：
- `scheduler_delayed_ratio`
- `scheduler_avg_gate_wait_ms`
- `scheduler_max_gate_wait_ms`
- `avg_num_requests_waiting`
- `avg_ttft_ms`
- `p95_ttft_ms`
