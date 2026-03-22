import sys
import time
import types
import unittest
from unittest.mock import patch

np = types.ModuleType("numpy")
np.mean = lambda xs: sum(xs) / len(xs)
np.min = min
np.max = max
np.percentile = lambda xs, q: sorted(xs)[0]
sys.modules.setdefault("numpy", np)

from vllm_serve_exp.evaluate_accuracy import evaluate_online_accuracy


class VLLMServeExpAccuracyTest(unittest.TestCase):
    @patch("vllm_serve_exp.evaluate_accuracy.complete_one")
    def test_evaluate_online_accuracy_supports_concurrency_and_stable_order(self, mock_complete_one):
        eval_data = [
            {
                "id": "q0",
                "question": "Q0",
                "A": "A0",
                "B": "B0",
                "C": "C0",
                "D": "D0",
                "answer": "A",
            },
            {
                "id": "q1",
                "question": "Q1",
                "A": "A1",
                "B": "B1",
                "C": "C1",
                "D": "D1",
                "answer": "B",
            },
            {
                "id": "q2",
                "question": "Q2",
                "A": "A2",
                "B": "B2",
                "C": "C2",
                "D": "D2",
                "answer": "C",
            },
        ]

        def fake_complete_one(base_url, model, prompt, max_tokens, temperature):
            if "Q0" in prompt:
                time.sleep(0.05)
                return "A"
            if "Q1" in prompt:
                time.sleep(0.01)
                return "D"
            return "C"

        mock_complete_one.side_effect = fake_complete_one

        correct, wrong_cases = evaluate_online_accuracy(
            eval_data=eval_data,
            base_url="http://127.0.0.1:8000",
            model="demo",
            max_tokens=16,
            temperature=0.0,
            concurrency=3,
        )

        self.assertEqual(correct, 2)
        self.assertEqual(len(wrong_cases), 1)
        self.assertEqual(wrong_cases[0]["id"], "q1")
        self.assertEqual(wrong_cases[0]["pred"], "D")
        self.assertEqual(wrong_cases[0]["gold"], "B")
        self.assertEqual(mock_complete_one.call_count, 3)


if __name__ == "__main__":
    unittest.main()
