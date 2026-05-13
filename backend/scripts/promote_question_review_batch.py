"""CLI for promoting approved SJT review rows to seed item JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.config import GENERATED_DIR, QUESTION_GENERATION_CONFIG_PATH
from backend.question_review import promote_review_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_csv")
    parser.add_argument("--config", default=str(QUESTION_GENERATION_CONFIG_PATH))
    parser.add_argument("--output-items", default=str(GENERATED_DIR / "promoted_question_items.json"))
    args = parser.parse_args()

    summary = promote_review_batch(
        Path(args.review_csv),
        Path(args.output_items),
        config_path=Path(args.config),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

