# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v7/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 05:15:00 +0800` | 14B Length-Aware V7 初始化 | 在 V6 基础上独立分叉；从 ratio correction 进一步切到 normalized backlog pressure 驱动。 | `records/2026-03-23_051500_length_aware_v7_init.md` |

说明：

- `v7` 独立于 `v1/v2/v3/v4/v5/v6`
- `v1/v2/v3/v4/v5/v6` 的历史记录保留在各自原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
