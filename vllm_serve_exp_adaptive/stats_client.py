from __future__ import annotations

import argparse
import json
import urllib.request

from .metrics import save_json


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch adaptive proxy scheduler stats")
    parser.add_argument("--base_url", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    with urllib.request.urlopen(f"{args.base_url}/scheduler_stats", timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if args.output:
        save_json(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
