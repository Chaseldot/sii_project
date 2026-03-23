# vLLM 14B Length-Aware V6 Offline

`vllm_14b_length_aware_v6_offline` 是把在线 `14b-v6` 的调度思想迁到离线批量推理后的独立目录。

这个目录已经收口成独立提交包：

- 不依赖仓库内其他 Python 包
- 默认测试数据放在本目录 `data/`
- 默认结果输出到本目录 `results/`
- `max_num_seqs` 默认不显式传给 vLLM，由 vLLM 自己决定

核心变化：

- 不再使用 HTTP proxy / active dispatch
- 保留 `short/long` 分桶
- 保留 `arrival ratio vs queue ratio` 的连续修正
- 保留 `credit/debt` 和 `max_consecutive_short`
- 将在线单请求 dispatch 改成离线 `batch planner`
- 默认在 batch 内按估计输入 token 长度升序排序，尽量减少长短混跑

核心入口：

- `python -m vllm_14b_length_aware_v6_offline.inference`
- `python -m vllm_14b_length_aware_v6_offline.benchmark`
- `python -m vllm_14b_length_aware_v6_offline.evaluate_accuracy`

脚本入口：

- `bash vllm_14b_length_aware_v6_offline/bash/smoke_14b_vllm.sh`
- `bash vllm_14b_length_aware_v6_offline/bash/benchmark_14b_vllm.sh`
- `bash vllm_14b_length_aware_v6_offline/bash/accuracy_14b_vllm.sh`
- `bash vllm_14b_length_aware_v6_offline/bash/run_14b_vllm_all.sh`

建议实验对照：

- 原始离线：`vllm_14b`
- 新离线 FIFO planner：`PLANNER_POLICY=fifo`
- 新离线 v6 planner：`PLANNER_POLICY=length_aware_v6`

默认数据文件：

- `data/test_prompts.jsonl`
- `data/ceval_subset.jsonl`
