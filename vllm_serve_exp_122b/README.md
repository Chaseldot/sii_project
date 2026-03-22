# vLLM Serve Exp 122B

`vllm_serve_exp_122b` 是面向 `4x H100` + `122B` 模型的实验入口。

特点：
- 复用 `vllm_serve_exp` 的 benchmark / accuracy / monitor / summary 逻辑
- 单独提供 122B 专用脚本和默认参数
- 默认结果输出到 `results/vllm_serve_122b/`
- 默认模型路径是 `/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B`

## Quick Start

启动服务：

```bash
bash vllm_serve_exp_122b/bash/start_server.sh
```

跑 benchmark：

```bash
export CONCURRENCY=8
bash vllm_serve_exp_122b/bash/run_benchmark.sh
```

跑 accuracy：

```bash
export ACCURACY_CONCURRENCY=32
bash vllm_serve_exp_122b/bash/run_accuracy.sh
```

一键运行：

```bash
bash vllm_serve_exp_122b/bash/run_all.sh
```

## Important Env Vars

- `MODEL_PATH`: 默认 `/inspire/ssd/project/mianxiangdayuyanmoxing/public/Qwen3.5-122B`
- `CUDA_VISIBLE_DEVICES`: 默认 `0,1,2,3`
- `TENSOR_PARALLEL_SIZE`: 默认 `4`
- `GPU_MEMORY_UTILIZATION`: 默认 `0.90`
- `MAX_MODEL_LEN`: 默认 `16384`
- `MAX_NUM_SEQS`: 默认 `16`
- `MAX_NUM_BATCHED_TOKENS`: 默认 `8192`
- `ENABLE_PREFIX_CACHING`: 默认 `1`
- `CONCURRENCY_LIST`: benchmark 并发列表，默认 `1 2 4 8 12 16`
- `ACCURACY_CONCURRENCY`: accuracy 并发，默认 `16`
