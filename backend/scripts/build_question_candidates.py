"""CLI for building reviewed-before-use SJT question candidates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.config import GENERATED_DIR, QUESTION_GENERATION_CONFIG_PATH
from backend.question_candidates import write_candidate_pool


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(QUESTION_GENERATION_CONFIG_PATH))
    parser.add_argument("--output", default=str(GENERATED_DIR / "question_candidates.json"))
    args = parser.parse_args()

    pool = write_candidate_pool(Path(args.output), Path(args.config))
    summary = {
        "output": args.output,
        "version": pool["version"],
        "status": pool["status"],
        "counts": pool["counts"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
