"""Review workflow for the Chinese occupation -> RIASEC bridge.

The generator intentionally marks rule-based mappings as ``needs_review``.
This module creates a review CSV and promotes only explicit approved rows back
into the local Holland DuckDB, keeping the core handoff gate auditable.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from backend.config import DB_PATH


RIASEC_CODES = {"R", "I", "A", "S", "E", "C"}
REVIEW_FIELDS = [
    "occupation_code",
    "occupation_name",
    "current_riasec",
    "matched_rule_id",
    "matched_keyword",
    "confidence",
    "review_status",
    "source_version",
    "source_text",
    "review_decision",
    "reviewed_riasec",
    "review_notes",
    "reviewer",
]


def _table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {
        row[1]
        for row in con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    }


def write_review_batch(
    output_path: Path,
    *,
    db_path: str = DB_PATH,
    limit: int | None = None,
) -> dict[str, Any]:
    output_path = Path(output_path)
    con = duckdb.connect(db_path, read_only=True)
    try:
        rows = con.execute(
            """
            SELECT
                occupation_code,
                occupation_name,
                primary_riasec,
                matched_rule_id,
                matched_keyword,
                confidence,
                review_status,
                source_version,
                source_text
            FROM cn_occupation_riasec_map
            WHERE lower(coalesce(review_status, '')) NOT LIKE 'approved%'
            ORDER BY confidence ASC, occupation_code
            """
        ).fetchall()
    finally:
        con.close()

    if limit is not None:
        rows = rows[:limit]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "occupation_code": row[0],
                "occupation_name": row[1],
                "current_riasec": row[2],
                "matched_rule_id": row[3],
                "matched_keyword": row[4],
                "confidence": row[5],
                "review_status": row[6],
                "source_version": row[7],
                "source_text": row[8],
                "review_decision": "todo",
                "reviewed_riasec": row[2],
                "review_notes": "",
                "reviewer": "",
            })

    return {
        "status": "written",
        "rows": len(rows),
        "output_path": str(output_path),
    }


def promote_review_batch(
    input_path: Path,
    *,
    db_path: str = DB_PATH,
    approved_status: str = "approved_manual",
) -> dict[str, Any]:
    input_path = Path(input_path)
    promoted = 0
    skipped = 0
    errors: list[dict[str, str]] = []

    with input_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    con = duckdb.connect(db_path)
    try:
        columns = _table_columns(con, "cn_occupation_riasec_map")
        has_lineage = "lineage_json" in columns
        for idx, row in enumerate(rows, start=2):
            decision = str(row.get("review_decision", "")).strip().lower()
            if decision not in {"approved", "approve"}:
                skipped += 1
                continue
            occupation_code = str(row.get("occupation_code", "")).strip()
            reviewed_riasec = str(row.get("reviewed_riasec") or row.get("current_riasec") or "").strip().upper()
            reviewer = str(row.get("reviewer", "")).strip()
            if not occupation_code:
                errors.append({"line": str(idx), "error": "missing occupation_code"})
                continue
            if reviewed_riasec not in RIASEC_CODES:
                errors.append({"line": str(idx), "occupation_code": occupation_code, "error": "invalid reviewed_riasec"})
                continue
            if not reviewer:
                errors.append({"line": str(idx), "occupation_code": occupation_code, "error": "missing reviewer"})
                continue

            lineage_patch = {
                "occupation_review": {
                    "reviewed_at": datetime.utcnow().replace(microsecond=0).isoformat(),
                    "reviewer": reviewer,
                    "review_decision": decision,
                    "reviewed_riasec": reviewed_riasec,
                    "review_notes": str(row.get("review_notes", "")).strip(),
                    "review_batch": str(input_path),
                }
            }
            if has_lineage:
                current = con.execute(
                    """
                    SELECT lineage_json
                    FROM cn_occupation_riasec_map
                    WHERE occupation_code = ?
                    """,
                    [occupation_code],
                ).fetchone()
                existing_lineage = {}
                if current and current[0]:
                    try:
                        existing_lineage = json.loads(current[0])
                    except json.JSONDecodeError:
                        existing_lineage = {"previous_lineage_raw": current[0]}
                existing_lineage.update(lineage_patch)
                con.execute(
                    """
                    UPDATE cn_occupation_riasec_map
                    SET primary_riasec = ?,
                        review_status = ?,
                        confidence = greatest(coalesce(confidence, 0), 0.85),
                        lineage_json = ?
                    WHERE occupation_code = ?
                    """,
                    [reviewed_riasec, approved_status, json.dumps(existing_lineage, ensure_ascii=False, sort_keys=True), occupation_code],
                )
            else:
                con.execute(
                    """
                    UPDATE cn_occupation_riasec_map
                    SET primary_riasec = ?,
                        review_status = ?,
                        confidence = greatest(coalesce(confidence, 0), 0.85)
                    WHERE occupation_code = ?
                    """,
                    [reviewed_riasec, approved_status, occupation_code],
                )
            exists_after_update = con.execute(
                """
                SELECT COUNT(*)
                FROM cn_occupation_riasec_map
                WHERE occupation_code = ?
                  AND lower(coalesce(review_status, '')) LIKE 'approved%'
                """,
                [occupation_code],
            ).fetchone()[0]
            promoted += 1 if exists_after_update else 0
    finally:
        con.close()

    return {
        "status": "ok" if not errors else "has_errors",
        "promoted_rows": promoted,
        "skipped_rows": skipped,
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review Chinese occupation RIASEC bridge mappings")
    sub = parser.add_subparsers(dest="command", required=True)

    write_parser = sub.add_parser("write-batch")
    write_parser.add_argument("--output", required=True)
    write_parser.add_argument("--db-path", default=DB_PATH)
    write_parser.add_argument("--limit", type=int)

    promote_parser = sub.add_parser("promote-batch")
    promote_parser.add_argument("--input", required=True)
    promote_parser.add_argument("--db-path", default=DB_PATH)

    args = parser.parse_args()
    if args.command == "write-batch":
        summary = write_review_batch(Path(args.output), db_path=args.db_path, limit=args.limit)
    else:
        summary = promote_review_batch(Path(args.input), db_path=args.db_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
