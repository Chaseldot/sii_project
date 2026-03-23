from __future__ import annotations

from vllm_14b.engine import EngineConfig, VLLM14BEngine


class VLLM14BLengthAwareV6OfflineEngine(VLLM14BEngine):
    def estimate_input_tokens(self, prompts: list[str]) -> list[int]:
        return self._input_token_lens(prompts)
