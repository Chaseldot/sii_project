# 48-Hour Execution Plan Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 48 小时内完成基础项交付，并对 3 个加分项都形成可运行、可演示或可论证的成果。

**Architecture:** 基础项主线采用单卡 `vLLM + Qwen2.5-14B-Instruct/量化版`，保持与 baseline 一致的评测输出格式。加分项分为三条并行线：`Prompt/KV Cache` 复用实验、`4x H100` 上 `Qwen3.5-122B` 的最小分布式验证、以及对 `vLLM` 的性能瓶颈定位与分析。

**Tech Stack:** Python, PyTorch, Transformers, vLLM, CUDA, baseline scripts, markdown report assets

---

## Execution Rules

- 基础项永远优先于加分项。
- 所有实验结果必须落盘为文件，不接受“看起来跑过了”。
- 所有对比实验必须保持同一模型、同一 prompt 集、同一精度评测子集。
- `Qwen3.5-122B` 分布式项只追求“最小可运行/可演示”，不追求深度优化。
- 三人并行时，避免同时改同一文件。

## Recommended Ownership

- 成员 A：推理引擎与服务实现
- 成员 B：评测脚本、实验执行、结果落盘
- 成员 C：报告、图表、瓶颈分析、答辩材料

## Deliverables Checklist

- `results/baseline/<model_name>/results_baseline.json`
- `accuracy_baseline.json`
- `results_optimized.json`
- `accuracy_optimized.json`
- `cache_reuse_report.md` 或同等结果文档
- `distributed_qwen35_122b_report.md` 或同等结果文档
- `performance_bottleneck_report.md`
- 项目 `README.md`
- 流式输出演示脚本
- 实验报告/PPT 素材

### Task 1: Freeze Baseline Evidence

**Files:**
- Verify: `/Users/chaselyang/cc_workspace/sii/实训/baseline/baseline_inference.py`
- Verify: `/Users/chaselyang/cc_workspace/sii/实训/baseline/benchmark.py`
- Verify: `/Users/chaselyang/cc_workspace/sii/实训/baseline/evaluate_accuracy.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/results/baseline/<model_name>/results_baseline.json`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/results/baseline/<model_name>/accuracy_baseline.json`

**Step 1: 跑通基线单条推理**

Run: `python baseline/baseline_inference.py --model_path $MODEL_PATH`
Expected: 模型加载成功并输出一段生成结果。

**Step 2: 生成性能基线**

Run: `python baseline/benchmark.py --model_path $MODEL_PATH --output results/baseline/<model_name>/results_baseline.json`
Expected: 成功生成 `results/baseline/<model_name>/results_baseline.json`。

**Step 3: 生成精度基线**

Run: `python baseline/evaluate_accuracy.py --model_path $MODEL_PATH --eval_file baseline/ceval_subset.jsonl --output results/baseline/<model_name>/accuracy_baseline.json`
Expected: 成功生成 `results/baseline/<model_name>/accuracy_baseline.json`。

**Step 4: 记录基线摘要**

Write: 在 README 或实验记录中写明 baseline 的吞吐、P95 延迟、TTFT、显存、精度。

**Step 5: Commit**

```bash
git add results/baseline
git commit -m "chore: capture baseline results"
```

### Task 2: Stand Up Optimized Single-GPU Path

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/engine.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/inference.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/__init__.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/README.md`

**Step 1: 写最小 `vLLM` 引擎封装**

Implement: 提供 `load_engine()`、`generate_once()`、可选流式输出接口。

**Step 2: 先验证单条推理**

Run: `python -m vllm_base.inference --model_path $MODEL_PATH --prompt "解释KV Cache的作用"`
Expected: 成功返回生成结果。

**Step 3: 增加流式输出演示**

Implement: `--stream` 模式，能够边生成边打印。

**Step 4: 更新运行说明**

Write: README 中新增 `vllm_base` 路线运行命令。

**Step 5: Commit**

```bash
git add vllm_base README.md
git commit -m "feat: add vllm_base single-gpu inference path"
```

### Task 3: Keep Metrics Compatible

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/benchmark.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/evaluate_accuracy.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/results/vllm_base/<model_name>/results_optimized.json`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/results/vllm_base/<model_name>/accuracy_optimized.json`

**Step 1: 复用 baseline prompt 与评测集**

Implement: benchmark 和 accuracy 脚本默认读取 `baseline/prompts.jsonl` 与 `baseline/ceval_subset.jsonl`。

**Step 2: 保持输出字段兼容**

Implement: 至少输出 `overall_throughput_tps`、`avg_latency_ms`、`p95_latency_ms`、`peak_gpu_mem_gb`、`accuracy` 等字段。

**Step 3: 跑 optimized benchmark**

Run: `python -m vllm_base.benchmark --model_path $MODEL_PATH --output results/vllm_base/<model_name>/results_optimized.json`
Expected: 成功生成 `results/vllm_base/<model_name>/results_optimized.json`。

**Step 4: 跑 optimized accuracy**

Run: `python -m vllm_base.evaluate_accuracy --model_path $MODEL_PATH --eval_file baseline/ceval_subset.jsonl --output results/vllm_base/<model_name>/accuracy_optimized.json`
Expected: 成功生成 `results/vllm_base/<model_name>/accuracy_optimized.json`。

