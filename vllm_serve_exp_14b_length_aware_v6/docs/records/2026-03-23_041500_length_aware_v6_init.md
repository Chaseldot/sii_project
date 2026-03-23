# 14B Length-Aware V6 初始化

时间：`2026-03-23 04:15:00 +0800`

## 背景

`v5` 的方向是对的，但绝对 long guard 太强：

- long 本来在真实 workload 里就占大头
- 绝对 guard 会把“正常的 long 多”误判成“long 被压制”
- 结果导致调度器过度偏向 long

## v6 设计目标

`v6` 改成纯比例驱动：

- 用 `arrival ratio` 表示真实 short/long 到达结构
- 用 `queue ratio` 表示当前 short/long 积压结构
- 用两者偏差连续修正 `target_short_share`
- 不再依赖绝对 long guard 阈值

## 核心策略

- `POLICY=length_aware_v6`
- `SHORT_THRESHOLD_CHARS=256`
- `ARRIVAL_WINDOW_SIZE=256`
- `TARGET_SHORT_SHARE_BONUS=0.2`
- `MIN_SHORT_SHARE=0.5`
- `MAX_SHORT_SHARE=0.75`
- `QUEUE_RATIO_CONTROL_GAIN=1.0`
- `QUEUE_RATIO_MARGIN=0.08`
- `MAX_RATIO_ADJUSTMENT=0.2`
- `MAX_CONSECUTIVE_SHORT=4`
- `MAX_ACTIVE_REQUESTS=64`

## 关键实现

- `arrival_short_ratio`
- `queue_short_ratio`
- `ratio_adjustment = f(queue_short_ratio - arrival_short_ratio)`
- `target_short_share = base_target + ratio_adjustment`

## 预期收益

- 相比 `v5`，不再出现 guard 主导调度
- short/long 的偏置会随比例偏差平滑变化
- 更容易得到比 `v5` 均衡的结果

## 观察指标

- `scheduler_recent_arrival_short_ratio`
- `scheduler_current_queue_short_ratio`
- `scheduler_target_short_share_current`
- `scheduler_ratio_adjustment_current`
- `scheduler_ratio_bias_to_short_dispatches`
- `scheduler_ratio_bias_to_long_dispatches`
