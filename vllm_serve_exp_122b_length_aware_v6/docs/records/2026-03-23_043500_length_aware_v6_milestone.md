# 122B Length-Aware V6 Milestone

时间：`2026-03-23 04:35:00 +0800`

## 结论

当前 milestone 版本定为 `v6`。

原因：

- 相比 baseline，`v6` 仍然显著改善 short 请求体验
- 相比 `v4`，`v6` 明显回收了 long 和 overall tail 代价
- 相比 `v5`，`v6` 成功修正了 absolute long guard 导致的策略跑偏

## 与 Baseline 的详细对比

Baseline：

- `results/vllm_serve_122b_baseline/122b_baseline_c256/benchmark_online.json`

V6：

- `results/vllm_serve_122b_length_aware_v6/122b_length_aware_v6_length_aware_v6_c256/benchmark_online.json`

### 整体指标

- throughput：`2243.02 -> 2251.05`，`+0.36%`
- avg TTFT：`53899.43 -> 52440.58`，`-2.71%`
- p95 TTFT：`80422.76 -> 93645.07`，`+16.44%`
- avg latency：`77652.62 -> 76260.73`，`-1.79%`
- p95 latency：`106650.16 -> 122405.67`，`+14.77%`

### Short 请求

- avg TTFT：`52683.47 -> 23202.74`，`-55.96%`
- p95 TTFT：`79488.61 -> 46399.85`，`-41.63%`
- avg latency：`69545.90 -> 40098.68`，`-42.34%`
- p95 latency：`102541.61 -> 65330.19`，`-36.29%`

### Long 请求

- avg TTFT：`54422.50 -> 65017.76`，`+19.47%`
- p95 TTFT：`81266.36 -> 94372.05`，`+16.13%`
- avg latency：`81139.87 -> 91816.47`，`+13.16%`
- p95 latency：`108200.87 -> 123252.80`，`+13.91%`

## 与 V4 / V5 的位置关系

### 相比 V4

- `v4` short 更激进：short avg TTFT `14783.03`
- `v6` short 稍弱：short avg TTFT `23202.74`
- 但 `v6` 更均衡：overall p95 latency `122405.67`，优于 `v4` 的 `124139.30`
- `v6` 的 long p95 latency `123252.80`，优于 `v4` 的 `125955.35`

### 相比 V5

- `v5` 明显跑偏到 long 优先：short avg TTFT `101913.87`
- `v6` 将 short avg TTFT 拉回到 `23202.74`
- `v5` overall p95 latency `159573.15`
- `v6` overall p95 latency `122405.67`

## 调度器行为

来源：

- `results/vllm_serve_122b_length_aware_v6/122b_length_aware_v6_length_aware_v6_c256/benchmark_online_scheduler_stats.json`

关键信号：

- `scheduler_recent_arrival_short_ratio = 0.2812`
- `scheduler_target_short_share_current = 0.5`
- `scheduler_actual_short_share = 0.3008`
- `scheduler_ratio_adjustment_avg = -0.1192`

解释：

- 真实到达流中 short 约占 `28%`
- 队列中的 short 占比长期低于 arrival short 占比
- 控制器据此持续向 long 方向做比例修正
- 但修正是连续的，不再像 `v5` 那样由绝对 guard 抢占主导

## 当前 Insight

`v6` 说明：用“arrival ratio 与 queue ratio 偏差”做连续修正，比绝对 long guard 更自然、更稳。

它仍然是 short-first 策略，但已经从“极端短优先”收敛到“可接受的均衡短优先”。
