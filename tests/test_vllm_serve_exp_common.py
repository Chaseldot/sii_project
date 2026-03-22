import unittest


from vllm_serve_exp.common import (
    build_ceval_prompt,
    compute_online_benchmark_stats,
    extract_answer,
    parse_stream_event,
)


class VLLMServeExpCommonTest(unittest.TestCase):
    def test_build_ceval_prompt_contains_choices(self):
        item = {
            "question": "太阳从哪边升起？",
            "A": "东边",
            "B": "西边",
            "C": "南边",
            "D": "北边",
        }
        prompt = build_ceval_prompt(item)
        self.assertIn("题目：太阳从哪边升起？", prompt)
        self.assertIn("A. 东边", prompt)
        self.assertTrue(prompt.endswith("答案："))

    def test_extract_answer_returns_first_valid_option(self):
        self.assertEqual(extract_answer("C\n解释略"), "C")
        self.assertEqual(extract_answer("答案是 b",), "B")
        self.assertEqual(extract_answer("不知道"), "X")

    def test_parse_stream_event_extracts_text_and_done_signal(self):
        text, done = parse_stream_event(b'data: {"choices":[{"text":"hello"}]}\n')
        self.assertEqual(text, "hello")
        self.assertFalse(done)

        text, done = parse_stream_event(b"data: [DONE]\n")
        self.assertEqual(text, "")
        self.assertTrue(done)

    def test_compute_online_benchmark_stats_keeps_expected_schema(self):
        results = [
            {"output_tokens": 100, "latency_ms": 1000.0, "ttft_ms": 200.0},
            {"output_tokens": 120, "latency_ms": 2000.0, "ttft_ms": 300.0},
        ]
        stats = compute_online_benchmark_stats(results, wall_time_sec=5.0)
        self.assertEqual(stats["total_prompts"], 2)
        self.assertEqual(stats["total_output_tokens"], 220)
        self.assertEqual(stats["overall_throughput_tps"], 44.0)
        self.assertEqual(stats["avg_latency_ms"], 1500.0)
        self.assertEqual(stats["p95_latency_ms"], 1950.0)
        self.assertEqual(stats["avg_ttft_ms"], 250.0)
        self.assertEqual(stats["p95_ttft_ms"], 295.0)


if __name__ == "__main__":
    unittest.main()
