# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v6_1/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 05:00:00 +0800` | 14B Length-Aware V6.1 初始化 | 在 `v6` 基础上独立分叉；仅调默认参数，不改控制框架，用于验证 `v6` 的问题是否主要来自参数过硬。 | `records/2026-03-23_050000_length_aware_v6_1_init.md` |

说明：

- `v6.1` 独立于 `v1/v2/v3/v4/v5/v6`
- `v1/v2/v3/v4/v5/v6` 的历史记录保留在各自原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
