# Progress Log

## Session: 2026-03-21

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-03-21
- Actions taken:
  - 检查目录结构，确认资料范围较小且以文档分析为主。
  - 读取相关技能说明，确定采用文件化规划方式开展分析。
  - 创建 `task_plan.md`、`findings.md`、`progress.md` 作为过程记录。
  - 阅读 `实训赛题.md`，提取课题目标、能力要求和最终交付方向。
  - 阅读 `baseline/README.md`，提取实验环境、评分指标、运行命令和代码提交要求。
  - 解析 `课题解读.pptx` 文本，提取基础功能、优化方向和加分项。
  - 阅读 `baseline/baseline_inference.py`，确认 baseline 采用朴素 `generate()` 推理流程，且 TTFT 统计较粗糙。
  - 阅读 `baseline/benchmark.py`，确认性能评测输出字段和统计口径。
  - 阅读 `baseline/evaluate_accuracy.py`，确认精度评测方法与精度约束。
  - 阅读 `baseline/requirements.txt`，确认推荐依赖栈覆盖 `vllm` 与 `llama-cpp-python`。
  - 查看 `baseline/prompts.jsonl` 样例，确认答辩/报告涉及的知识点范围。
- Files created/modified:
  - `task_plan.md` (created)
  - `findings.md` (created)
  - `progress.md` (created)

### Phase 2: Material Analysis
- **Status:** complete
- Actions taken:
  - 交叉阅读赛题说明、PPT 和 baseline 代码，确认课题目标、评分指标和交付物。
  - 识别 baseline 的能力边界：单条 HF `generate()` 推理、串行 benchmark、C-Eval 精度评测。
- Files created/modified:
  - `findings.md` (updated)

### Phase 3: Solution Planning
- **Status:** complete
- Actions taken:
  - 确定推荐技术路线为 `vLLM + Qwen2.5-14B-Instruct/量化版`。
  - 将课题执行路径拆分为环境搭建、基线复现、优化实现、评测对比、报告答辩五个阶段。
  - 整理用户可直接使用的完成规划文档。
  - 新增时间与资源约束：两天工期、基础项 1 卡 H100、加分项 4 卡 H100。
  - 调整目标为“基础必交付 + 三个加分项都尽量触达”。
- Files created/modified:
  - `task_plan.md` (updated)
  - `findings.md` (updated)
  - `课题完成规划.md` (created)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| 资料清单检查 | `rg --files .` | 列出根目录资料文件 | 已列出 `实训赛题.md`、`课题解读.pptx`、`baseline/*` | ✓ |
| 需求来源确认 | 阅读 `实训赛题.md` + `baseline/README.md` | 提取课题目标与交付要求 | 已提取核心目标、指标和提交物 | ✓ |
| 方案一致性检查 | 交叉阅读题目/PPT/脚本 | 规划需覆盖指标、交付物、实现方向 | 已覆盖并形成执行方案 | ✓ |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
|           |       | 1       |            |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 5 |
| Where am I going? | 当前轮任务已完成，可进入后续实施阶段 |
| What's the goal? | 基于现有资料形成可执行的课题完成方案 |
| What have I learned? | 资料主要由题目、解读 PPT 和 baseline 构成 |
| What have I done? | 已完成资料分析、技术路线判断和方案定稿 |

### Phase 4: Verification
- **Status:** complete
- Actions taken:
  - 回读 `task_plan.md` 和 `findings.md`，校验规划与资料结论一致。
  - 校验 `课题完成规划.md` 内容与关键文件引用是否一致。
  - 通过关键词搜索确认基线脚本、结果文件名和推荐技术路线均已写入规划文档。
- Files created/modified:
  - `task_plan.md` (updated)
  - `progress.md` (updated)

### Phase 5: Delivery
- **Status:** complete
- Actions taken:
  - 输出面向用户的课题理解与完成规划。
  - 补充说明推荐路线、当前限制与后续可执行动作。
  - 根据“两天工期 + 1 卡/4 卡 H100”约束，新增 48 小时执行版计划。
  - 修复 baseline 单条推理中的 TTFT 打印键名错误，并加入回归测试。
  - 新增 `vllm_base/` vLLM 路线及 `vllm_base/bash/` 全流程脚本，供夜间跑单卡 14B 结果。
  - 新增 `vllm_serve_exp/` 在线实验目录，支持 `vllm serve` 的并发 benchmark 和在线 accuracy。
- Files created/modified:
  - `课题完成规划.md` (created)
  - `task_plan.md` (updated)
  - `progress.md` (updated)
  - `docs/plans/2026-03-21-48h-execution-plan.md` (created)
  - `vllm_base/*` (created)
  - `vllm_base/bash/*` (created)
  - `tests/test_vllm_base_common.py` (created)
  - `vllm_serve_exp/*` (created)
  - `vllm_serve_exp/bash/*` (created)
  - `tests/test_vllm_serve_exp_common.py` (created)


---
*Update after completing each phase or encountering errors*
