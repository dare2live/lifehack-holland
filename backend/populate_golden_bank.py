"""
Script to populate DuckDB with a comprehensive set of SJT questions.
Implements the 'Dual-Track' independent testing strategy:
- Module 1: O*NET tasks mapped strictly to Holland RIASEC.
- Module 2: IPIP Jungian translated scenarios mapped strictly to MBTI.
"""
import json
import duckdb
from pathlib import Path
from backend.config import DB_PATH, PROJECT_ROOT

# ═══════════════════════════════════════════════════════════════════
# GENERATED QUESTION BANK (Dual-Track Decoupled)
# Data is loaded dynamically from configuration files.
# ═══════════════════════════════════════════════════════════════════

def populate():
    print("Populating generated question bank (decoupled Dual-Track mode) into DuckDB...")
    con = duckdb.connect(DB_PATH)

    con.execute("DELETE FROM sjt_responses")
    con.execute("DELETE FROM sjt_weights")
    con.execute("DELETE FROM sjt_consistency_rules")
    con.execute("DELETE FROM sjt_item_bank")

    # Load parameters from configuration files
    seed_dir = PROJECT_ROOT / "backend" / "data" / "seed"

    with open(seed_dir / "golden_items.json", "r", encoding="utf-8") as f:
        bank_data = json.load(f)

    with open(seed_dir / "golden_rules.json", "r", encoding="utf-8") as f:
        rules_data = json.load(f)

    questions_for_frontend = {}

    for item in bank_data:
        con.execute("""
            INSERT INTO sjt_item_bank (sjt_q_id, mother_source, mother_id, core_mechanism, scenario_text)
            VALUES (?, ?, ?, ?, ?)
        """, (item["q_id"], item["mother_source"], item["mother_id"], item["mechanism"], item["text"]))

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
        rule_id = f"RULE_{rule['trigger_q_id']}"
        con.execute("""
            INSERT INTO sjt_consistency_rules
            (rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option, penalty_dimension, penalty_weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id, rule["trigger_q_id"], rule["trigger_option"], rule["verify_q_id"],
            rule["expected_option"], rule["penalty_dimension"], rule["penalty_weight"]
        ))

    con.close()

    # Write JSON for frontend (dynamic text rendering)
    with open(PROJECT_ROOT / "backend" / "data" / "questions.json", "w", encoding="utf-8") as f:
        json.dump(questions_for_frontend, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully inserted {len(bank_data)} questions (decoupled), mapping weights, and {len(rules_data)} rules.")

if __name__ == "__main__":
    populate()
