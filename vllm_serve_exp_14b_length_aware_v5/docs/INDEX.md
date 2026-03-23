# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v5/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 04:00:00 +0800` | 14B Length-Aware V5 初始化 | 在 V4 基础上独立分叉；去掉 completion-window 主导，改成 arrival/queue-aware constrained fair scheduling。 | `records/2026-03-23_040000_length_aware_v5_init.md` |

说明：

- `v5` 独立于 `v1/v2/v3/v4`
- `v1/v2/v3/v4` 的历史记录保留在各自原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
