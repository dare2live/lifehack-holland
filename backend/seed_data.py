"""
seed_data.py — Seed 2 complete test-question groups into DuckDB.

Each group contains:
  • 1 main scenario question  (sjt_item_bank)
  • 3-4 option weight mappings (sjt_weights)
  • 1 hidden verification question (sjt_item_bank)
  • 2-3 verification option weights (sjt_weights)
  • 1 consistency rule (sjt_consistency_rules)

Group 1: 迎新晚会音响故障 (Gala Sound Failure)
Group 2: 班级海报设计之争 (Poster Design Conflict)

Usage:
    python -m backend.seed_data          # from project root
    python backend/seed_data.py          # direct execution
"""
import json
import duckdb
from backend.config import DB_PATH


# ═══════════════════════════════════════════════════════════════════
# SEED DATA — GROUP 1: 迎新晚会音响故障
# ═══════════════════════════════════════════════════════════════════

GROUP_1_ITEMS = [
    # ── 主场景题 ──
    {
        "sjt_q_id": "Q_Gala",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_4.A.4.a.1",
        "core_mechanism": "L2_crisis_response_E_vs_R",
        "scenario_text": (
            "迎新晚会彩排时，音响突然烧坏了，距离开场还有10分钟。"
            "作为负责人的你，第一反应是什么？"
        ),
    },
    # ── 隐藏验证题 (选了A才出现) ──
    {
        "sjt_q_id": "Q_Gala_verify",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_4.A.4.a.1_v",
        "core_mechanism": "L2_verify_E_authenticity",
        "scenario_text": (
            "你走向主持人请求帮忙临场互动拖延时间，"
            '但主持人翻了个白眼说"这不在台本上，我不干"。你的下一步是？'
        ),
    },
]

GROUP_1_WEIGHTS = [
    # ── 主场景选项权重 ──
    # 选项 A: 安抚观众+让主持人互动拖延
    {"sjt_q_id": "Q_Gala", "option_val": "A", "dimension_code": "Holland_E", "inherited_weight": 2.0},
    {"sjt_q_id": "Q_Gala", "option_val": "A", "dimension_code": "MBTI_E",   "inherited_weight": 1.5},
    # 选项 B: 冲到总电闸排查线路
    {"sjt_q_id": "Q_Gala", "option_val": "B", "dimension_code": "Holland_R", "inherited_weight": 2.0},
    {"sjt_q_id": "Q_Gala", "option_val": "B", "dimension_code": "MBTI_T",   "inherited_weight": 1.5},
    # 选项 C: 打电话叫有经验的学长来帮忙
    {"sjt_q_id": "Q_Gala", "option_val": "C", "dimension_code": "Holland_S", "inherited_weight": 1.0},
    {"sjt_q_id": "Q_Gala", "option_val": "C", "dimension_code": "MBTI_F",   "inherited_weight": 1.0},

    # ── 验证题选项权重 ──
    # 选项 X: 自己直接冲上台暖场 (真正的 E 型)
    {"sjt_q_id": "Q_Gala_verify", "option_val": "X", "dimension_code": "Holland_E", "inherited_weight": 1.5},
    {"sjt_q_id": "Q_Gala_verify", "option_val": "X", "dimension_code": "MBTI_E",   "inherited_weight": 1.0},
    # 选项 Y: 算了，让灯光师放点背景音乐，大家等着就好
    {"sjt_q_id": "Q_Gala_verify", "option_val": "Y", "dimension_code": "Holland_C", "inherited_weight": 0.5},
    {"sjt_q_id": "Q_Gala_verify", "option_val": "Y", "dimension_code": "MBTI_I",   "inherited_weight": 0.5},
    # 选项 Z: 去找音控组的人一起排查问题
    {"sjt_q_id": "Q_Gala_verify", "option_val": "Z", "dimension_code": "Holland_R", "inherited_weight": 1.0},
    {"sjt_q_id": "Q_Gala_verify", "option_val": "Z", "dimension_code": "MBTI_T",   "inherited_weight": 0.5},
]

GROUP_1_RULES = [
    {
        "rule_id": "RULE_Gala_E_fake",
        "trigger_q_id": "Q_Gala",
        "trigger_option": "A",           # 主场景中选了"安抚观众"
        "verify_q_id": "Q_Gala_verify",
        "expected_option": "Y",          # 验证中选了"算了放音乐等着"
        "penalty_dimension": "Holland_E",
        "penalty_weight": -2.0,
    },
]

