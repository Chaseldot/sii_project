from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHORT_FILE = ROOT / "baseline" / "prompts.jsonl"
DEFAULT_LONG_FILE = ROOT / "baseline" / "test_prompts.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def save_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Build mixed short/long prompt workload")
    parser.add_argument("--short_file", type=str, default=str(DEFAULT_SHORT_FILE))
    parser.add_argument("--long_file", type=str, default=str(DEFAULT_LONG_FILE))
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument(
        "--mode",
        type=str,
        default="preserve_short",
        choices=["preserve_short", "fixed_total"],
        help="preserve_short: 保留全部 short 样本，再按比例采样 long；fixed_total: 固定总数并按比例采样。",
    )
    parser.add_argument(
        "--short_ratio",
        type=float,
        default=0.3,
        help="short 样本比例，例如 0.3 表示 short:long 约为 3:7。",
    )
    parser.add_argument(
        "--total_samples",
        type=int,
        default=0,
        help="mode=fixed_total 时生效；0 表示自动退回 preserve_short 逻辑。",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="是否打散 short/long 顺序；建议在线服务实验打开。",
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def build_rows(
    short_items: list[dict],
    long_items: list[dict],
    mode: str,
    short_ratio: float,
    total_samples: int,
    shuffle: bool,
    seed: int,
) -> list[dict]:
    if not 0 < short_ratio < 1:
        raise ValueError("short_ratio must be between 0 and 1")

    rng = random.Random(seed)
    short_rows = []
    long_rows = []

    if mode == "fixed_total" and total_samples > 0:
        short_target = min(len(short_items), int(round(total_samples * short_ratio)))
        long_target = min(len(long_items), max(0, total_samples - short_target))
    else:
        short_target = len(short_items)
        long_target = min(
            len(long_items),
            int(math.ceil(short_target * (1 - short_ratio) / short_ratio)),
        )

    chosen_short = rng.sample(short_items, k=short_target)
    chosen_long = rng.sample(long_items, k=long_target)

    for idx, item in enumerate(chosen_short, start=1):
        prompt = item["prompt"] if isinstance(item, dict) else str(item)
        short_rows.append(
            {
                "id": f"short_{idx}",
                "source_id": item.get("id", idx) if isinstance(item, dict) else idx,
                "source_prompt_file": Path(DEFAULT_SHORT_FILE).name,
                "length_bucket": "short",
                "prompt_chars": len(prompt),
                "prompt": prompt,
            }
        )

    for idx, item in enumerate(chosen_long, start=1):
        prompt = item["prompt"] if isinstance(item, dict) else str(item)
        long_rows.append(
            {
                "id": f"long_{idx}",
                "source_id": item.get("id", idx) if isinstance(item, dict) else idx,
                "source_prompt_file": Path(DEFAULT_LONG_FILE).name,
                "length_bucket": "long",
                "prompt_chars": len(prompt),
                "prompt": prompt,
            }
        )

    rows = short_rows + long_rows
    if shuffle:
        rng.shuffle(rows)

    for idx, row in enumerate(rows, start=1):
        row["mixed_id"] = idx

    return rows


def main():
    args = parse_args()
    short_file = Path(args.short_file)
    long_file = Path(args.long_file)
    output = Path(args.output)

    short_items = load_jsonl(short_file)
    long_items = load_jsonl(long_file)
    rows = build_rows(
        short_items=short_items,
        long_items=long_items,
        mode=args.mode,
        short_ratio=args.short_ratio,
        total_samples=args.total_samples,
        shuffle=args.shuffle,
        seed=args.seed,
    )
    save_jsonl(output, rows)

    short_count = sum(1 for row in rows if row["length_bucket"] == "short")
    long_count = len(rows) - short_count
    print(f"[INFO] short_file={short_file}")
    print(f"[INFO] long_file={long_file}")
    print(f"[INFO] output={output}")
    print(f"[INFO] short_count={short_count}")
    print(f"[INFO] long_count={long_count}")
    print(f"[INFO] total_count={len(rows)}")


if __name__ == "__main__":
    main()
