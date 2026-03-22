import unittest
from unittest.mock import patch

from vllm_serve_exp.monitor import query_vllm_metrics


class FakeResponse:
    def __init__(self, text: str):
        self._text = text

    def read(self):
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class VLLMServeExpMonitorTest(unittest.TestCase):
    @patch("vllm_serve_exp.monitor.urllib.request.urlopen")
    def test_query_vllm_metrics_supports_labeled_prometheus_metrics(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(
            "\n".join(
                [
                    '# HELP vllm:num_requests_running Number of requests in model execution batches.',
                    '# TYPE vllm:num_requests_running gauge',
                    'vllm:num_requests_running{engine="0",model_name="demo"} 2.0',
                    'vllm:num_requests_waiting{engine="0",model_name="demo"} 1.0',
                    'vllm:kv_cache_usage_perc{engine="0",model_name="demo"} 0.42',
                ]
            )
        )

        metrics = query_vllm_metrics("http://127.0.0.1:8000")

        self.assertEqual(metrics["num_requests_running"], 2.0)
        self.assertEqual(metrics["num_requests_waiting"], 1.0)
        self.assertEqual(metrics["kv_cache_usage_perc"], 0.42)


if __name__ == "__main__":
    unittest.main()
