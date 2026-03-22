# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v2/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 02:30:00 +0800` | 14B Length-Aware V2 初始化 | 在 V1 基础上独立分叉；默认策略改为 `2:1 + long aging(30s)`，目标是缓和 long 和 overall p95 的损失。 | `records/2026-03-23_023000_length_aware_v2_init.md` |

说明：

- `v2` 独立于 `v1`
- `v1` 的历史记录保留在原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
