"""Review and promote SJT question candidates.

Candidates are source material. Only rows explicitly marked approved in a
review CSV can be promoted into production-ready seed item JSON.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from backend.config import QUESTION_GENERATION_CONFIG_PATH
from backend.question_candidates import build_candidate_pool, load_generation_config


def _candidate_raw_text(candidate: dict[str, Any]) -> str:
    if candidate.get("raw_task"):
        return candidate["raw_task"]
    raw_options = " / ".join(candidate.get("raw_options", []))
    return f"{candidate.get('raw_title', '')} {raw_options}".strip()


def _review_fields(config: dict[str, Any]) -> list[str]:
    return config["review"]["batch_fields"]


def write_review_batch(
    output_path: Path,
    *,
    limit: int = 50,
    source: str | None = None,
    config_path: Path = QUESTION_GENERATION_CONFIG_PATH,
) -> dict[str, Any]:
    config = load_generation_config(config_path)
    pool = build_candidate_pool(config_path)
    rows = []
    for candidate in pool["candidates"]:
        if source and candidate.get("source") != source:
            continue
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "source": candidate["source"],
                "mother_source": candidate["mother_source"],
                "mother_id": candidate["mother_id"],
                "source_version": candidate.get("source_version", ""),
                "transform_level": candidate.get("transform_level", ""),
                "dimension_code": candidate.get("dimension_code", ""),
                "inherited_weight": candidate.get("inherited_weight", ""),
                "review_priority": candidate.get("review_priority", ""),
                "quality_flags_json": json.dumps(
                    candidate.get("quality_flags", []),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "raw_text": _candidate_raw_text(candidate),
                "scenario_shell": candidate.get("scenario_shell", ""),
                "draft_prompt": candidate.get("draft_prompt", ""),
                "candidate_lineage_json": json.dumps(
                    candidate.get("lineage", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "review_status": candidate.get("review_status", config["output"]["candidate_status"]),
                "approved_q_id": "",
                "scenario_text": "",
                "option_a_text": "",
                "option_a_weights_json": "",
                "option_a_lineage_json": "",
                "option_b_text": "",
                "option_b_weights_json": "",
                "option_b_lineage_json": "",
                "option_c_text": "",
                "option_c_weights_json": "",
                "option_c_lineage_json": "",
                "review_notes": "",
            }
        )
        if len(rows) >= limit:
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_review_fields(config))
        writer.writeheader()
        writer.writerows(rows)
    return {"output": str(output_path), "rows": len(rows), "source": source or "all"}


def _parse_weights(raw: str, *, field: str, candidate_id: str) -> list[list[Any]]:
    if not raw.strip():
        raise ValueError(f"{candidate_id}: {field} is required for approved options")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{candidate_id}: {field} must be valid JSON") from exc
    if not isinstance(value, list) or not value:
        raise ValueError(f"{candidate_id}: {field} must be a non-empty list")
    parsed = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"{candidate_id}: {field} entries must be [dimension_code, weight]")
        dimension_code, weight = item
        if not isinstance(dimension_code, str) or not dimension_code:
            raise ValueError(f"{candidate_id}: {field} dimension_code is required")
        parsed.append([dimension_code, float(weight)])
    return parsed


def _parse_option_lineage(raw: str, *, field: str, candidate_id: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{candidate_id}: {field} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{candidate_id}: {field} must be a JSON object")
    return value


def _default_option_lineage(
    *,
    row: dict[str, str],
    candidate: dict[str, Any],
    option_val: str,
    weights: list[list[Any]],
) -> dict[str, Any]:
    return {
        "lineage_quality": "candidate_option_review",
        "candidate_id": row["candidate_id"],
        "source": candidate["source"],
        "source_version": candidate["source_version"],
        "mother_source": candidate["mother_source"],
        "mother_id": candidate["mother_id"],
        "transform_level": candidate.get("transform_level", ""),
        "review_status": row.get("review_status", ""),
        "question_id": row.get("approved_q_id", "").strip(),
        "option_val": option_val,
        "scoring_role": "direct_score",
        "raw_text": _candidate_raw_text(candidate),
        "weights": weights,
        "candidate_lineage": candidate.get("lineage", {}),
        "review_notes": row.get("review_notes", ""),
    }


def _promote_row(row: dict[str, str], candidate: dict[str, Any]) -> dict[str, Any]:
    candidate_id = row["candidate_id"]
    q_id = row.get("approved_q_id", "").strip()
    scenario_text = row.get("scenario_text", "").strip()
    if not q_id:
        raise ValueError(f"{candidate_id}: approved_q_id is required")
    if not scenario_text:
        raise ValueError(f"{candidate_id}: scenario_text is required")

    options = []
    for option_val, text_field, weight_field, lineage_field in [
        ("A", "option_a_text", "option_a_weights_json", "option_a_lineage_json"),
        ("B", "option_b_text", "option_b_weights_json", "option_b_lineage_json"),
        ("C", "option_c_text", "option_c_weights_json", "option_c_lineage_json"),
    ]:
        option_text = row.get(text_field, "").strip()
        if not option_text:
            continue
        weights = _parse_weights(row.get(weight_field, ""), field=weight_field, candidate_id=candidate_id)
        lineage = _parse_option_lineage(row.get(lineage_field, ""), field=lineage_field, candidate_id=candidate_id)
        default_lineage = _default_option_lineage(
            row=row,
            candidate=candidate,
            option_val=option_val,
            weights=weights,
        )
        options.append(
            {
                "val": option_val,
                "text": option_text,
                "weights": weights,
                "lineage": {**default_lineage, **lineage},
            }
        )
    if len(options) < 2:
        raise ValueError(f"{candidate_id}: approved items need at least two options")

    return {
        "q_id": q_id,
        "mother_source": candidate["mother_source"],
        "mother_id": candidate["mother_id"],
        "mechanism": f"{candidate.get('transform_level', 'L1_candidate_seed')}:{candidate_id}",
        "text": scenario_text,
        "options": options,
        "lineage": {
            "candidate_id": candidate_id,
            "source": candidate["source"],
            "source_version": candidate["source_version"],
            "raw_text": _candidate_raw_text(candidate),
            "candidate_lineage": candidate.get("lineage", {}),
            "review_notes": row.get("review_notes", ""),
        },
    }


def promote_review_batch(
    review_csv: Path,
    output_items_path: Path,
    *,
    config_path: Path = QUESTION_GENERATION_CONFIG_PATH,
) -> dict[str, Any]:
    config = load_generation_config(config_path)
    allowed_statuses = set(config["review"]["allowed_statuses"])
    approved_status = config["review"]["approved_status"]
    pool = build_candidate_pool(config_path)
    candidates = {candidate["candidate_id"]: candidate for candidate in pool["candidates"]}
    approved_items = []
    status_counts: dict[str, int] = {}

    with open(review_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidate_id = row.get("candidate_id", "")
            if candidate_id not in candidates:
                raise ValueError(f"Unknown candidate_id: {candidate_id}")
            status = row.get("review_status", "").strip() or config["output"]["candidate_status"]
            if status not in allowed_statuses:
                raise ValueError(f"{candidate_id}: invalid review_status {status}")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == approved_status:
                approved_items.append(_promote_row(row, candidates[candidate_id]))

    output_items_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_items_path, "w", encoding="utf-8") as f:
        json.dump(approved_items, f, ensure_ascii=False, indent=2)

    return {
        "review_csv": str(review_csv),
        "output_items": str(output_items_path),
        "approved_items": len(approved_items),
        "status_counts": dict(sorted(status_counts.items())),
    }
