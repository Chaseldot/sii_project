# Findings & Decisions

## Requirements
- 用户希望我理解当前目录中的实训课题资料，分析课题内容，并规划如何完成该课题。
- 输出应覆盖：课题目标理解、资料分析、完成路径、阶段安排、风险与建议。
- 最终规划需要兼顾题目目标、baseline 能力、评分指标与最终提交物。
- 新约束：总工期仅剩两天，规划必须压缩到 48 小时内可落地。
- 资源约束：基础任务可使用 1 张 H100；加分项目可使用 4 张 H100。
- 目标偏好：尽量触达全部 3 个加分项，即使其中部分只能做到演示级或分析级成果。

## Research Findings
- 项目根目录只有三类资料：赛题说明文档、课题解读 PPT、baseline 代码目录。
- `baseline/` 目录包含推理、评测、基准说明和依赖文件，说明题目已提供最小可运行起点。
- 课题目标不是单纯“跑通模型”，而是基于开源技术栈设计并实现一个面向边端环境的大语言模型推理框架，并围绕 Prefill/Decode、Tokenizer、KV Cache、动态 Batch、显存优化、量化等方向做系统级优化。
- 评分指标已明确为吞吐、延迟、TTFT、峰值显存和精度，其中精度损失要求不超过 5%。
- 交付物至少包括：优化后代码、项目 README、流式输出演示脚本、基线与优化后性能结果 JSON、基线与优化后精度 JSON、实验报告。
- baseline 默认实验环境为单卡 `cuda:0`，推荐模型为 `Qwen2.5-14B-Instruct` 及其量化版本。
- PPT 进一步强调基础功能至少要覆盖：模型加载、Tokenizer、Prefill+Decode、量化、流式输出；优化重点包括 KV Cache 管理、显存/内存优化、动态 batch/cache 复用，以及性能瓶颈分析。
- baseline 主脚本是 Hugging Face `AutoModelForCausalLM.from_pretrained(...).generate(...)` 的单请求推理实现，仅适合做链路验证和粗略性能起点，不构成真正的“推理框架”。
- `baseline_inference.py` 中 TTFT 只是用总延迟近似，且打印阶段访问了不存在的键 `ttft_approx_ms`，说明 baseline 代码本身也存在可修正问题，不能直接视为最终方案雏形。
- `benchmark.py` 的基线评测方式是读取 `prompts.jsonl`，逐条调用 `infer_single()`，记录整体吞吐、平均/P95/P99 延迟、TTFT 和峰值显存。它目前没有并发调度，也没有将 TTFT 与流式首 token 真正分离。
- `evaluate_accuracy.py` 通过构造 C-Eval 单选题 prompt，逐题调用 `infer_single()`，从输出中抽取首个 `A/B/C/D` 字符统计准确率，输出 `accuracy_baseline.json` / `accuracy_optimized.json` 所需字段。
- 因为评测脚本与推理函数高度耦合，后续优化更稳妥的做法是保留兼容接口，或新增 optimized 版本脚本但继续输出与 baseline 一致的指标字段。
- `requirements.txt` 除了 PyTorch/Transformers 外，还直接包含 `vllm` 与 `llama-cpp-python`，说明题目允许甚至鼓励基于成熟推理框架做优化，而不要求从零手写底层内核。
- `prompts.jsonl` 的样例问题集中在 Transformer、Prefill/Decode、KV Cache、PagedAttention、量化、Continuous Batching、FlashAttention、边端资源约束等主题，说明报告与答辩需要能解释这些概念及其工程价值。
- 在两天工期下，最合理的策略不是追求自研底层优化，而是基于成熟框架快速建立可运行结果、可复现实验和可解释分析。
- 由于 4 卡 H100 可用，`Qwen3.5-122B` 分布式部署不再只是理论项，可以争取做到最小可运行验证或启动级演示。
- 已新增 `vllm_base/` 路线，完全不修改 `baseline/`；其目标是基于 `vLLM` 复用 baseline 的 prompt/eval 文件和结果字段口径。
- 已新增 `vllm_base/bash/` 脚本，可串行执行单条推理、benchmark 和 accuracy，并将结果保存到 `results/vllm_base/<MODEL_NAME>/`。
- 已新增 `vllm_serve_exp/` 路线，用于 `vllm serve` 的在线服务实验，单独承担真实 TTFT、并发 benchmark 和在线 accuracy 评测。
- `vllm_serve_exp` 与 `vllm_base` 的职责不同：前者测在线服务能力，后者测离线/本地推理能力。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 以 `实训赛题.md` 作为需求主来源 | 文件名表明其最可能包含正式题目要求 |
| 以 `课题解读.pptx` 作为补充理解材料 | PPT 往往包含任务背景、方法提示或评分细则 |
| 以 `baseline/README.md` 和脚本作为实施起点分析对象 | 可以判断官方基线具备哪些能力、缺什么 |
| 后续规划需围绕“基线复现 -> 指标测量 -> 分项优化 -> 结果对比 -> 文档交付”展开 | baseline README 已经给出了标准对比路径与产出格式 |
| 优先设计“兼容官方评测脚本”的优化方案 | 降低交付风险，避免最后因结果格式不一致影响提交 |
| 推荐以成熟框架二次封装为主，而不是从零实现完整推理内核 | 时间有限，赛题更看重系统级优化、实验对比和工程完成度 |
| 主路线优先选 `vLLM`，`llama.cpp` 作为备选或补充对比 | 单卡 H100 + 吞吐/TTFT/显存指标更适合 `vLLM` 的技术优势 |
| 两天内采用“基础项必交付 + 三个加分项都留证据”的压缩策略 | 用户明确希望尽量触达全部加分项 |
| 分布式 `Qwen3.5-122B` 目标下调为“最小可运行/可演示”而非完整深度优化 | 两天内更现实，且能满足加分展示需求 |
| vLLM 版 benchmark/accuracy 默认继续使用 baseline 的数据文件与 JSON 字段 | 便于和 baseline 直接对比 |
| 夜间跑数优先保证稳定性，因此 vLLM 版默认 `batch_size=1` | 先拿到可比结果，后续再尝试调大 batch |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| PPT 文本提取结果存在少量格式噪声 | 仍可读取核心内容，后续按题目与 README 交叉验证 |

## Resources
- `/Users/chaselyang/cc_workspace/sii/实训/实训赛题.md`
- `/Users/chaselyang/cc_workspace/sii/实训/课题解读.pptx`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/README.md`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/baseline_inference.py`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/benchmark.py`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/evaluate_accuracy.py`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/prompts.jsonl`
- `/Users/chaselyang/cc_workspace/sii/实训/baseline/ceval_subset.jsonl`

## Visual/Browser Findings
- PPT 首页再次确认课题名称和时间信息。
- PPT 明确写出“需要完成一个具备端到端推理优化能力的大模型推理系统”。
- PPT 将“支持多种模型格式、动态 Batch、Token/KV Cache、PagedAttention 或等效机制、激活压缩/流式推理、INT8 及更低位量化”列为实现方向。
- PPT 写明加分项包含 Prompt Cache/KV Cache 复用、超大模型分布式部署、以及针对选用框架做性能瓶颈定位与优化分析。

---
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
