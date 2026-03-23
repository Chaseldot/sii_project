# 14B Length-Aware V7 初始化

时间：`2026-03-23 05:15:00 +0800`

## 背景

`v6` 已经找到一个比 `v4/v5` 更均衡的点，但主控制变量仍然是：

- `target_short_share`

这会让系统天然围绕“short 应拿几成份额”来调，而不是围绕“谁相对积压更异常”来调。

## v7 目标

`v7` 改成 normalized backlog pressure 驱动：

- `short_pressure = queue_short_ratio / arrival_short_ratio`
- `long_pressure = queue_long_ratio / arrival_long_ratio`
- `pressure_gap = short_pressure - long_pressure`

解释：

- 谁在队列中的占比，相对其到达占比更高
- 谁就更可能被相对压住
- 调度器优先补 pressure 更高的一侧

## 默认参数

- `POLICY=length_aware_v7`
- `SHORT_THRESHOLD_CHARS=256`
- `ARRIVAL_WINDOW_SIZE=256`
- `TARGET_SHORT_SHARE_BONUS=0.10`
- `MIN_SHORT_SHARE=0.35`
- `MAX_SHORT_SHARE=0.65`
- `PRESSURE_EPS=0.05`
- `PRESSURE_GAIN=0.6`
- `PRESSURE_MARGIN=0.15`
- `MAX_PRESSURE_ADJUSTMENT=0.15`
- `MAX_CONSECUTIVE_SHORT=4`
- `MAX_CONSECUTIVE_LONG=4`
- `MAX_ACTIVE_REQUESTS=64`

## 预期

- 比 `v6` 更对称
- 减少对人工 `MIN_SHORT_SHARE` 下界的依赖
- 在 short / long 间找到更自然的 backlog 平衡
