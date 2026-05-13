"""Build lineage-preserving SJT question candidates from master sources."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from backend.config import PROJECT_ROOT, QUESTION_GENERATION_CONFIG_PATH


def load_generation_config(path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _project_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def _load_onet_interest_scores(config: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    onet_config = config["onet"]
    dimension_codes = onet_config["dimension_codes"]
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    stats = {
        "interest_rows_scanned": 0,
        "interest_rows_used": 0,
        "interest_occupations": 0,
        "eligible_occupations": 0,
        "eligible_occupations_by_dimension": {},
    }

    with open(_project_path(onet_config["interests_file"]), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            stats["interest_rows_scanned"] += 1
            if row.get("Scale ID") != onet_config.get("scale_id", "OI"):
                continue
            element_name = row.get("Element Name", "")
            dimension_code = dimension_codes.get(element_name)
            if not dimension_code:
                continue
            try:
                value = float(row.get("Data Value", "0"))
            except ValueError:
                continue
            scores[row["O*NET-SOC Code"]][dimension_code] = value
            stats["interest_rows_used"] += 1

    min_score = float(onet_config.get("min_top_interest_score", 0))
    top_scores = {}
    stats["interest_occupations"] = len(scores)
    by_dimension: dict[str, int] = defaultdict(int)
    for soc_code, dim_scores in scores.items():
        if not dim_scores:
            continue
        dimension_code, value = max(dim_scores.items(), key=lambda item: item[1])
        if value >= min_score:
            top_scores[soc_code] = {
                "dimension_code": dimension_code,
                "interest_score": value,
                "all_scores": dim_scores,
            }
            by_dimension[dimension_code] += 1
    stats["eligible_occupations"] = len(top_scores)
    stats["eligible_occupations_by_dimension"] = dict(sorted(by_dimension.items()))
    return top_scores, stats


def _review_priority(config: dict[str, Any], source: str, inherited_weight: float | None = None) -> int:
    priority_config = config.get("output", {}).get("review_priority", {})
    if source == "onet" and inherited_weight is not None:
        return int(round(inherited_weight * float(priority_config.get("onet_weight_multiplier", 10))))
    return int(priority_config.get("ipip_default_priority", 40))


def _quality_flags(config: dict[str, Any], source: str) -> list[str]:
    flags = config.get("output", {}).get("quality_flags", {}).get(source, [])
    return [str(flag) for flag in flags]


def _build_onet_candidates_with_stats(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    onet_config = config["onet"]
    top_scores, interest_stats = _load_onet_interest_scores(config)
    allowed_task_types = set(onet_config.get("task_types", []))
    max_per_dimension = int(onet_config.get("max_tasks_per_dimension", 40))
    candidate_status = config["output"]["candidate_status"]
    transform_level = config["output"]["transform_level"]
    shells = config.get("scenario_shells", ["校园任务"])
    per_dimension_count: dict[str, int] = defaultdict(int)
    candidates = []
    stats = {
        **interest_stats,
        "task_rows_scanned": 0,
        "task_rows_allowed_type": 0,
        "task_rows_with_interest_signal": 0,
        "task_rows_skipped_by_cap": 0,
        "selected_tasks_by_dimension": {},
        "selection_policy": {
            "scale_id": onet_config.get("scale_id", "OI"),
            "min_top_interest_score": onet_config.get("min_top_interest_score", 0),
            "task_types": list(onet_config.get("task_types", [])),
            "max_tasks_per_dimension": max_per_dimension,
        },
    }

    with open(_project_path(onet_config["tasks_file"]), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            stats["task_rows_scanned"] += 1
            soc_code = row["O*NET-SOC Code"]
            task_type = row.get("Task Type", "")
            if allowed_task_types and task_type not in allowed_task_types:
                continue
            stats["task_rows_allowed_type"] += 1
            score_info = top_scores.get(soc_code)
            if not score_info:
                continue
            stats["task_rows_with_interest_signal"] += 1
            dimension_code = score_info["dimension_code"]
            if per_dimension_count[dimension_code] >= max_per_dimension:
                stats["task_rows_skipped_by_cap"] += 1
                continue

            task_id = row["Task ID"]
            inherited_weight = round(float(score_info["interest_score"]), 2)
            per_dimension_count[dimension_code] += 1
            shell = shells[(len(candidates) + int(task_id)) % len(shells)]
            candidates.append(
                {
                    "candidate_id": f"ONET_{soc_code}_{task_id}".replace(".", "_"),
                    "source": "onet",
                    "source_version": config["source_versions"]["onet"],
                    "mother_source": "ONET",
                    "mother_id": f"{soc_code}:{task_id}",
                    "transform_level": transform_level,
                    "review_status": candidate_status,
                    "occupation_soc_code": soc_code,
                    "raw_task": row["Task"],
                    "raw_task_type": task_type,
                    "dimension_code": dimension_code,
                    "inherited_weight": inherited_weight,
                    "all_interest_scores": score_info["all_scores"],
                    "scenario_shell": shell,
                    "review_priority": _review_priority(config, "onet", inherited_weight),
                    "quality_flags": _quality_flags(config, "onet"),
                    "draft_prompt": (
                        f"把 O*NET 职业任务转写成中国高中生可理解的情境选择题。"
                        f"场景类型：{shell}。隐藏测量意图，选项必须都是合理选择。"
                    ),
                    "lineage": {
                        "interests_file": onet_config["interests_file"],
                        "tasks_file": onet_config["tasks_file"],
                        "source_row": {
                            "O*NET-SOC Code": soc_code,
                            "Task ID": task_id,
                            "Date": row.get("Date"),
                            "Domain Source": row.get("Domain Source"),
                        },
                        "selection_policy": stats["selection_policy"],
                    },
                }
            )
    stats["selected_tasks_by_dimension"] = dict(sorted(per_dimension_count.items()))
    return candidates, stats


def build_onet_candidates(config: dict[str, Any]) -> list[dict[str, Any]]:
    candidates, _stats = _build_onet_candidates_with_stats(config)
    return candidates


def build_ipip_candidates(config: dict[str, Any]) -> list[dict[str, Any]]:
    ipip_config = config["ipip"]
    with open(_project_path(ipip_config["items_file"]), "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = []
    for idx, item in enumerate(data.get("questions", [])[: int(ipip_config.get("max_items", 88))], start=1):
        candidates.append(
            {
                "candidate_id": f"IPIP_88_{idx}",
                "source": "ipip",
                "source_version": config["source_versions"]["ipip"],
                "mother_source": "IPIP",
                "mother_id": f"MBTI_88_{idx}",
                "transform_level": config["output"]["transform_level"],
                "review_status": config["output"]["candidate_status"],
                "dimension_status": ipip_config.get("dimension_status", "needs_manual_dimension_mapping"),
                "raw_title": item.get("title", ""),
                "raw_options": item.get("selections", []),
                "review_priority": _review_priority(config, "ipip"),
                "quality_flags": _quality_flags(config, "ipip"),
                "draft_prompt": (
                    "把该 IPIP 题项转写成中国高中生情境判断题。"
                    "保留原始选项的心理对立关系，但不要让题目直接暴露测量维度。"
                ),
                "lineage": {
                    "items_file": ipip_config["items_file"],
                    "source_row": {"item_index": idx},
                },
            }
        )
    return candidates


def build_candidate_pool(config_path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    config = load_generation_config(config_path)
    onet_candidates, onet_stats = _build_onet_candidates_with_stats(config)
    ipip_candidates = build_ipip_candidates(config)
    candidates = onet_candidates + ipip_candidates
    candidates = sorted(
        candidates,
        key=lambda item: (-int(item.get("review_priority", 0)), item.get("source", ""), item.get("candidate_id", "")),
    )
    return {
        "version": config["version"],
        "status": config["output"]["candidate_status"],
        "transform_level": config["output"]["transform_level"],
        "counts": {
            "total": len(candidates),
            "onet": len(onet_candidates),
            "ipip": len(ipip_candidates),
        },
        "source_counts": {
            "onet": onet_stats,
            "ipip": {
                "items_file": config["ipip"]["items_file"],
                "raw_items": len(ipip_candidates),
                "selected_items": len(ipip_candidates),
                "selection_policy": {
                    "max_items": config["ipip"].get("max_items", 88),
                    "dimension_status": config["ipip"].get("dimension_status", "needs_manual_dimension_mapping"),
                },
            },
        },
        "candidates": candidates,
    }


def write_candidate_pool(output_path: Path, config_path: Path = QUESTION_GENERATION_CONFIG_PATH) -> dict[str, Any]:
    pool = build_candidate_pool(config_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    return pool