# ═══════════════════════════════════════════════════════════════════
# SEED DATA — GROUP 2: 班级海报设计之争
# ═══════════════════════════════════════════════════════════════════

GROUP_2_ITEMS = [
    # ── 主场景题 ──
    {
        "sjt_q_id": "Q_Poster",
        "mother_source": "IPIP_Jung",
        "mother_id": "IPIP_E_vs_I_03",
        "core_mechanism": "L2_creative_conflict_A_vs_I",
        "scenario_text": (
            "班级要参加校庆海报比赛，你和另一位同学对设计方向完全相反——"
            "你想做极简风格，TA 想做花哨拼贴。班主任说你俩自己商量，"
            "但比赛明天就要交。你会怎么做？"
        ),
    },
    # ── 隐藏验证题 (选了A才出现) ──
    {
        "sjt_q_id": "Q_Poster_verify",
        "mother_source": "IPIP_Jung",
        "mother_id": "IPIP_E_vs_I_03_v",
        "core_mechanism": "L2_verify_A_creative_persistence",
        "scenario_text": (
            "你花了两小时做完了自己的方案，拿给几个同学看，"
            "大家一致觉得另一位同学的拼贴风更好看。你接下来更可能怎么处理？"
        ),
    },
]

GROUP_2_WEIGHTS = [
    # ── 主场景选项权重 ──
    # 选项 A: 各做各的方案，明天让全班投票决定 (坚持+竞争)
    {"sjt_q_id": "Q_Poster", "option_val": "A", "dimension_code": "Holland_A", "inherited_weight": 2.0},
    {"sjt_q_id": "Q_Poster", "option_val": "A", "dimension_code": "MBTI_T",   "inherited_weight": 1.5},
    # 选项 B: 主动约TA去奶茶店聊，找个折中方案 (协调+妥协)
    {"sjt_q_id": "Q_Poster", "option_val": "B", "dimension_code": "Holland_S", "inherited_weight": 2.0},
    {"sjt_q_id": "Q_Poster", "option_val": "B", "dimension_code": "MBTI_F",   "inherited_weight": 1.5},
    # 选项 C: 上网查历年获奖海报的数据来说服TA (研究+分析)
    {"sjt_q_id": "Q_Poster", "option_val": "C", "dimension_code": "Holland_I", "inherited_weight": 2.0},
    {"sjt_q_id": "Q_Poster", "option_val": "C", "dimension_code": "MBTI_N",   "inherited_weight": 1.0},
    # 选项 D: 算了，让TA做吧，我去忙别的 (回避)
    {"sjt_q_id": "Q_Poster", "option_val": "D", "dimension_code": "MBTI_I",   "inherited_weight": 1.0},
    {"sjt_q_id": "Q_Poster", "option_val": "D", "dimension_code": "Holland_C", "inherited_weight": 0.5},

    # ── 验证题选项权重 ──
    # 选项 X: 尊重大家意见，就用TA的方案吧 (坦然接受)
    {"sjt_q_id": "Q_Poster_verify", "option_val": "X", "dimension_code": "Holland_S", "inherited_weight": 1.0},
    {"sjt_q_id": "Q_Poster_verify", "option_val": "X", "dimension_code": "MBTI_F",   "inherited_weight": 1.0},
    # 选项 Y: 有点不服，觉得他们不懂审美，但嘴上不说
    {"sjt_q_id": "Q_Poster_verify", "option_val": "Y", "dimension_code": "MBTI_I",   "inherited_weight": 0.5},
    {"sjt_q_id": "Q_Poster_verify", "option_val": "Y", "dimension_code": "Holland_A", "inherited_weight": -0.5},
    # 选项 Z: 坚持提出修改意见，用对比图展示两种方案的优劣
    {"sjt_q_id": "Q_Poster_verify", "option_val": "Z", "dimension_code": "Holland_A", "inherited_weight": 1.5},
    {"sjt_q_id": "Q_Poster_verify", "option_val": "Z", "dimension_code": "MBTI_T",   "inherited_weight": 1.0},
]

GROUP_2_RULES = [
    {
        "rule_id": "RULE_Poster_A_fake",
        "trigger_q_id": "Q_Poster",
        "trigger_option": "A",             # 主场景中选了"各做方案全班投票"
        "verify_q_id": "Q_Poster_verify",
        "expected_option": "Y",            # 验证中选了"不服但嘴上不说"
        "penalty_dimension": "Holland_A",
        "penalty_weight": -1.5,
    },
]


