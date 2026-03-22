# Length-Aware V3 Init

Timestamp: `2026-03-23 02:45:00 +0800`

## Purpose

`v3` 基于 `v2` 的反例继续迭代，但不修改 `v1/v2` 代码。

`v2` 的问题是：

- 绝对时间 `LONG_AGING_WAIT_MS` 对 workload 过于敏感
- 在当前数据比例下，long promotion 触发过多
- 最终把 short QoS 伤回去了

因此 `v3` 的目标是：

- 去掉绝对时间阈值
- 改成基于近期 workload 统计的自适应调度

## Strategy

`v3` 的默认策略是：

- `POLICY=length_aware_v3`
- `SHORT_THRESHOLD_CHARS=256`
- 初始 `SHORT_WEIGHT=2`
- 初始 `LONG_WEIGHT=1`
- 初始 `MAX_CONSECUTIVE_SHORT=4`
- `MAX_ACTIVE_REQUESTS=64`
- `ADAPT_WINDOW_SIZE=128`
- `ADAPT_UPDATE_INTERVAL=64`

## Core Idea

保留双队列：

- `short queue`
- `long queue`

但不再使用固定 `LONG_AGING_WAIT_MS`。

改为：

1. 持续记录近期完成请求
2. 在滑动窗口内统计：
   - short/long 比例
   - short/long `p95 TTFT`
   - short/long `p95 latency`
   - short/long 平均 gate wait
3. 周期性更新：
   - `SHORT_WEIGHT`
   - `MAX_CONSECUTIVE_SHORT`

## Adaptation Rule

当前实现是一个轻量离散控制器：

1. 先根据近期 short 比例给出基础目标
   - short 占比低：更偏向 short
   - short 占比高：偏置减弱

2. 再根据近期 QoS 指标修正
   - 如果 short `p95 TTFT` 依然接近 long
     - 增强 short 偏置
   - 如果 long `p95 latency` 明显过高
     - 减弱 short 偏置

3. 每次只单步更新
   - 防止参数振荡过快

## Why V3 Is More Natural

相比 `v2`：

- 不再依赖绝对时间阈值
- 更贴近当前 workload 比例和近期统计
- 更容易随着请求分布变化自适应

## Comparison Plan

建议对照组：

1. baseline 直连
2. FIFO proxy
3. length-aware v1
4. length-aware v2
5. length-aware v3

重点比较：

- `v3 -> v2`
- `v3 -> fifo`

关键指标：

- short `avg/p95 TTFT`
- long `avg/p95 latency`
- overall `p95 latency`
- throughput
- `scheduler_policy_updates`
