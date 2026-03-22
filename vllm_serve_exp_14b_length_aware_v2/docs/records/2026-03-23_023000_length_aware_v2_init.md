# Length-Aware V2 Init

Timestamp: `2026-03-23 02:30:00 +0800`

## Purpose

`v2` 基于 `v1` 的结论继续迭代，但不修改 `v1` 代码。

`v1` 已经证明：

- short 请求收益非常明显
- 但 long 请求时延和 overall `p95` 明显变差

因此 `v2` 的目标是：

- 尽量保住 short 收益
- 缓和对 long 和 overall tail 的伤害

## Strategy

`v2` 的默认策略是：

- `POLICY=length_aware_v2`
- `SHORT_THRESHOLD_CHARS=256`
- `SHORT_WEIGHT=2`
- `LONG_WEIGHT=1`
- `MAX_CONSECUTIVE_SHORT=4`
- `LONG_AGING_WAIT_MS=30000`
- `MAX_ACTIVE_REQUESTS=64`

## Rationale

### 1. Weight 从 `3:1` 调到 `2:1`

原因：

- `v1` 的 short 偏置过强
- short 已明显“被救出来”
- long 被压得过重

预期：

- short 仍有明显优势
- long 恶化程度低于 `v1`

### 2. 增加 long aging

原因：

- `v1` 中 proxy 调度统计显示：
  - short 平均 gate wait 约 `12s`
  - long 平均 gate wait 约 `69s`
- 因此把 `LONG_AGING_WAIT_MS` 初值设为 `30000`
- 这个值高于 short 当前平均等待，但低于 long 当前平均等待

作用：

- long 如果已经在 proxy 中等太久
- 就不再继续被 short 压制
- 这样有机会改善 long tail 和 overall `p95`

## Comparison Plan

建议对照组：

1. baseline 直连
2. FIFO proxy
3. length-aware v1
4. length-aware v2

关键比较：

- `v1 -> v2`

重点指标：

- short `avg_ttft_ms`
- short `p95_ttft_ms`
- long `avg_ttft_ms`
- long `p95_ttft_ms`
- overall `p95_latency_ms`
- throughput
