import csv
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb
from fastapi.testclient import TestClient

from backend.config import DB_PATH
from backend.init_db import init_database
from backend.main import app
from backend.populate_golden_bank import _load_seed_file_list, populate
from backend.question_candidates import build_candidate_pool
from backend.question_review import promote_review_batch, write_review_batch
from backend.scripts.generate_cn_occupation_mapping import _load_rules, tag_occupation


class HollandPlanSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        populate()
        con = duckdb.connect(DB_PATH)
        try:
            con.execute("DROP TABLE IF EXISTS cn_occupation_riasec_map")
            con.execute(
                """
                CREATE TABLE cn_occupation_riasec_map (
                    occupation_code VARCHAR PRIMARY KEY,
                    occupation_name VARCHAR,
                    primary_riasec VARCHAR,
                    matched_rule_id VARCHAR,
                    matched_keyword VARCHAR,
                    source_version VARCHAR,
                    source_text VARCHAR,
                    mapped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            con.execute(
                """
                INSERT INTO cn_occupation_riasec_map (
                    occupation_code, occupation_name, primary_riasec,
                    matched_rule_id, matched_keyword, source_version, source_text
                )
                VALUES
                    ('2-02-02-02', '工程测量工程技术人员', 'R', 'test', '工程', 'test', '工程 测量'),
                    ('2-02-01-02', '地球物理地球化学与遥感勘查工程技术人员', 'I', 'test', '遥感', 'test', '遥感 数据')
                """
            )
        finally:
            con.close()

    def test_core_tables_and_seed_bank(self):
        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sjt_item_bank").fetchone()[0], 18)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM sjt_consistency_rules").fetchone()[0], 2)
            self.assertGreater(con.execute("SELECT COUNT(*) FROM sjt_weights").fetchone()[0], 0)
            weight_columns = {
                row[1]
                for row in con.execute("PRAGMA table_info('sjt_weights')").fetchall()
            }
            self.assertIn("source_version", weight_columns)
            self.assertIn("review_status", weight_columns)
            self.assertIn("lineage_json", weight_columns)
            weight_lineage = con.execute(
                "SELECT lineage_json FROM sjt_weights WHERE sjt_q_id = 'H_Gala' LIMIT 1"
            ).fetchone()[0]
            self.assertIn("option_val", json.loads(weight_lineage))
            columns = {
                row[1]
                for row in con.execute("PRAGMA table_info('sjt_item_bank')").fetchall()
            }
            self.assertIn("lineage_json", columns)
            self.assertIn("review_status", columns)
            lineage = con.execute(
                "SELECT lineage_json FROM sjt_item_bank WHERE sjt_q_id = 'H_Gala'"
            ).fetchone()[0]
            self.assertIn("option_weights", json.loads(lineage))
            rule_columns = {
                row[1]
                for row in con.execute("PRAGMA table_info('sjt_consistency_rules')").fetchall()
            }
            self.assertIn("source_version", rule_columns)
            self.assertIn("review_status", rule_columns)
            self.assertIn("lineage_json", rule_columns)
            rule_lineage = con.execute(
                "SELECT lineage_json FROM sjt_consistency_rules WHERE rule_id = 'RULE_M_Exam_JP1'"
            ).fetchone()[0]
            parsed_rule_lineage = json.loads(rule_lineage)
            self.assertEqual(parsed_rule_lineage["rule_type"], "consistency_penalty")
            self.assertEqual(parsed_rule_lineage["source_version"], "2026-05-13")
        finally:
            con.close()

    def test_questions_api_includes_visible_verification_choices(self):
        client = TestClient(app)
        response = client.get("/api/questions")
        self.assertEqual(response.status_code, 200)
        questions = response.json()["questions"]
        self.assertEqual(len(questions), 18)
        self.assertTrue(all(q["choices"] for q in questions))
        verify_questions = [q for q in questions if q.get("visibleIf")]
        self.assertTrue(verify_questions)
        self.assertTrue(all(q["choices"] for q in verify_questions))

    def test_submit_and_report_scoring_loop(self):
        client = TestClient(app)
        questions = client.get("/api/questions").json()["questions"]
        answers = {}
        for question in questions:
            if not question.get("visibleIf"):
                answers[question["name"]] = question["choices"][0]["value"]
        for question in questions:
            condition = question.get("visibleIf")
            if not condition:
                continue
            match = re.match(r"\{([^}]+)\}\s*=\s*'([^']+)'", condition)
            self.assertIsNotNone(match)
            trigger_q, trigger_value = match.groups()
            if answers.get(trigger_q) == trigger_value:
                answers[question["name"]] = question["choices"][0]["value"]

        submit = client.post("/api/submit", json={"user_id": "smoke", "answers": answers})
        self.assertEqual(submit.status_code, 200)
        report = client.get(f"/api/report/{submit.json()['submission_id']}")
        self.assertEqual(report.status_code, 200)
        payload = report.json()
        self.assertTrue(payload["dimensions"])
        self.assertTrue(payload["holland_top3"])
        self.assertTrue(payload["mbti_type"])
        self.assertTrue(payload["cross_insight"])
        self.assertTrue(payload["recommended_cn_occupations"])
        self.assertTrue(payload["source_lineage"]["answered_items"])
        first_weight = payload["source_lineage"]["answered_items"][0]["weights"][0]
        self.assertIn("lineage", first_weight)
        self.assertIn("review_status", first_weight)
        self.assertEqual(payload["source_lineage"]["service"], "lifehack-holland")
        self.assertTrue(payload["consistency_issues"])
        issue = payload["consistency_issues"][0]
        self.assertEqual(issue["review_status"], "approved_seed")
        self.assertEqual(issue["lineage"]["rule_type"], "consistency_penalty")

    def test_candidate_pool_preserves_lineage_and_review_gate(self):
        pool = build_candidate_pool()
        self.assertEqual(pool["status"], "needs_review")
        self.assertGreaterEqual(pool["counts"]["onet"], 6)
        self.assertEqual(pool["counts"]["ipip"], 88)
        sample = pool["candidates"][0]
        self.assertIn("lineage", sample)
        self.assertEqual(sample["review_status"], "needs_review")
        self.assertEqual(sample["transform_level"], "L1_candidate_seed")

    def test_review_batch_and_approved_promotion_preserve_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            batch_path = tmp_path / "review.csv"
            summary = write_review_batch(batch_path, limit=2, source="onet")
            self.assertEqual(summary["rows"], 2)

            with open(batch_path, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["source_version"], "O*NET Database 30.2 text files")
            self.assertEqual(rows[0]["transform_level"], "L1_candidate_seed")
            self.assertIn("source_row", json.loads(rows[0]["candidate_lineage_json"]))
            approved = rows[0]
            approved["review_status"] = "approved"
            approved["approved_q_id"] = "Q_REVIEW_SMOKE"
            approved["scenario_text"] = "社团需要完成一次复杂任务，你更想承担哪一部分？"
            approved["option_a_text"] = "先拆解任务流程，自己动手解决最关键的技术环节。"
            approved["option_a_weights_json"] = '[["Holland_R", 1.5]]'
            approved["option_a_lineage_json"] = '{"mother_id":"11-1011.00:8823"}'
            approved["option_b_text"] = "先查资料和案例，判断哪种方案成功概率更高。"
            approved["option_b_weights_json"] = '[["Holland_I", 1.5]]'
            approved["option_b_lineage_json"] = '{"mother_id":"11-1011.00:8824"}'
            rows[1]["review_status"] = "needs_rewrite"

            with open(batch_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            output_path = tmp_path / "items.json"
            promoted = promote_review_batch(batch_path, output_path)
            self.assertEqual(promoted["approved_items"], 1)
            items = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(items[0]["q_id"], "Q_REVIEW_SMOKE")
            self.assertEqual(items[0]["lineage"]["candidate_id"], approved["candidate_id"])
            self.assertIn("candidate_lineage", items[0]["lineage"])
            self.assertEqual(items[0]["options"][0]["lineage"]["mother_id"], "11-1011.00:8823")

    def test_approved_promotion_rejects_missing_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            batch_path = tmp_path / "bad_review.csv"
            write_review_batch(batch_path, limit=1, source="onet")
            with open(batch_path, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            rows[0]["review_status"] = "approved"
            rows[0]["approved_q_id"] = "Q_BAD_REVIEW"
            rows[0]["scenario_text"] = "一个没有权重的坏题目。"
            rows[0]["option_a_text"] = "选项 A"
            rows[0]["option_b_text"] = "选项 B"
            with open(batch_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(ValueError):
                promote_review_batch(batch_path, tmp_path / "items.json")

    def test_career_riasec_rules_are_config_driven(self):
        rules = _load_rules()
        tagged = tag_occupation(
            {
                "occupation_name": "摄影测量与遥感工程技术人员",
                "skill_keywords_json": '["遥感", "数据处理"]',
                "major_keywords_json": "[]",
            },
            rules,
        )
        self.assertEqual(tagged["primary_riasec"], "I")
        self.assertEqual(tagged["matched_rule_id"], "investigative_data_science")

    def test_production_seed_files_are_config_driven(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "question_generation.json"
            config_path.write_text(
                json.dumps(
                    {
                        "production_seed": {
                            "item_files": ["backend/data/seed/custom_items.json"],
                            "rule_files": ["backend/data/seed/custom_rules.json"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch("backend.populate_golden_bank.QUESTION_GENERATION_CONFIG_PATH", config_path):
                self.assertEqual(
                    _load_seed_file_list("item_files", ["fallback.json"]),
                    ["backend/data/seed/custom_items.json"],
                )
                self.assertEqual(
                    _load_seed_file_list("rule_files", ["fallback_rules.json"]),
                    ["backend/data/seed/custom_rules.json"],
                )

            config_path.write_text(
                json.dumps({"production_seed": {"item_files": "backend/data/seed/custom_items.json"}}),
                encoding="utf-8",
            )
            with patch("backend.populate_golden_bank.QUESTION_GENERATION_CONFIG_PATH", config_path):
                with self.assertRaises(ValueError):
                    _load_seed_file_list("item_files", ["fallback.json"])


if __name__ == "__main__":
    unittest.main()
