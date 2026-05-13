import re
import unittest

import duckdb
from fastapi.testclient import TestClient

from backend.config import DB_PATH
from backend.init_db import init_database
from backend.main import app
from backend.populate_golden_bank import populate
from backend.question_candidates import build_candidate_pool
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

    def test_candidate_pool_preserves_lineage_and_review_gate(self):
        pool = build_candidate_pool()
        self.assertEqual(pool["status"], "needs_review")
        self.assertGreaterEqual(pool["counts"]["onet"], 6)
        self.assertEqual(pool["counts"]["ipip"], 88)
        sample = pool["candidates"][0]
        self.assertIn("lineage", sample)
        self.assertEqual(sample["review_status"], "needs_review")
        self.assertEqual(sample["transform_level"], "L1_candidate_seed")

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


if __name__ == "__main__":
    unittest.main()
