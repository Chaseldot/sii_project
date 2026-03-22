# Experiment Index

固定归档目录：

- `vllm_serve_exp_14b_length_aware/docs/records/`

时间索引：

| Timestamp | Topic | Summary | Record |
| --- | --- | --- | --- |
| `2026-03-23 02:27:07 +0800` | 14B Length-Aware 初始阶段 | 完成 baseline、FIFO proxy、Length-aware proxy 三组对照；确认 short 请求收益明显，但 long 和 overall p95 变差。 | `records/2026-03-23_022707_length_aware_status.md` |

后续规则：

1. 每一轮重要实验或策略改动，新增一份时间戳文档到 `docs/records/`
2. 同时在本索引追加一条记录
3. 不覆盖旧文档，只追加新版本
