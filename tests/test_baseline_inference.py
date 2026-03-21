import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "baseline" / "baseline_inference.py"


def load_module():
    spec = importlib.util.spec_from_file_location("baseline_inference", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BaselineInferenceRenderResultTest(unittest.TestCase):
    def test_render_result_uses_ttft_ms_key(self):
        module = load_module()
        result = {
            "prompt": "test prompt",
            "output": "test output",
            "input_tokens": 10,
            "output_tokens": 20,
            "total_latency_ms": 321.0,
            "ttft_ms": 321.0,
            "throughput_tps": 62.3,
        }

        rendered = module.render_result(result, peak_gpu_mem_gb=15.021)

        self.assertIn("TTFT (近似)", rendered)
        self.assertIn("321.0", rendered)
        self.assertIn("15.021 GB", rendered)


if __name__ == "__main__":
    unittest.main()
