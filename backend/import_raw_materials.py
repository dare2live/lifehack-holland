"""Import raw master materials into the local Holland DuckDB.

This module is an offline data-prep utility. It reads source locations from
config files, preserves row-level lineage, and writes only to this project's
local ``holland.duckdb``. Production questions are still created through the
candidate review and seed promotion flow.
"""
from __future__ import annotations

import csv
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    DB_PATH,
    PROJECT_ROOT,
    QUESTION_GENERATION_CONFIG_PATH,
    SOURCE_REGISTRY_CONFIG_PATH,
)


def _project_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _source_file(registry: dict[str, Any], source_key: str, role: str) -> dict[str, Any]:
    source = registry.get("sources", {}).get(source_key)
    if not isinstance(source, dict):
        raise ValueError(f"source_registry missing source: {source_key}")
    for item in source.get("files", []):
        if item.get("role") == role:
            return {
                "source_key": source_key,
                "source_name": source.get("source_name", ""),
                "source_version": source.get("source_version", ""),
                **item,
            }
    raise ValueError(f"source_registry.{source_key} missing file role: {role}")


def _safe_float(raw: str | None) -> float | None:
    if raw in (None, ""):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _lineage(
    *,
    registry_version: str,
    source_file: dict[str, Any],
    source_row_number: int,
    source_row_pk: str,
) -> str:
    return json.dumps(
        {
            "service": "lifehack-holland",
            "lineage_quality": "raw_master_snapshot",
            "source_registry_version": registry_version,
            "source_key": source_file["source_key"],
            "source_name": source_file.get("source_name", ""),
            "source_version": source_file.get("source_version", ""),
            "source_role": source_file.get("role", ""),
            "source_path": source_file.get("output_path", ""),
            "source_url": source_file.get("url", ""),
            "acquisition_mode": source_file.get("acquisition_mode", "download"),
            "source_row_number": source_row_number,
            "source_row_pk": source_row_pk,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _create_run_table(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_material_import_runs (
            run_id VARCHAR PRIMARY KEY,
            source_registry_version VARCHAR,
            question_generation_version VARCHAR,
            imported_tables_json VARCHAR,
            row_counts_json VARCHAR,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
        """
    )


def _reset_raw_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP TABLE IF EXISTS raw_onet_interests")
    con.execute("DROP TABLE IF EXISTS raw_onet_task_statements")
    con.execute("DROP TABLE IF EXISTS raw_ipip_items")
    con.execute(
        """
        CREATE TABLE raw_onet_interests (
            run_id VARCHAR,
            source_key VARCHAR,
            source_name VARCHAR,
            source_version VARCHAR,
            source_role VARCHAR,
            source_path VARCHAR,
            source_row_number INTEGER,
            onet_soc_code VARCHAR,
            element_id VARCHAR,
            element_name VARCHAR,
            scale_id VARCHAR,
            data_value DOUBLE,
            raw_data_value VARCHAR,
            reported_date VARCHAR,
            domain_source VARCHAR,
            raw_row_json VARCHAR,
            lineage_json VARCHAR,
            imported_at TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE raw_onet_task_statements (
            run_id VARCHAR,
            source_key VARCHAR,
            source_name VARCHAR,
            source_version VARCHAR,
            source_role VARCHAR,
            source_path VARCHAR,
            source_row_number INTEGER,
            onet_soc_code VARCHAR,
            task_id VARCHAR,
            task_text VARCHAR,
            task_type VARCHAR,
            incumbents_responding VARCHAR,
            reported_date VARCHAR,
            domain_source VARCHAR,
            raw_row_json VARCHAR,
            lineage_json VARCHAR,
            imported_at TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE raw_ipip_items (
            run_id VARCHAR,
            source_key VARCHAR,
            source_name VARCHAR,
            source_version VARCHAR,
            source_role VARCHAR,
            source_path VARCHAR,
            source_row_number INTEGER,
            item_id VARCHAR,
            item_index INTEGER,
            question_text VARCHAR,
            options_json VARCHAR,
            raw_item_json VARCHAR,
            lineage_json VARCHAR,
            imported_at TIMESTAMP
        )
        """
    )


def _import_onet_interests(
    con: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    registry_version: str,
    source_file: dict[str, Any],
    imported_at: datetime,
) -> int:
    path = _project_path(source_file["output_path"])
    count = 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for source_row_number, row in enumerate(reader, start=2):
            source_row_pk = ":".join(
                [
                    row.get("O*NET-SOC Code", ""),
                    row.get("Element ID", ""),
                    row.get("Scale ID", ""),
                ]
            )
            con.execute(
                """
                INSERT INTO raw_onet_interests (
                    run_id, source_key, source_name, source_version, source_role,
                    source_path, source_row_number, onet_soc_code, element_id,
                    element_name, scale_id, data_value, raw_data_value,
                    reported_date, domain_source, raw_row_json, lineage_json,
                    imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    source_file["source_key"],
                    source_file.get("source_name", ""),
                    source_file.get("source_version", ""),
                    source_file.get("role", ""),
                    source_file.get("output_path", ""),
                    source_row_number,
                    row.get("O*NET-SOC Code", ""),
                    row.get("Element ID", ""),
                    row.get("Element Name", ""),
                    row.get("Scale ID", ""),
                    _safe_float(row.get("Data Value")),
                    row.get("Data Value", ""),
                    row.get("Date", ""),
                    row.get("Domain Source", ""),
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                    _lineage(
                        registry_version=registry_version,
                        source_file=source_file,
                        source_row_number=source_row_number,
                        source_row_pk=source_row_pk,
                    ),
                    imported_at,
                ],
            )
            count += 1
    return count


def _import_onet_tasks(
    con: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    registry_version: str,
    source_file: dict[str, Any],
    imported_at: datetime,
) -> int:
    path = _project_path(source_file["output_path"])
    count = 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for source_row_number, row in enumerate(reader, start=2):
            source_row_pk = ":".join([row.get("O*NET-SOC Code", ""), row.get("Task ID", "")])
            con.execute(
                """
                INSERT INTO raw_onet_task_statements (
                    run_id, source_key, source_name, source_version, source_role,
                    source_path, source_row_number, onet_soc_code, task_id,
                    task_text, task_type, incumbents_responding, reported_date,
                    domain_source, raw_row_json, lineage_json, imported_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    source_file["source_key"],
                    source_file.get("source_name", ""),
                    source_file.get("source_version", ""),
                    source_file.get("role", ""),
                    source_file.get("output_path", ""),
                    source_row_number,
                    row.get("O*NET-SOC Code", ""),
                    row.get("Task ID", ""),
                    row.get("Task", ""),
                    row.get("Task Type", ""),
                    row.get("Incumbents Responding", ""),
                    row.get("Date", ""),
                    row.get("Domain Source", ""),
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                    _lineage(
                        registry_version=registry_version,
                        source_file=source_file,
                        source_row_number=source_row_number,
                        source_row_pk=source_row_pk,
                    ),
                    imported_at,
                ],
            )
            count += 1
    return count


def _import_ipip_items(
    con: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    registry_version: str,
    source_file: dict[str, Any],
    imported_at: datetime,
) -> int:
    path = _project_path(source_file["output_path"])
    data = _load_json(path)
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError(f"{path} must contain a questions list")

    count = 0
    for idx, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: questions[{idx}] must be an object")
        item_id = str(item.get("item_id") or f"MBTI_88_{idx}")
        options = item.get("selections", [])
        con.execute(
            """
            INSERT INTO raw_ipip_items (
                run_id, source_key, source_name, source_version, source_role,
                source_path, source_row_number, item_id, item_index,
                question_text, options_json, raw_item_json, lineage_json,
                imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                source_file["source_key"],
                source_file.get("source_name", ""),
                source_file.get("source_version", ""),
                source_file.get("role", ""),
                source_file.get("output_path", ""),
                idx,
                item_id,
                idx,
                item.get("title", ""),
                json.dumps(options, ensure_ascii=False, sort_keys=True),
                json.dumps(item, ensure_ascii=False, sort_keys=True),
                _lineage(
                    registry_version=registry_version,
                    source_file=source_file,
                    source_row_number=idx,
                    source_row_pk=item_id,
                ),
                imported_at,
            ],
        )
        count += 1
    return count


def import_raw_materials(
    *,
    db_path: str = DB_PATH,
    source_registry_path: Path = SOURCE_REGISTRY_CONFIG_PATH,
    question_config_path: Path = QUESTION_GENERATION_CONFIG_PATH,
) -> dict[str, Any]:
    registry = _load_json(source_registry_path)
    question_config = _load_json(question_config_path)
    registry_version = str(registry.get("version", "unknown"))
    question_generation_version = str(question_config.get("version", "unknown"))
    run_id = str(uuid.uuid4())
    started_at = datetime.utcnow()
    imported_at = datetime.utcnow()

    onet_interests = _source_file(registry, "onet_database_text", "interests")
    onet_tasks = _source_file(registry, "onet_database_text", "task_statements")
    ipip_items = _source_file(registry, "ipip_jungian_seed", "jungian_item_seed")

    con = duckdb.connect(db_path)
    try:
        _create_run_table(con)
        _reset_raw_tables(con)
        row_counts = {
            "raw_onet_interests": _import_onet_interests(
                con,
                run_id=run_id,
                registry_version=registry_version,
                source_file=onet_interests,
                imported_at=imported_at,
            ),
            "raw_onet_task_statements": _import_onet_tasks(
                con,
                run_id=run_id,
                registry_version=registry_version,
                source_file=onet_tasks,
                imported_at=imported_at,
            ),
            "raw_ipip_items": _import_ipip_items(
                con,
                run_id=run_id,
                registry_version=registry_version,
                source_file=ipip_items,
                imported_at=imported_at,
            ),
        }
        imported_tables = list(row_counts.keys())
        finished_at = datetime.utcnow()
        con.execute(
            """
            INSERT INTO raw_material_import_runs (
                run_id, source_registry_version, question_generation_version,
                imported_tables_json, row_counts_json, started_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                registry_version,
                question_generation_version,
                json.dumps(imported_tables, ensure_ascii=False, sort_keys=True),
                json.dumps(row_counts, ensure_ascii=False, sort_keys=True),
                started_at,
                finished_at,
            ],
        )
    finally:
        con.close()

    return {
        "run_id": run_id,
        "source_registry_version": registry_version,
        "question_generation_version": question_generation_version,
        "row_counts": row_counts,
        "tables": imported_tables,
    }


if __name__ == "__main__":
    summary = import_raw_materials()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
