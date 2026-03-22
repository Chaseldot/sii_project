import json
import tempfile
import unittest
from pathlib import Path

from vllm_serve_exp.summary import (
    ACCURACY_COLUMNS,
    BENCHMARK_COLUMNS,
    collect_accuracy_rows,
    collect_benchmark_rows,
    render_markdown_table,
    render_transposed_markdown_table,
)


class VLLMServeExpSummaryTest(unittest.TestCase):
    def test_collect_benchmark_rows_and_render_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exp1 = root / "14b_online_c1"
            exp2 = root / "14b_online_c8"
            exp1.mkdir()
            exp2.mkdir()

            (exp1 / "benchmark_online.json").write_text(
                json.dumps(
                    {
                        "overall_throughput_tps": 100.0,
                        "avg_latency_ms": 2000.0,
                        "peak_gpu_mem_gb": 20.5,
                    }
                ),
                encoding="utf-8",
            )
            (exp2 / "benchmark_online.json").write_text(
                json.dumps(
                    {
                        "overall_throughput_tps": 800.0,
                        "avg_latency_ms": 2600.0,
                        "peak_gpu_mem_gb": 25.1,
                    }
                ),
                encoding="utf-8",
            )

            rows = collect_benchmark_rows(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["experiment"], "14b_online_c1")
            self.assertEqual(rows[1]["experiment"], "14b_online_c8")

            table = render_markdown_table(rows, BENCHMARK_COLUMNS[:5])
            self.assertIn("| experiment |", table)
            self.assertIn("14b_online_c1", table)
            self.assertIn("800", table)

            transposed = render_transposed_markdown_table(
                rows,
                ["overall_throughput_tps", "peak_gpu_mem_gb"],
                {
                    "overall_throughput_tps": "整体吞吐率 (tokens/sec)",
                    "peak_gpu_mem_gb": "峰值 GPU 显存占用 (GB)",
                },
            )
            self.assertIn("| 指标 | 含义 | 14b_online_c1 | 14b_online_c8 |", transposed)
            self.assertIn("| overall_throughput_tps | 整体吞吐率 (tokens/sec) | 100 | 800 |", transposed)

    def test_collect_accuracy_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exp_root = root / "14b_online_accuracy"
            exp = exp_root / "14b_online_c1024"
            exp.mkdir(parents=True)
            (exp / "accuracy_online.json").write_text(
                json.dumps(
                    {
                        "accuracy": 0.76,
                        "accuracy_pct": 76.0,
                        "peak_gpu_mem_gb": 23.4,
                    }
                ),
                encoding="utf-8",
            )

            rows = collect_accuracy_rows(root, prefix="14b_online_")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["experiment"], "14b_online_accuracy/14b_online_c1024")

            table = render_markdown_table(rows, ACCURACY_COLUMNS[:4])
            self.assertIn("| experiment |", table)
            self.assertIn("14b_online_accuracy/14b_online_c1024", table)


if __name__ == "__main__":
    unittest.main()
