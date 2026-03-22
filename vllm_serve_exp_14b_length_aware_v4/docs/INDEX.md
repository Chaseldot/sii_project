# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v4/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 03:05:00 +0800` | 14B Length-Aware V4 初始化 | 在 V3 基础上独立分叉；去掉启发式自适应主导，改成显式目标函数与硬约束控制。 | `records/2026-03-23_030500_length_aware_v4_init.md` |

说明：

- `v4` 独立于 `v1/v2/v3`
- `v1/v2/v3` 的历史记录保留在各自原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
