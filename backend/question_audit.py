"""Audit question-source lineage before candidates or seed items are used."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT, QUESTION_GENERATION_CONFIG_PATH
from backend.question_candidates import build_candidate_pool, load_generation_config


def _project_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def audit_candidate_pool(config_path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    pool = build_candidate_pool(config_path)
    errors: list[str] = []
    warnings: list[str] = []

    counts = pool.get("counts", {})
    if counts.get("total", 0) <= 0:
        errors.append("candidate_pool_empty")
    if not pool.get("source_counts", {}).get("onet"):
        errors.append("source_counts_onet_missing")
    if not pool.get("source_counts", {}).get("ipip"):
        errors.append("source_counts_ipip_missing")

    candidate_ids: set[str] = set()
    for candidate in pool.get("candidates", []):
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            errors.append("candidate_id_missing")
            continue
        if candidate_id in candidate_ids:
            errors.append(f"{candidate_id}:duplicate_candidate_id")
        candidate_ids.add(candidate_id)

        for field in ("source", "source_version", "mother_source", "mother_id", "transform_level", "review_status"):
            if not candidate.get(field):
                errors.append(f"{candidate_id}:{field}_missing")
        if candidate.get("review_status") == "approved":
            errors.append(f"{candidate_id}:candidate_pool_must_not_be_approved")
        if not isinstance(candidate.get("lineage"), dict) or not candidate["lineage"]:
            errors.append(f"{candidate_id}:lineage_missing")
        if not candidate.get("review_priority"):
            warnings.append(f"{candidate_id}:review_priority_missing")
        if "lineage_ready" not in candidate.get("quality_flags", []):
            warnings.append(f"{candidate_id}:lineage_ready_flag_missing")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
        "source_counts": pool.get("source_counts", {}),
    }


def audit_seed_files(config_path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    config = load_generation_config(config_path)
    item_paths = config.get("production_seed", {}).get("item_files", [])
    rule_paths = config.get("production_seed", {}).get("rule_files", [])
    errors: list[str] = []
    warnings: list[str] = []
    item_count = 0
    rule_count = 0
    rule_records: list[dict[str, Any]] = []
    verification_only_ids: set[str] = set()

    for path in rule_paths:
        records = json.loads(_project_path(path).read_text(encoding="utf-8"))
        rule_records.extend(records)
        for rule in records:
            if rule.get("verify_q_id"):
                verification_only_ids.add(str(rule["verify_q_id"]))

    for path in item_paths:
        records = json.loads(_project_path(path).read_text(encoding="utf-8"))
        for item in records:
            item_count += 1
            q_id = str(item.get("q_id") or "")
            if not q_id:
                errors.append(f"{path}:item_q_id_missing")
                continue
            for field in ("mother_source", "mother_id", "mechanism", "text"):
                if not item.get(field):
                    errors.append(f"{q_id}:{field}_missing")
            options = item.get("options")
            if not isinstance(options, list) or len(options) < 2:
                errors.append(f"{q_id}:at_least_two_options_required")
                continue
            for option in options:
                option_id = f"{q_id}:{option.get('val', '')}"
                if not option.get("text"):
                    errors.append(f"{option_id}:option_text_missing")
                if not option.get("weights"):
                    if q_id in verification_only_ids:
                        warnings.append(f"{option_id}:verification_option_has_no_direct_score")
                    else:
                        errors.append(f"{option_id}:weights_missing")
                if not option.get("lineage"):
                    warnings.append(f"{option_id}:option_lineage_falls_back_to_item")

    for rule in rule_records:
        rule_count += 1
        rule_id = str(rule.get("rule_id") or "")
        if not rule_id:
            errors.append("rule_id_missing")
            continue
        for field in ("trigger_q_id", "trigger_option", "verify_q_id", "expected_option", "penalty_dimension", "penalty_weight"):
            if rule.get(field) in ("", None):
                errors.append(f"{rule_id}:{field}_missing")
        if not rule.get("lineage"):
            warnings.append(f"{rule_id}:rule_lineage_falls_back_to_seed")

    return {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "items": item_count,
            "rules": rule_count,
        },
    }


def audit_all(config_path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    candidate_audit = audit_candidate_pool(config_path)
    seed_audit = audit_seed_files(config_path)
    errors = candidate_audit["errors"] + seed_audit["errors"]
    return {
        "status": "pass" if not errors else "fail",
        "candidate_pool": candidate_audit,
        "production_seed": seed_audit,
    }
