# 14B Length-Aware V7 分析

时间：`2026-03-23 05:35:00 +0800`

## 基线对比

Baseline：

- `results/vllm_serve_14b_baseline/14b_baseline_c256/benchmark_online.json`

V7：

- `results/vllm_serve_14b_length_aware_v7/14b_length_aware_v7_length_aware_v7_c256/benchmark_online.json`

### 整体指标

- throughput：`2243.02 -> 2234.71`，`-0.37%`
- avg TTFT：`53899.43 -> 54370.30`，`+0.87%`
- p95 TTFT：`80422.76 -> 86504.11`，`+7.56%`
- avg latency：`77652.62 -> 78490.61`，`+1.08%`
- p95 latency：`106650.16 -> 115219.48`，`+8.03%`

### Short 请求

- avg TTFT：`52683.47 -> 41333.46`，`-21.54%`
- p95 TTFT：`79488.61 -> 64269.67`，`-19.15%`
- avg latency：`69545.90 -> 59287.11`，`-14.75%`
- p95 latency：`102541.61 -> 89160.01`，`-13.05%`

### Long 请求

- avg TTFT：`54422.50 -> 59978.33`，`+10.21%`
- p95 TTFT：`81266.36 -> 87532.04`，`+7.71%`
- avg latency：`81139.87 -> 86751.33`，`+6.92%`
- p95 latency：`108200.87 -> 116079.18`，`+7.28%`

## 与 V6 的关系

V6：

- `results/vllm_serve_14b_length_aware_v6/14b_length_aware_v6_length_aware_v6_c256/benchmark_online.json`

相对 `v6`：

- overall p95 TTFT：`-7.63%`
- overall p95 latency：`-5.87%`
- short avg TTFT：`+78.14%`
- short p95 TTFT：`+38.51%`
- long avg latency：`-5.52%`
- long p95 latency：`-5.82%`

结论：

- `v7` 比 `v6` 更均衡
- 但 short 收益明显回落
- 当前 milestone 仍保留 `v6`

## 资源与队列

- avg GPU mem：`+1.64%`
- peak GPU mem：`+1.64%`
- avg KV cache：`-2.20%`
- max KV cache：`-3.55%`

注意：

- proxy 版本的 vLLM 内部 waiting 指标会显著下降
- 这不代表系统没有排队
- 只是排队位置从 vLLM 内部移到了 proxy 外部

## 调度器 insight

来源：

- `results/vllm_serve_14b_length_aware_v7/14b_length_aware_v7_length_aware_v7_c256/benchmark_online_scheduler_stats.json`

关键点：

- `arrival ratio` 约 `28% short / 72% long`
- `pressure controller` 持续判断 long 的相对积压更高
- 因此 `target_short_share` 被压到约 `0.36`
- 最终 `actual_short_share` 约 `0.30`

这解释了为什么：

- `v7` 比 `v6` 更照顾 long
- 但 short 收益也明显回落
