# Current Status

Timestamp: `2026-03-23 02:27:07 +0800`

## Goal

当前实验目标是验证：

- 在 14B 在线服务中
- 面对混合长短请求 workload
- 通过外部 request-level scheduler
- 是否能改善 short 请求的 `TTFT / latency`

这版实验不修改 vLLM 源码，只在前面增加 proxy。

## Workload

使用混合数据：

- 文件：`vllm_serve_exp_14b_length_aware/data/mixed_prompts_30s70l.jsonl`
- 总数：`512`
- short：`154`
- long：`358`
- short 来源：`baseline/prompts.jsonl`
- long 来源：`baseline/test_prompts.jsonl`

混合数据由：

- `vllm_serve_exp_14b_length_aware/build_mixed_prompts.py`
- `vllm_serve_exp_14b_length_aware/bash/build_mixed_prompts.sh`

生成。

## Baseline Config

后端统一固定为：

- 模型：`Qwen2.5-14B-Instruct`
- `MAX_NEW_TOKENS=1024`
- `MAX_NUM_SEQS=64`
- `MAX_NUM_BATCHED_TOKENS=8192`
- benchmark `CONCURRENCY=256`

基线目录：

- `vllm_serve_exp_14b_baseline`

对应主结果：

- `results/vllm_serve_14b_baseline/14b_baseline_c256/benchmark_online.json`

## Implementation Evolution

### Stage 1

第一版 length-aware proxy 只是“请求到达后立即 acquire 再转发”，没有形成真正的 proxy 内部队列。

结果特征：

- `scheduler_short_avg_gate_wait_ms` 和 `scheduler_long_avg_gate_wait_ms` 接近 `0`
- `scheduler_max_short_queue` 和 `scheduler_max_long_queue` 只有 `1`
- 与 baseline 几乎无差别

结论：

- 这版没有真正改变请求进入 vLLM 的顺序
- 不能证明 length-aware 策略本身

### Stage 2

当前有效版本已改成 active-dispatch：

- proxy 内部先排队
- 用 `MAX_ACTIVE_REQUESTS` 控制同时进入后端的活动请求数
- 在相同 active-dispatch 框架下，支持两种策略：
  - `fifo`
  - `length_aware`

核心文件：

- `vllm_serve_exp_14b_length_aware/scheduler.py`
- `vllm_serve_exp_14b_length_aware/proxy.py`
- `vllm_serve_exp_14b_length_aware/bash/start_proxy.sh`

## Three-Way Comparison

当前有效对照组为三组：

1. 直连 baseline：`client -> vLLM`
2. FIFO proxy：`client -> FIFO proxy -> vLLM`
3. Length-aware proxy：`client -> Length-aware proxy -> vLLM`

其中：

- `FIFO proxy` 和 `Length-aware proxy` 共用相同的 `MAX_ACTIVE_REQUESTS=64`
- 唯一变化只保留调度策略本身

## Latest Results at c256

### 1. Direct Baseline

结果文件：

- `results/vllm_serve_14b_baseline/14b_baseline_c256/benchmark_online.json`

关键结果：

- throughput：`2243.02 tok/s`
- overall `avg_ttft`：`53899.43 ms`
- overall `avg_latency`：`77652.62 ms`
- short `avg_ttft`：`52683.47 ms`
- short `avg_latency`：`69545.90 ms`
- long `avg_ttft`：`54422.50 ms`
- long `avg_latency`：`81139.87 ms`

### 2. FIFO Proxy

结果文件：

- `results/vllm_serve_14b_length_aware/14b_length_aware_fifo_c256/benchmark_online.json`
- `results/vllm_serve_14b_length_aware/14b_length_aware_fifo_c256/benchmark_online_scheduler_stats.json`

关键结果：

- throughput：`2225.09 tok/s`
- overall `avg_ttft`：`54389.72 ms`
- overall `avg_latency`：`78253.44 ms`
- short `avg_ttft`：`53160.87 ms`
- short `avg_latency`：`70506.66 ms`
- long `avg_ttft`：`54918.33 ms`
- long `avg_latency`：`81585.85 ms`

解释：

- 相比直连 baseline，proxy 框架本身开销很小
- 这组主要用于隔离“active-dispatch 机制”的影响

### 3. Length-Aware Proxy

结果文件：

- `results/vllm_serve_14b_length_aware/14b_length_aware_length_aware_c256/benchmark_online.json`
- `results/vllm_serve_14b_length_aware/14b_length_aware_length_aware_c256/benchmark_online_scheduler_stats.json`

当前参数：

- `POLICY=length_aware`
- `SHORT_THRESHOLD_CHARS=256`
- `SHORT_WEIGHT=3`
- `LONG_WEIGHT=1`
- `MAX_CONSECUTIVE_SHORT=6`
- `MAX_ACTIVE_REQUESTS=64`

关键结果：

- throughput：`2240.15 tok/s`
- overall `avg_ttft`：`52396.52 ms`
- overall `avg_latency`：`76203.04 ms`
- overall `p95_ttft`：`94633.10 ms`
- overall `p95_latency`：`123806.55 ms`
- short `avg_ttft`：`12559.43 ms`
- short `p95_ttft`：`27761.16 ms`
- short `avg_latency`：`29467.69 ms`
- short `p95_latency`：`52041.76 ms`
- long `avg_ttft`：`69533.14 ms`
- long `avg_latency`：`96307.08 ms`

调度器统计：

- `scheduler_policy=length_aware`
- `scheduler_max_active_requests=64`
- `scheduler_short_avg_gate_wait_ms=12190.10`
- `scheduler_long_avg_gate_wait_ms=69166.08`
- `scheduler_max_total_queue=193`

## Current Conclusion

### What worked

- Length-aware 策略显著改善了 short 请求体验
- 相比 FIFO proxy：
  - short `avg_ttft` 下降约 `76%`
  - short `p95_ttft` 下降约 `65%`
  - short `avg_latency` 下降约 `58%`
  - short `p95_latency` 下降约 `50%`
- 吞吐基本持平

### What got worse

- long 请求时延明显上升
- overall `p95_ttft` 和 `p95_latency` 变差

### Interpretation

这个策略当前更适合讲：

- **交互型短请求 QoS 优化**

而不适合讲：

- **统一优化所有请求的整体尾延迟**

## Important Note

在 proxy 方案下，vLLM 自己看到的 `num_requests_waiting` 很低，不代表系统没有排队。

准确含义是：

- baseline：队排在 vLLM 内部
- proxy 方案：队排在 proxy 内部，并被重新排序

因此分析 proxy 方案时，必须同时看：

- `benchmark_online.json`
- `benchmark_online_scheduler_stats.json`

## Next Iteration Directions

下一轮最值得调的不是后端，而是策略参数：

1. 降低 short 偏置强度
   - 例如 `SHORT_WEIGHT=2`, `LONG_WEIGHT=1`

2. 收紧 short 判定范围
   - 例如降低 `SHORT_THRESHOLD_CHARS`

3. 增强 anti-starvation
   - 例如让等待过久的 long 请求提升优先级

目标是：

- 尽量保住 short 请求收益
- 同时减轻 long 请求和 overall p95 的损失
