"""CLI for exporting SJT candidate review batches."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.config import GENERATED_DIR, QUESTION_GENERATION_CONFIG_PATH
from backend.question_review import write_review_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(QUESTION_GENERATION_CONFIG_PATH))
    parser.add_argument("--output", default=str(GENERATED_DIR / "question_review_batch.csv"))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--source", choices=["onet", "ipip"], default=None)
    args = parser.parse_args()

    summary = write_review_batch(
        Path(args.output),
        limit=args.limit,
        source=args.source,
        config_path=Path(args.config),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

