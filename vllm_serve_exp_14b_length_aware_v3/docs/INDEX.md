# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware_v3/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 02:45:00 +0800` | 14B Length-Aware V3 初始化 | 在 V2 基础上独立分叉；去掉绝对时间 aging，改成滑动窗口统计驱动的自适应参数更新。 | `records/2026-03-23_024500_length_aware_v3_init.md` |

说明：

- `v3` 独立于 `v1` 和 `v2`
- `v1/v2` 历史记录保留在原目录，不在这里继续追加

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
