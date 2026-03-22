# vLLM Serve Experiment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `vllm serve` 增加一套独立的在线实验目录，支持真实 TTFT 的并发 benchmark 和基于 HTTP 接口的 C-Eval accuracy 评测。

**Architecture:** 新增 `vllm_serve_exp/` 目录，服务端通过 `bash/start_server.sh` 启动 `vllm serve`。客户端分成两条线：`client_benchmark.py` 通过流式 HTTP 响应统计 TTFT/总延迟/吞吐，`evaluate_accuracy.py` 通过同步 HTTP 请求复用现有 C-Eval prompt 模板统计精度。所有结果保存到 `results/vllm_serve/<exp_name>/`。

**Tech Stack:** Python standard library, urllib, concurrent.futures, transformers tokenizer, bash, vllm serve

---

### Task 1: Common Utilities

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/common.py`
- Test: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/tests/test_vllm_serve_exp_common.py`

**Step 1: Write the failing test**

```python
def test_parse_stream_events_extracts_text_chunks():
    ...
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -p 'test_vllm_serve_exp_common.py'`
Expected: FAIL with `ModuleNotFoundError: No module named 'vllm_serve_exp'`

**Step 3: Write minimal implementation**

Implement prompt loading, C-Eval prompt builder, answer extraction, SSE line parsing, stats aggregation, JSON save helpers.

**Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -p 'test_vllm_serve_exp_common.py'`
Expected: PASS

### Task 2: Streaming Benchmark Client

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/client_benchmark.py`

**Step 1: Write the failing test**

Use common-module coverage only; keep this task implementation-focused.

**Step 2: Implement minimal benchmark client**

Implement: read prompt file, send streaming `/v1/completions` requests, measure per-request TTFT and total latency, summarize throughput and latency.

**Step 3: Verify CLI parses**

Run: `python -m vllm_serve_exp.client_benchmark --help`
Expected: exit 0

### Task 3: Online Accuracy Client

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/evaluate_accuracy.py`

**Step 1: Implement C-Eval over HTTP**

Implement: read eval set, call `/v1/completions`, parse first valid `A/B/C/D`, compute accuracy.

**Step 2: Verify CLI parses**

Run: `python -m vllm_serve_exp.evaluate_accuracy --help`
Expected: exit 0

### Task 4: Service Bash Scripts

**Files:**
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/bash/start_server.sh`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/bash/run_benchmark.sh`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/bash/run_accuracy.sh`
- Create: `/Users/chaselyang/cc_workspace/sii/实训/sii_project/vllm_serve_exp/bash/run_all.sh`

**Step 1: Implement server startup**

Run: `vllm serve ...`
Expected: service binds to configured host/port.

**Step 2: Implement benchmark runner**

Run benchmark client against the configured server URL and write JSON/logs under `results/vllm_serve/<exp_name>/`.

**Step 3: Implement accuracy runner**

Run accuracy client against the configured server URL and write JSON/logs under `results/vllm_serve/<exp_name>/`.

**Step 4: Verify bash syntax**

Run: `bash -n vllm_serve_exp/bash/*.sh`
Expected: exit 0
