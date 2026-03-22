# Length-Aware V4 Init

Timestamp: `2026-03-23 03:05:00 +0800`

## Purpose

`v4` 基于 `v3` 的结论继续迭代，但不修改 `v1/v2/v3` 代码。

当前判断是：

- `v1` 能强力保护 short，但 long 和 overall tail 受损
- `v2` 的绝对时间 aging 对 workload 太敏感
- `v3` 的自适应方向可行，但还不是显式受约束优化

因此 `v4` 的目标是：

- 把“目标函数/约束条件”正式落进控制器
- 不再只靠启发式增减权重

## Strategy

`v4` 的默认策略是：

- `POLICY=length_aware_v4`
- `SHORT_THRESHOLD_CHARS=256`
- 初始 `SHORT_WEIGHT=2`
- 初始 `LONG_WEIGHT=1`
- 初始 `MAX_CONSECUTIVE_SHORT=4`
- `MAX_ACTIVE_REQUESTS=64`
- `ADAPT_WINDOW_SIZE=128`
- `ADAPT_UPDATE_INTERVAL=64`
- `OBJECTIVE_SHORT_P95_TTFT_MS=45000`
- `CONSTRAINT_MAX_LONG_P95_LATENCY_MS=110000`
- `CONSTRAINT_MAX_OVERALL_P95_LATENCY_MS=110000`

## Control Logic

控制器每次更新时：

1. 统计近期完成请求窗口
2. 计算：
   - `short_p95_ttft_ms`
   - `long_p95_latency_ms`
   - `overall_p95_latency_ms`
3. 按显式规则决策：
   - 如果 long 或 overall 约束被破坏
     - 降低 short 偏置
   - 否则如果 short 目标未达成
     - 增强 short 偏置
   - 否则保持当前参数

## Why This Version Exists

`v4` 的重点不是“更复杂的自适应”，而是：

- 显式目标
- 显式约束
- 可解释的更新逻辑

这能更清楚回答：

- short QoS 到底是不是在满足约束的前提下优化出来的

## Suggested Comparison

建议对照：

1. baseline 直连
2. FIFO proxy
3. length-aware v1
4. length-aware v4

重点比较：

- `v4 -> fifo`
- `v4 -> v1`

关键指标：

- short `avg/p95 TTFT`
- long `p95 latency`
- overall `p95 latency`
- throughput
- `scheduler_policy_updates`
