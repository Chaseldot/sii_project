import unittest


from vllm_base.common import (
    build_ceval_prompt,
    compute_benchmark_stats,
    extract_answer,
)


class OptimizedCommonTest(unittest.TestCase):
    def test_build_ceval_prompt_contains_question_and_choices(self):
        item = {
            "question": "1+1=?",
            "A": "1",
            "B": "2",
            "C": "3",
            "D": "4",
        }

        prompt = build_ceval_prompt(item)

        self.assertIn("以下是一道单选题", prompt)
        self.assertIn("题目：1+1=?", prompt)
        self.assertIn("B. 2", prompt)
        self.assertTrue(prompt.endswith("答案："))

    def test_extract_answer_returns_first_valid_choice(self):
        self.assertEqual(extract_answer("B\n因为..."), "B")
        self.assertEqual(extract_answer("答案是 c"), "C")
        self.assertEqual(extract_answer("不知道"), "X")

    def test_compute_benchmark_stats_keeps_expected_schema(self):
        results = [
            {"output_tokens": 100, "total_latency_ms": 1000.0, "ttft_ms": 300.0},
            {"output_tokens": 120, "total_latency_ms": 2000.0, "ttft_ms": 500.0},
        ]

        stats = compute_benchmark_stats(
            results=results,
            wall_time_sec=4.0,
            max_new_tokens=256,
            peak_gpu_mem_gb=12.345,
        )

        self.assertEqual(stats["total_prompts"], 2)
        self.assertEqual(stats["total_output_tokens"], 220)
        self.assertEqual(stats["max_new_tokens_cfg"], 256)
        self.assertEqual(stats["overall_throughput_tps"], 55.0)
        self.assertEqual(stats["avg_latency_ms"], 1500.0)
        self.assertEqual(stats["p95_latency_ms"], 1950.0)
        self.assertEqual(stats["avg_ttft_ms"], 400.0)
        self.assertEqual(stats["peak_gpu_mem_gb"], 12.345)


if __name__ == "__main__":
    unittest.main()
