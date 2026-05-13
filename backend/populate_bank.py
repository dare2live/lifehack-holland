"""
populate_bank.py — Generate and insert a comprehensive SJT question bank.

This script replaces `seed_data.py` and provides a larger, LLM-curated (by Antigravity)
question bank that translates O*NET and IPIP master concepts into high school scenarios.
No runtime LLM calls are needed; this is the offline generated output.
"""
import json
import duckdb
from backend.config import DB_PATH, PROJECT_ROOT

# ═══════════════════════════════════════════════════════════════════
# GENERATED QUESTION BANK (Translated from Master Sources)
# ═══════════════════════════════════════════════════════════════════

ITEMS = []
WEIGHTS = []
RULES = []

def add_group(main_item, main_weights, verify_item=None, verify_weights=None, rule=None):
    ITEMS.append(main_item)
    for w in main_weights:
        WEIGHTS.append(w)
    if verify_item:
        ITEMS.append(verify_item)
        for w in verify_weights:
            WEIGHTS.append(w)
    if rule:
        RULES.append(rule)

# ── Group 1: 科技社团招新 (Tech Club Recruitment) - R, E, I / E, I, T ──
add_group(
    main_item={
        "sjt_q_id": "Q_TechClub",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_1.A.1",
        "core_mechanism": "L2_influence_vs_hands_on",
        "scenario_text": "你是科技社团的骨干。这周末要在操场上摆摊招新，为了吸引更多同学，你主动提出承担哪项工作？",
    },
    main_weights=[
        {"sjt_q_id": "Q_TechClub", "option_val": "A", "dimension_code": "Holland_R", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_TechClub", "option_val": "A", "dimension_code": "MBTI_T",   "inherited_weight": 1.0},
        
        {"sjt_q_id": "Q_TechClub", "option_val": "B", "dimension_code": "Holland_E", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_TechClub", "option_val": "B", "dimension_code": "MBTI_E",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_TechClub", "option_val": "C", "dimension_code": "Holland_I", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_TechClub", "option_val": "C", "dimension_code": "MBTI_I",   "inherited_weight": 1.5},
    ],
    verify_item={
        "sjt_q_id": "Q_TechClub_v",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_1.A.1_v",
        "core_mechanism": "L2_verify_E_resilience",
        "scenario_text": "招新刚开始，有几个路过的同学对你大声说：'这社团好无聊啊，别去了。' 你接下来更可能怎么处理？",
    },
    verify_weights=[
        {"sjt_q_id": "Q_TechClub_v", "option_val": "X", "dimension_code": "Holland_E", "inherited_weight": 1.5},
        {"sjt_q_id": "Q_TechClub_v", "option_val": "Y", "dimension_code": "MBTI_I", "inherited_weight": 1.0},
    ],
    rule={
        "rule_id": "RULE_TechClub_E_fake",
        "trigger_q_id": "Q_TechClub", "trigger_option": "B",  # Picked presentation/marketing
        "verify_q_id": "Q_TechClub_v", "expected_option": "Y", # But got embarrassed easily
        "penalty_dimension": "Holland_E", "penalty_weight": -2.0,
    }
)

# ── Group 2: 期末复习计划 (Finals Study Plan) - C, A / J, P, S, N ──
add_group(
    main_item={
        "sjt_q_id": "Q_Finals",
        "mother_source": "IPIP_Jung",
        "mother_id": "IPIP_J_vs_P_01",
        "core_mechanism": "L2_planning_vs_spontaneous",
        "scenario_text": "距离期末考试还有两周，你平时的复习习惯更倾向于哪种？",
    },
    main_weights=[
        {"sjt_q_id": "Q_Finals", "option_val": "A", "dimension_code": "Holland_C", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_Finals", "option_val": "A", "dimension_code": "MBTI_J",   "inherited_weight": 2.0},
        
        {"sjt_q_id": "Q_Finals", "option_val": "B", "dimension_code": "MBTI_P",   "inherited_weight": 2.0},
        {"sjt_q_id": "Q_Finals", "option_val": "B", "dimension_code": "Holland_A", "inherited_weight": 1.0},
        
        {"sjt_q_id": "Q_Finals", "option_val": "C", "dimension_code": "MBTI_N",   "inherited_weight": 1.5},
        {"sjt_q_id": "Q_Finals", "option_val": "C", "dimension_code": "MBTI_P",   "inherited_weight": 1.0},
    ],
    verify_item={
        "sjt_q_id": "Q_Finals_v",
        "mother_source": "IPIP_Jung",
        "mother_id": "IPIP_J_vs_P_01_v",
        "core_mechanism": "L2_verify_J_strictness",
        "scenario_text": "周末你计划好要复习数学，但最好的朋友突然拿到两张绝版演唱会门票叫你马上出去。你的反应是？",
    },
    verify_weights=[
        {"sjt_q_id": "Q_Finals_v", "option_val": "X", "dimension_code": "MBTI_J", "inherited_weight": 1.5},
        {"sjt_q_id": "Q_Finals_v", "option_val": "Y", "dimension_code": "MBTI_P", "inherited_weight": 1.0},
    ],
    rule={
        "rule_id": "RULE_Finals_J_fake",
        "trigger_q_id": "Q_Finals", "trigger_option": "A",  # Picked strict schedule
        "verify_q_id": "Q_Finals_v", "expected_option": "Y", # Broke it immediately
        "penalty_dimension": "MBTI_J", "penalty_weight": -1.5,
    }
)

# ── Group 3: 运动会报名争议 (Sports Meet Conflict) - S, E, C / F, T ──
add_group(
    main_item={
        "sjt_q_id": "Q_SportsMeet",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_3.A.2",
        "core_mechanism": "L2_conflict_resolution_S_vs_E",
        "scenario_text": "班级运动会报名，有个没人愿意跑的 3000 米长跑名额。班长强制指派了平时不太爱运动的小明，小明很委屈。作为体育委员，你会怎么处理？",
    },
    main_weights=[
        {"sjt_q_id": "Q_SportsMeet", "option_val": "A", "dimension_code": "Holland_S", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_SportsMeet", "option_val": "A", "dimension_code": "MBTI_F",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_SportsMeet", "option_val": "B", "dimension_code": "Holland_E", "inherited_weight": 1.5},
        {"sjt_q_id": "Q_SportsMeet", "option_val": "B", "dimension_code": "MBTI_T",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_SportsMeet", "option_val": "C", "dimension_code": "Holland_C", "inherited_weight": 1.5},
        {"sjt_q_id": "Q_SportsMeet", "option_val": "C", "dimension_code": "MBTI_J",   "inherited_weight": 1.0},
    ]
    # No verify rule here to show variety
)

# ── Group 4: 破损的实验室仪器 (Broken Lab Equipment) - R, I, A / S, N, T ──
add_group(
    main_item={
        "sjt_q_id": "Q_Lab",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_2.A.1",
        "core_mechanism": "L2_problem_solving_R_vs_I",
        "scenario_text": "化学实验课上，显微镜的焦距旋钮突然卡住了，老师又去别的组指导了。你会怎么做？",
    },
    main_weights=[
        {"sjt_q_id": "Q_Lab", "option_val": "A", "dimension_code": "Holland_R", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_Lab", "option_val": "A", "dimension_code": "MBTI_S",   "inherited_weight": 1.0},
        
        {"sjt_q_id": "Q_Lab", "option_val": "B", "dimension_code": "Holland_I", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_Lab", "option_val": "B", "dimension_code": "MBTI_N",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_Lab", "option_val": "C", "dimension_code": "Holland_S", "inherited_weight": 1.0},
        {"sjt_q_id": "Q_Lab", "option_val": "C", "dimension_code": "MBTI_F",   "inherited_weight": 1.0},
    ]
)

# ── Group 5: 艺术节舞台布置 (Art Fest Stage) - A, C, E / N, S, E ──
add_group(
    main_item={
        "sjt_q_id": "Q_ArtFest",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_1.A.2",
        "core_mechanism": "L2_creativity_vs_convention",
        "scenario_text": "你负责校园艺术节的舞台布置。你会如何开展这项工作？",
    },
    main_weights=[
        {"sjt_q_id": "Q_ArtFest", "option_val": "A", "dimension_code": "Holland_A", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_ArtFest", "option_val": "A", "dimension_code": "MBTI_N",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_ArtFest", "option_val": "B", "dimension_code": "Holland_C", "inherited_weight": 2.0},
        {"sjt_q_id": "Q_ArtFest", "option_val": "B", "dimension_code": "MBTI_S",   "inherited_weight": 1.5},
        
        {"sjt_q_id": "Q_ArtFest", "option_val": "C", "dimension_code": "Holland_E", "inherited_weight": 1.5},
        {"sjt_q_id": "Q_ArtFest", "option_val": "C", "dimension_code": "MBTI_E",   "inherited_weight": 1.0},
    ],
    verify_item={
        "sjt_q_id": "Q_ArtFest_v",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_1.A.2_v",
        "core_mechanism": "L2_verify_A_authenticity",
        "scenario_text": "教导主任看了你的设计，说太前卫了，要求你换成历年传统的大红灯笼风格。你此时心里的想法是？",
    },
    verify_weights=[
        {"sjt_q_id": "Q_ArtFest_v", "option_val": "X", "dimension_code": "Holland_A", "inherited_weight": 1.0},
        {"sjt_q_id": "Q_ArtFest_v", "option_val": "Y", "dimension_code": "Holland_C", "inherited_weight": 1.0},
    ],
    rule={
        "rule_id": "RULE_ArtFest_A_fake",
        "trigger_q_id": "Q_ArtFest", "trigger_option": "A",
        "verify_q_id": "Q_ArtFest_v", "expected_option": "Y", 
        "penalty_dimension": "Holland_A", "penalty_weight": -2.0,
    }
)


# ═══════════════════════════════════════════════════════════════════
# OPTION TEXTS FOR FRONTEND EXPORT
# ═══════════════════════════════════════════════════════════════════

OPTION_TEXTS = {
    "Q_TechClub": {
        "A": "把社团的发明作品带来，现场给别人展示怎么拆解和组装。",
        "B": "拿个大喇叭站在摊位前，向来往的同学激情推销社团的优势。",
        "C": "提前研究一下其他热门社团的招新套路，整理成数据给会长看。",
    },
    "Q_TechClub_v": {
        "X": "立刻拿大喇叭回怼，并大声介绍社团的牛逼事迹证明他们错了。",
        "Y": "觉得很丢脸，声音变小了，默默退到摊位后方整理传单。",
    },
    "Q_Finals": {
        "A": "制定详细到半小时的复习课表，打印贴在桌上严格执行。",
        "B": "不写课表，看今天心情想复习哪科就复习哪科，往往最后几天突击。",
        "C": "先花一天时间画出所有科目的思维导图，重点抓大题思路。",
    },
    "Q_Finals_v": {
        "X": "果断拒绝，告诉她计划不能打乱，考完试再约。",
        "Y": "稍微犹豫一下就答应了，心想'反正是绝版演唱会，复习明天再熬夜补吧'。",
    },
    "Q_SportsMeet": {
        "A": "私下找小明聊天，倾听他的抱怨，帮他放松心态，并在比赛时全程陪跑。",
        "B": "当面告诉小明：'这是集体荣誉，你必须上，跑倒数第一大家也不会怪你。'",
        "C": "去查历年成绩，计算出一个只要小明走完也能帮班级拿参与分的策略告诉他。",
    },
    "Q_Lab": {
        "A": "自己动手拆开旋钮的盖子，试图找到卡住的齿轮并把它复位。",
        "B": "不乱动，翻开物理光学课本，研究显微镜的构造原理试图推断故障原因。",
        "C": "主动去问旁边进度快的组，能不能等他们做完借他们的显微镜用一下。",
    },
    "Q_ArtFest": {
        "A": "构思一个极具创意的赛博朋克主题，尝试使用平时没见过的废弃材料。",
        "B": "翻看过去三年的晚会照片，严格按照以往成功、无差错的经典流程去买装饰。",
        "C": "把布置任务切分成几块，自己不动手，去游说和指挥低年级的干事来做。",
    },
    "Q_ArtFest_v": {
        "X": "非常抵触，觉得那样太俗气，决定去和主任据理力争保留自己的设计。",
        "Y": "松了一口气，心想：行吧，反正听领导的准没错，还省了我去买新材料的麻烦。",
    }
}


# ═══════════════════════════════════════════════════════════════════
# DATABASE SEEDING
# ═══════════════════════════════════════════════════════════════════

def populate():
    print("Populating generated question bank into DuckDB...")
    con = duckdb.connect(DB_PATH)
    
    # 1. Update backend/main.py with these text mappings so API works
    # (Since we stored texts in main.py temporarily for the seed data, 
    # we update a generated json file that main.py can read, or just output it)
    
    with open(PROJECT_ROOT / "backend" / "data" / "questions.json", "w", encoding="utf-8") as f:
        json.dump(OPTION_TEXTS, f, ensure_ascii=False, indent=2)
    
    try:
        # 2. Clear old data
        con.execute("DELETE FROM sjt_consistency_rules")
        con.execute("DELETE FROM sjt_weights")
        con.execute("DELETE FROM sjt_item_bank")
        
        # 3. Insert new items
        for item in ITEMS:
            con.execute(
                """
                INSERT INTO sjt_item_bank (sjt_q_id, mother_source, mother_id, core_mechanism, scenario_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                [item["sjt_q_id"], item["mother_source"], item["mother_id"], item["core_mechanism"], item["scenario_text"]]
            )
        
        for w in WEIGHTS:
            con.execute(
                """
                INSERT INTO sjt_weights (sjt_q_id, option_val, dimension_code, inherited_weight)
                VALUES (?, ?, ?, ?)
                """,
                [w["sjt_q_id"], w["option_val"], w["dimension_code"], w["inherited_weight"]]
            )
            
        for r in RULES:
            con.execute(
                """
                INSERT INTO sjt_consistency_rules
                    (rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option, penalty_dimension, penalty_weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [r["rule_id"], r["trigger_q_id"], r["trigger_option"], r["verify_q_id"], r["expected_option"], r["penalty_dimension"], r["penalty_weight"]]
            )
            
        print(f"✅ Successfully inserted {len(ITEMS)} questions, {len(WEIGHTS)} weight mappings, and {len(RULES)} rules.")
        print("💡 Restarting FastAPI will use these new questions if main.py reads from questions.json.")
    finally:
        con.close()

if __name__ == "__main__":
    populate()
