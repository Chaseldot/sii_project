import unittest
from itertools import groupby


from vllm_14b_length_aware_v6_offline.planner import OfflineLengthAwarePlanner, PlannerConfig


class OfflineLengthAwarePlannerTest(unittest.TestCase):
    def test_planner_preserves_all_requests_and_batch_sorting(self):
        planner = OfflineLengthAwarePlanner(
            PlannerConfig(
                policy="length_aware_v6",
                batch_size=3,
                lookahead_size=6,
                short_threshold_tokens=100,
                sort_within_batch=True,
            )
        )
        prompts = ["a", "b", "c", "d", "e", "f"]
        estimated_tokens = [60, 10, 30, 220, 80, 40]
        requests = planner.build_requests(prompts, estimated_tokens)

        batches = planner.plan(requests)
        flattened = [item.original_index for batch in batches for item in batch]

        self.assertEqual(sorted(flattened), [0, 1, 2, 3, 4, 5])
        self.assertEqual(len(flattened), 6)
        for batch in batches:
            batch_tokens = [item.estimated_tokens for item in batch]
            self.assertEqual(batch_tokens, sorted(batch_tokens))

    def test_max_consecutive_short_is_enforced_when_long_exists(self):
        planner = OfflineLengthAwarePlanner(
            PlannerConfig(
                policy="length_aware_v6",
                batch_size=1,
                lookahead_size=8,
                short_threshold_tokens=100,
                max_consecutive_short=2,
                sort_within_batch=False,
            )
        )
        prompts = [f"p{i}" for i in range(8)]
        estimated_tokens = [20, 30, 40, 200, 25, 35, 220, 45]
        requests = planner.build_requests(prompts, estimated_tokens)

        batches = planner.plan(requests)
        order = [batch[0].bucket for batch in batches]

        self.assertEqual(order[:3], ["short", "short", "long"])
        max_short_run = max(
            (sum(1 for _ in group) for bucket, group in groupby(order) if bucket == "short"),
            default=0,
        )
        self.assertLessEqual(max_short_run, 2)

    def test_snapshot_contains_expected_fields(self):
        planner = OfflineLengthAwarePlanner(
            PlannerConfig(
                policy="fifo",
                batch_size=2,
                lookahead_size=4,
                short_threshold_tokens=50,
            )
        )
        requests = planner.build_requests(
            prompts=["x", "y", "z"],
            estimated_tokens=[10, 100, 20],
        )
        planner.plan(requests)
        snapshot = planner.snapshot()

        self.assertEqual(snapshot["planner_policy"], "fifo")
        self.assertEqual(snapshot["planner_total_requests"], 3)
        self.assertEqual(snapshot["planner_total_selected"], 3)
        self.assertEqual(snapshot["planner_total_batches"], 2)


if __name__ == "__main__":
    unittest.main()
