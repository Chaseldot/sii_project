# 14B Length-Aware V5 初始化

时间：`2026-03-23 04:00:00 +0800`

## 背景

`v4` 已经证明显式目标/约束可以生效，但控制时机偏晚：

- 主控制信号仍然来自 completion window
- 长请求 tail 变差后才开始回调 short 偏置
- 结果上和 `v3` 接近，没有真正拉开新的均衡点

## v5 设计目标

`v5` 的目标不是继续调固定参数，而是提前在 dispatch 阶段感知队列压力：

- 用 `arrival window` 估计真实 short/long 到达比例
- 用 `target_short_share` 表达 short 应得份额
- 用 `credit/debt` 做受约束公平调度
- 用 `long head wait` 和 `long queue length` 作为 long 保护 guard

## 核心策略

- `POLICY=length_aware_v5`
- `SHORT_THRESHOLD_CHARS=256`
- `ARRIVAL_WINDOW_SIZE=256`
- `TARGET_SHORT_SHARE_BONUS=0.2`
- `MIN_SHORT_SHARE=0.5`
- `MAX_SHORT_SHARE=0.75`
- `MAX_CONSECUTIVE_SHORT=4`
- `LONG_HEAD_WAIT_GUARD_MS=45000`
- `LONG_QUEUE_LEN_GUARD=96`
- `MAX_ACTIVE_REQUESTS=64`

## 关键实现

- 主调度器：`scheduler.py`
- 代理入口：`proxy.py`
- 启动脚本：`bash/start_proxy.sh`
- benchmark：`bash/run_benchmark.sh`

## 预期收益

- short 仍显著优于 baseline / FIFO
- long 不再像 `v1/v3/v4` 那样长期被延后
- overall tail 相比 `v1/v3/v4` 更稳

## 观察指标

- `benchmark_online.json`
- `benchmark_online_length_stats.json`
- `benchmark_online_scheduler_stats.json`

重点看：

- short `avg/p95 ttft`
- long `avg/p95 latency`
- overall `p95 latency`
- `scheduler_target_short_share_current`
- `scheduler_actual_short_share`
- `scheduler_long_guard_dispatches`
