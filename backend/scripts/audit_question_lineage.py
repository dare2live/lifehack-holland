"""CLI for auditing Holland question-source lineage gates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.config import QUESTION_GENERATION_CONFIG_PATH
from backend.question_audit import audit_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(QUESTION_GENERATION_CONFIG_PATH))
    args = parser.parse_args()

    report = audit_all(Path(args.config))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