**Step 5: Commit**

```bash
git add vllm_base results/vllm_base
git commit -m "feat: add vllm_base benchmark and accuracy evaluation"
```

### Task 4: Add Prompt Cache / KV Cache Reuse Evidence

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_base/cache_reuse_demo.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/cache_reuse_report.md`

**Step 1: 设计可重复 prompt 场景**

Implement: 选择共享 system prompt 或长前缀 prompt 的请求组，制造 cache 可复用条件。

**Step 2: 实现两组实验**

Run A: 关闭或不使用复用机制。
Run B: 开启 Prompt Cache / KV Cache 复用。
Expected: 至少比较 TTFT、总延迟、吞吐变化。

**Step 3: 固化结果**

Write: `cache_reuse_report.md` 中记录实验设置、命令、前后指标、结论。

**Step 4: 准备答辩一句话**

Write: “缓存复用主要减少重复前缀的 Prefill 开销，因此更明显改善 TTFT。”

**Step 5: Commit**

```bash
git add vllm_base/cache_reuse_demo.py cache_reuse_report.md
git commit -m "feat: add cache reuse experiment"
```

### Task 5: Run Minimal Distributed Qwen3.5-122B Demo

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/distributed/serve_qwen35_122b.sh`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/distributed/test_qwen35_122b.py`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/distributed_qwen35_122b_report.md`

**Step 1: 写最小启动脚本**

Implement: 使用 `4x H100` 启动 `Qwen3.5-122B` 的 tensor parallel / distributed inference。

**Step 2: 写最小验证脚本**

Run: 对服务发 1 到 3 条请求，保存响应或截图。
Expected: 至少有一次成功返回结果，或至少服务成功启动并能接受请求。

**Step 3: 固化环境信息**

Write: 记录 GPU 数量、启动命令、模型路径、是否成功生成、失败时的报错与限制。

**Step 4: 将目标定性为“最小可运行验证”**

Write: 在报告中明确这部分主要用于展示大模型分布式部署能力，不作为主要性能优化对比对象。

**Step 5: Commit**

```bash
git add distributed distributed_qwen35_122b_report.md
git commit -m "feat: add minimal distributed qwen3.5-122b demo"
```

### Task 6: Produce Bottleneck Analysis

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/performance_bottleneck_report.md`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/profiling/` 

**Step 1: 选 profiling 口径**

Implement: 至少包含 wall time 分解、GPU 利用率/显存、TTFT 观测，能用 `nsys`、`torch.profiler`、`nvidia-smi dmon` 或日志都可以。

**Step 2: 分析 baseline 与 optimized**

Observe: Prefill 开销、Decode 开销、batch 利用率、显存峰值、cache 复用收益。

**Step 3: 输出瓶颈与方向**

Write: 至少给出 3 条瓶颈结论和对应优化方向。

**Step 4: 与加分项关联**

Write: 将瓶颈分析和 `Prompt/KV Cache`、动态 batch、分布式部署的价值关联起来。

**Step 5: Commit**

```bash
git add performance_bottleneck_report.md profiling
git commit -m "docs: add performance bottleneck analysis"
```

### Task 7: Build Final README and Report Skeleton

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/README.md`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/report_outline.md`

**Step 1: README 必含内容**

Write: 环境、模型、baseline 路线、optimized 路线、分布式演示、流式输出、结果文件说明。

**Step 2: 报告骨架**

Write: 背景、系统架构、优化点、实验设置、结果对比、瓶颈分析、AI 工具辅助说明。

**Step 3: 嵌入结果表格**

Write: 将四份 JSON 的核心指标抄入 markdown 表格。

**Step 4: Commit**

```bash
git add README.md report_outline.md
git commit -m "docs: add final report skeleton"
```

### Task 8: Final 6-Hour Triage Window

**Files:**
- Modify: `/Users/chaselyang/cc_workspace/sii/实训/README.md`
- Modify: `/Users/chaselyang/cc_workspace/sii/实训/report_outline.md`

**Step 1: 如果时间不足，保留这 4 个最小成果**

Keep:
- 基础项两份 baseline 结果
- optimized 两份结果
- 一份 cache reuse 结果
- 一份 distributed 运行证据

**Step 2: 舍弃高风险内容**

Drop:
- 自研底层 attention
- 复杂 CUDA kernel
- 深入分布式性能优化

**Step 3: 统一表述**

Write: 所有未完成项必须写成“已验证方向 / 后续工作”，不要模糊表述。

**Step 4: Final Commit**

```bash
git add .
git commit -m "docs: finalize 48-hour delivery package"
```

## Suggested 48-Hour Timeline

### 0-6 小时
- Task 1
- Task 2 Step 1-2

### 6-12 小时
- Task 2 Step 3-5
- Task 3 Step 1-2

### 12-20 小时
- Task 3 Step 3-5
- Task 4 Step 1-2

### 20-28 小时
- Task 4 Step 3-5
- Task 6 Step 1-2

### 28-36 小时
- Task 5 Step 1-3

### 36-42 小时
- Task 5 Step 4-5
- Task 6 Step 3-5

### 42-48 小时
- Task 7
- Task 8