# ═══════════════════════════════════════════════════════════════════
# SEEDING LOGIC
# ═══════════════════════════════════════════════════════════════════

def seed_database(db_path: str = DB_PATH) -> None:
    """Insert all seed data into the DuckDB tables."""
    con = duckdb.connect(db_path)
    try:
        # Combine groups
        all_items = GROUP_1_ITEMS + GROUP_2_ITEMS
        all_weights = GROUP_1_WEIGHTS + GROUP_2_WEIGHTS
        all_rules = GROUP_1_RULES + GROUP_2_RULES

        # ── Clear existing seed data (idempotent re-runs) ──
        # Delete in reverse FK order
        con.execute("DELETE FROM sjt_consistency_rules")
        con.execute("DELETE FROM sjt_weights")
        con.execute("DELETE FROM sjt_item_bank")
        print("[seed_data] 🧹 Cleared existing data")

        # ── Insert item_bank ──
        for item in all_items:
            con.execute(
                """
                INSERT INTO sjt_item_bank (sjt_q_id, mother_source, mother_id, core_mechanism, scenario_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                [item["sjt_q_id"], item["mother_source"], item["mother_id"],
                 item["core_mechanism"], item["scenario_text"]],
            )
        print(f"[seed_data] 📝 Inserted {len(all_items)} items into sjt_item_bank")

        # ── Insert weights ──
        for w in all_weights:
            con.execute(
                """
                INSERT INTO sjt_weights (sjt_q_id, option_val, dimension_code, inherited_weight)
                VALUES (?, ?, ?, ?)
                """,
                [w["sjt_q_id"], w["option_val"], w["dimension_code"], w["inherited_weight"]],
            )
        print(f"[seed_data] ⚖️  Inserted {len(all_weights)} rows into sjt_weights")

        # ── Insert consistency rules ──
        for r in all_rules:
            con.execute(
                """
                INSERT INTO sjt_consistency_rules
                    (rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option,
                     penalty_dimension, penalty_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [r["rule_id"], r["trigger_q_id"], r["trigger_option"],
                 r["verify_q_id"], r["expected_option"],
                 r["penalty_dimension"], r["penalty_weight"]],
            )
        print(f"[seed_data] 🚨 Inserted {len(all_rules)} rows into sjt_consistency_rules")

        # ── Verification queries ──
        print("\n[seed_data] ── Verification ──")

        items = con.execute("SELECT sjt_q_id, mother_source, core_mechanism FROM sjt_item_bank").fetchall()
        print(f"  sjt_item_bank ({len(items)} rows):")
        for row in items:
            print(f"    {row[0]:20s} | source={row[1]:10s} | mechanism={row[2]}")

        weights = con.execute(
            "SELECT sjt_q_id, option_val, dimension_code, inherited_weight FROM sjt_weights ORDER BY sjt_q_id, option_val"
        ).fetchall()
        print(f"  sjt_weights ({len(weights)} rows):")
        for row in weights:
            print(f"    {row[0]:20s} | opt={row[1]} | dim={row[2]:12s} | weight={row[3]:+.1f}")

        rules = con.execute(
            "SELECT rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option, penalty_dimension, penalty_weight FROM sjt_consistency_rules"
        ).fetchall()
        print(f"  sjt_consistency_rules ({len(rules)} rows):")
        for row in rules:
            print(f"    {row[0]:25s} | if {row[1]}={row[2]} AND {row[3]}={row[4]} → {row[5]} {row[6]:+.1f}")

        print("\n[seed_data] ✅ Seed complete!")

    finally:
        con.close()


# ── Also dump seed data as JSON files for reference ──

def export_seed_json() -> None:
    """Export seed data as JSON files in data/seed/ for documentation."""
    from backend.config import SEED_DIR

    items_path = SEED_DIR / "sample_items.json"
    with open(items_path, "w", encoding="utf-8") as f:
        json.dump(GROUP_1_ITEMS + GROUP_2_ITEMS, f, ensure_ascii=False, indent=2)

    weights_path = SEED_DIR / "sample_weights.json"
    with open(weights_path, "w", encoding="utf-8") as f:
        json.dump(GROUP_1_WEIGHTS + GROUP_2_WEIGHTS, f, ensure_ascii=False, indent=2)

    rules_path = SEED_DIR / "sample_rules.json"
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump(GROUP_1_RULES + GROUP_2_RULES, f, ensure_ascii=False, indent=2)

    print(f"[seed_data] 📁 JSON exports saved to {SEED_DIR}")


if __name__ == "__main__":
    seed_database()
    export_seed_json()
