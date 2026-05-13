"""
Script to populate DuckDB with a comprehensive set of SJT questions.
Implements the 'Dual-Track' independent testing strategy:
- Module 1: O*NET tasks mapped strictly to Holland RIASEC.
- Module 2: IPIP Jungian translated scenarios mapped strictly to MBTI.
"""
import json
import duckdb
from pathlib import Path
from backend.config import DB_PATH, PROJECT_ROOT, QUESTION_GENERATION_CONFIG_PATH


def _project_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate


def _load_seed_file_list(key: str, fallback: list[str]) -> list[str]:
    try:
        with open(QUESTION_GENERATION_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        return fallback

    paths = config.get("production_seed", {}).get(key, fallback)
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        raise ValueError(f"production_seed.{key} must be a list of file paths")
    return paths


def _load_generation_config() -> dict:
    try:
        with open(QUESTION_GENERATION_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _load_seed_records(paths: list[str]) -> list[dict]:
    records = []
    for path in paths:
        with open(_project_path(path), "r", encoding="utf-8") as f:
            for record in json.load(f):
                item = dict(record)
                item["_seed_file"] = path
                records.append(item)
    return records


def _transform_level(item: dict) -> str:
    lineage = item.get("lineage") if isinstance(item.get("lineage"), dict) else {}
    if lineage.get("transform_level"):
        return str(lineage["transform_level"])
    mechanism = str(item.get("mechanism") or "")
    return mechanism.split(":", 1)[0] if mechanism.startswith("L") else "L4_curated_item"


def _item_lineage(item: dict, generation_config: dict) -> dict:
    lineage = item.get("lineage") if isinstance(item.get("lineage"), dict) else {}
    source_version = item.get("source_version") or lineage.get("source_version") or generation_config.get("version", "unknown")
    transform_level = _transform_level(item)
    review_status = item.get("review_status") or lineage.get("review_status") or "approved_seed"
    return {
        "lineage_quality": lineage.get("lineage_quality", "curated_seed_limited"),
        "source_seed_file": item.get("_seed_file"),
        "source_version": source_version,
        "mother_source": item.get("mother_source"),
        "mother_id": item.get("mother_id"),
        "transform_level": transform_level,
        "review_status": review_status,
        "option_weights": [
            {
                "option_val": option.get("val"),
                "weights": option.get("weights", []),
            }
            for option in item.get("options", [])
        ],
        **lineage,
    }


def _rule_id(rule: dict) -> str:
    if rule.get("rule_id"):
        return str(rule["rule_id"])
    return "RULE_{trigger}_{trigger_option}_{verify}_{expected}".format(
        trigger=rule["trigger_q_id"],
        trigger_option=rule["trigger_option"],
        verify=rule["verify_q_id"],
        expected=rule["expected_option"],
    )


def _rule_lineage(rule: dict, generation_config: dict) -> dict:
    lineage = rule.get("lineage") if isinstance(rule.get("lineage"), dict) else {}
    source_version = rule.get("source_version") or lineage.get("source_version") or generation_config.get("version", "unknown")
    review_status = rule.get("review_status") or lineage.get("review_status") or "approved_seed"
    return {
        "lineage_quality": lineage.get("lineage_quality", "curated_seed_limited"),
        "source_seed_file": rule.get("_seed_file"),
        "source_version": source_version,
        "review_status": review_status,
        "trigger_q_id": rule.get("trigger_q_id"),
        "trigger_option": rule.get("trigger_option"),
        "verify_q_id": rule.get("verify_q_id"),
        "expected_option": rule.get("expected_option"),
        "penalty_dimension": rule.get("penalty_dimension"),
        "penalty_weight": rule.get("penalty_weight"),
        **lineage,
    }


def populate():
    print("Populating generated question bank (decoupled Dual-Track mode) into DuckDB...")
    con = duckdb.connect(DB_PATH)

    con.execute("DELETE FROM sjt_responses")
    con.execute("DELETE FROM sjt_weights")
    con.execute("DELETE FROM sjt_consistency_rules")
    con.execute("DELETE FROM sjt_item_bank")

    item_files = _load_seed_file_list("item_files", ["backend/data/seed/golden_items.json"])
    rule_files = _load_seed_file_list("rule_files", ["backend/data/seed/golden_rules.json"])
    generation_config = _load_generation_config()
    bank_data = _load_seed_records(item_files)
    rules_data = _load_seed_records(rule_files)

    questions_for_frontend = {}

    for item in bank_data:
        lineage = _item_lineage(item, generation_config)
        con.execute("""
            INSERT INTO sjt_item_bank (
                sjt_q_id, mother_source, mother_id, core_mechanism, scenario_text,
                source_version, transform_level, review_status, lineage_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["q_id"],
            item["mother_source"],
            item["mother_id"],
            item["mechanism"],
            item["text"],
            lineage["source_version"],
            lineage["transform_level"],
            lineage["review_status"],
            json.dumps(lineage, ensure_ascii=False, sort_keys=True),
        ))

        opt_dict = {}
        for opt in item["options"]:
            opt_val = opt["val"]
            opt_text = opt["text"]
            opt_dict[opt_val] = opt_text

            for dim_code, weight in opt["weights"]:
                con.execute("""
                    INSERT INTO sjt_weights (sjt_q_id, option_val, dimension_code, inherited_weight)
                    VALUES (?, ?, ?, ?)
                """, (item["q_id"], opt_val, dim_code, weight))

        questions_for_frontend[item["q_id"]] = opt_dict

    for rule in rules_data:
        rule_id = _rule_id(rule)
        lineage = _rule_lineage(rule, generation_config)
        con.execute("""
            INSERT INTO sjt_consistency_rules
            (rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option,
             penalty_dimension, penalty_weight, source_version, review_status, lineage_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id, rule["trigger_q_id"], rule["trigger_option"], rule["verify_q_id"],
            rule["expected_option"], rule["penalty_dimension"], rule["penalty_weight"],
            lineage["source_version"], lineage["review_status"],
            json.dumps(lineage, ensure_ascii=False, sort_keys=True),
        ))

    con.close()

    # Write JSON for frontend (dynamic text rendering)
    with open(PROJECT_ROOT / "backend" / "data" / "questions.json", "w", encoding="utf-8") as f:
        json.dump(questions_for_frontend, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully inserted {len(bank_data)} questions (decoupled), mapping weights, and {len(rules_data)} rules.")

if __name__ == "__main__":
    populate()
