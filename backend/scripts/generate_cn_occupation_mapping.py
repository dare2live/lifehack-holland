"""Build a local Chinese occupation -> RIASEC bridge.

The script reads the main lifehack DuckDB in read-only mode and writes only to
this project's local holland.duckdb. Mapping rules live in
config/career_riasec_rules.json so labels can be reviewed without code edits.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import duckdb

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from backend.config import CAREER_RIASEC_RULES_PATH, DB_PATH, MAIN_PROJECT_DB_PATH


def _load_rules(path: Path = CAREER_RIASEC_RULES_PATH) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config["rules"] = sorted(config.get("rules", []), key=lambda r: r.get("priority", 0), reverse=True)
    return config


def _existing_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()}


def _combined_source_text(row: dict[str, Any], source_fields: list[str]) -> str:
    parts = []
    for field in source_fields:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(value)
        else:
            parts.append(json.dumps(value, ensure_ascii=False))
    return " ".join(parts).lower()


def tag_occupation(row: dict[str, Any], rules_config: dict[str, Any]) -> dict[str, Any]:
    source_text = _combined_source_text(row, rules_config.get("source_fields", ["occupation_name"]))
    for rule in rules_config.get("rules", []):
        for keyword in rule.get("keywords", []):
            if keyword.lower() in source_text:
                return {
                    "primary_riasec": rule["riasec"],
                    "matched_rule_id": rule["rule_id"],
                    "matched_keyword": keyword,
                    "confidence": float(rule.get("confidence", rules_config.get("matched_confidence", 0.72))),
                    "review_status": rule.get("review_status", rules_config.get("matched_review_status", "needs_review")),
                    "source_text": source_text,
                }
    return {
        "primary_riasec": rules_config.get("default_riasec", "R"),
        "matched_rule_id": "default",
        "matched_keyword": "",
        "confidence": float(rules_config.get("default_confidence", 0.3)),
        "review_status": rules_config.get("default_review_status", "needs_review"),
        "source_text": source_text,
    }


def _fetch_main_occupations(main_db_path: str, rules_config: dict[str, Any]) -> list[dict[str, Any]]:
    if not os.path.exists(main_db_path):
        raise FileNotFoundError(f"Main project DB not found: {main_db_path}")

    con = duckdb.connect(main_db_path, read_only=True)
    try:
        columns = _existing_columns(con, "fa_dim_career_occupation")
        requested = ["occupation_code", "occupation_name", *rules_config.get("source_fields", [])]
        selected = []
        for col in requested:
            if col in columns and col not in selected:
                selected.append(col)
        if "occupation_code" not in selected or "occupation_name" not in selected:
            raise RuntimeError("fa_dim_career_occupation must expose occupation_code and occupation_name")
        rows = con.execute(
            f"SELECT {', '.join(selected)} FROM fa_dim_career_occupation ORDER BY occupation_code"
        ).fetchall()
        return [dict(zip(selected, row)) for row in rows]
    finally:
        con.close()


def build_mapping(
    main_db_path: str = MAIN_PROJECT_DB_PATH,
    local_db_path: str = DB_PATH,
    rules_path: Path = CAREER_RIASEC_RULES_PATH,
) -> dict[str, Any]:
    rules_config = _load_rules(rules_path)
    occupations = _fetch_main_occupations(main_db_path, rules_config)

    local_con = duckdb.connect(local_db_path)
    try:
        local_con.execute("DROP TABLE IF EXISTS cn_occupation_riasec_map")
        local_con.execute(
            """
            CREATE TABLE cn_occupation_riasec_map (
                occupation_code VARCHAR PRIMARY KEY,
                occupation_name VARCHAR,
                primary_riasec VARCHAR,
                matched_rule_id VARCHAR,
                matched_keyword VARCHAR,
                confidence DOUBLE,
                review_status VARCHAR,
                source_version VARCHAR,
                source_text VARCHAR,
                lineage_json VARCHAR,
                mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        counts: dict[str, int] = {}
        for row in occupations:
            tag = tag_occupation(row, rules_config)
            counts[tag["primary_riasec"]] = counts.get(tag["primary_riasec"], 0) + 1
            lineage = {
                "source_project": "lifehack",
                "source_table": "fa_dim_career_occupation",
                "source_pk": row["occupation_code"],
                "read_mode": "duckdb_read_only",
                "rules_file": str(rules_path),
                "rules_version": rules_config.get("version", "unknown"),
                "matched_rule_id": tag["matched_rule_id"],
                "matched_keyword": tag["matched_keyword"],
            }
            local_con.execute(
                """
                INSERT INTO cn_occupation_riasec_map (
                    occupation_code, occupation_name, primary_riasec, matched_rule_id,
                    matched_keyword, confidence, review_status, source_version, source_text,
                    lineage_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row["occupation_code"],
                    row["occupation_name"],
                    tag["primary_riasec"],
                    tag["matched_rule_id"],
                    tag["matched_keyword"],
                    tag["confidence"],
                    tag["review_status"],
                    rules_config.get("version", "unknown"),
                    tag["source_text"],
                    json.dumps(lineage, ensure_ascii=False, sort_keys=True),
                ],
            )
    finally:
        local_con.close()

    return {
        "rows": len(occupations),
        "rules_version": rules_config.get("version"),
        "riasec_counts": dict(sorted(counts.items())),
        "local_table": "cn_occupation_riasec_map",
    }


if __name__ == "__main__":
    summary = build_mapping()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
