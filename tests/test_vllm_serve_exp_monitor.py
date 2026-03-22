import unittest
from unittest.mock import patch

from vllm_serve_exp.monitor import OnlineExperimentMonitor, query_vllm_metrics


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

    def test_summary_keeps_key_metrics_in_expected_order(self):
        monitor = OnlineExperimentMonitor(base_url="http://127.0.0.1:8000")
        monitor.gpu_mem_samples_gb = [70.0, 72.0, 74.0]
        monitor.gpu_total_mem_gb = 80.0
        monitor.gpu_mem_utilization_samples = [0.875, 0.9, 0.925]
        monitor.kv_cache_usage_samples = [0.10, 0.25, 0.30]
        monitor.waiting_request_samples = [0.0, 1.0, 2.0]
        monitor.running_request_samples = [4.0, 8.0, 16.0]
        monitor.cpu_cache_usage_samples = [0.05, 0.10]

        summary = monitor.summary()

        self.assertEqual(
            list(summary.keys()),
            [
                "avg_gpu_mem_gb",
                "peak_gpu_mem_gb",
                "avg_gpu_mem_utilization_perc",
                "peak_gpu_mem_utilization_perc",
                "avg_kv_cache_usage_perc",
                "max_kv_cache_usage_perc",
                "avg_num_requests_running",
                "max_num_requests_running",
                "avg_num_requests_waiting",
                "max_num_requests_waiting",
                "gpu_total_mem_gb",
                "initial_gpu_mem_gb",
                "final_gpu_mem_gb",
                "monitor_sample_interval_sec",
                "monitor_gpu_samples",
                "monitor_kv_samples",
                "avg_cpu_cache_usage_perc",
                "max_cpu_cache_usage_perc",
                "monitor_cpu_cache_samples",
            ],
        )
        self.assertNotIn("min_gpu_mem_gb", summary)
        self.assertNotIn("min_kv_cache_usage_perc", summary)
        self.assertNotIn("min_num_requests_running", summary)


if __name__ == "__main__":
    unittest.main()
