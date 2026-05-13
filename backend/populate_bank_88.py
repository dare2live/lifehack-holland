"""
Script to populate DuckDB with a comprehensive set of SJT questions.
Includes the original O*NET based questions + newly translated IPIP Jungian questions.
"""
import json
import duckdb
from backend.config import DB_PATH, PROJECT_ROOT

# ═══════════════════════════════════════════════════════════════════
# GENERATED QUESTION BANK (Translated from Master Sources)
# ═══════════════════════════════════════════════════════════════════

BANK = [
    # ── Module 1: Pure Holland Scenarios (O*NET based) ──
    {
        "q_id": "Q_Holland_Gala",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_1.A.1",
        "mechanism": "L2_influence_vs_hands_on",
        "text": "你是一年级新生晚会的总导演。演出前20分钟，主舞台的音响设备突然冒烟罢工了，全场开始有些躁动。此时你的第一反应是：",
        "options": [
            {"val": "A", "text": "马上走到台前，用备用大喇叭幽默地安抚前排焦躁的观众，并让主持人临场互动拖延时间", "weights": [("Holland_E", 1.5), ("Holland_S", 1.0)]},
            {"val": "B", "text": "立刻冲到总电闸处排查物理线路，拆开音响外壳查看是不是保险丝烧了", "weights": [("Holland_R", 1.5)]},
            {"val": "C", "text": "在后台冷静地给有经验的学长打电话，快速搜索音响故障的常见排查手册", "weights": [("Holland_I", 1.5), ("Holland_C", 0.5)]}
        ]
    },
    {
        "q_id": "Q_Holland_Gala_verify",
        "mother_source": "SYSTEM_RULE",
        "mother_id": "VERIFY_01",
        "mechanism": "L3_verify_E",
        "text": "【追问】刚才你选择了“安抚观众/寻求互动”，但如果此时那个本来负责临场互动的主持人紧张得躲在后台死活不肯上台，你会：",
        "options": [
            {"val": "X", "text": "算了不求他了，自己直接冲上台，脱稿给大家讲个段子暖场", "weights": []},
            {"val": "Y", "text": "觉得非常头疼且尴尬，只能让灯光师放点背景音乐，大家安静等着吧", "weights": []},
            {"val": "Z", "text": "叹口冷气，转身去找音控组的同学一起排查线路问题", "weights": []}
        ]
    },
    {
        "q_id": "Q_Holland_Poster",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_2.B.3",
        "mechanism": "L2_artistic_vs_conventional",
        "text": "你的小组要设计一张社团招新的海报。另一个组员坚持要用非常规矩、字很大的“居委会风格”，而你觉得应该用极其抽象、艺术感拉满的“赛博朋克风”。争执不下时，你会：",
        "options": [
            {"val": "A", "text": "各做各的方案，明天让全班投票决定，用数据说话", "weights": [("Holland_I", 1.0)]},
            {"val": "B", "text": "主动约TA去奶茶店聊聊，倾听TA的想法，找个能兼顾双方审美的折中方案", "weights": [("Holland_S", 1.5)]},
            {"val": "C", "text": "上网搜历年获奖海报的点击率和风格分布，用事实去说服TA", "weights": [("Holland_C", 1.5), ("Holland_E", 1.0)]},
            {"val": "D", "text": "自己另外起草一份天马行空的草图，自己完成自己的设计", "weights": [("Holland_A", 1.5)]}
        ]
    },
    {
        "q_id": "Q_Holland_Poster_verify",
        "mother_source": "SYSTEM_RULE",
        "mother_id": "VERIFY_02",
        "mechanism": "L3_verify_S",
        "text": "【追问】如果你选择了“折中方案”，但最终大家还是投票选了那个“居委会风格”，你内心的真实想法是：",
        "options": [
            {"val": "X", "text": "尊重大家的意见，说明这个方案确实更有受众市场", "weights": []},
            {"val": "Y", "text": "有点不服气，觉得他们不懂审美，但嘴上不说", "weights": []},
            {"val": "Z", "text": "依然坚持提出修改意见，用对比图展示两种方案的优劣", "weights": []}
        ]
    },
    {
        "q_id": "Q_Holland_TechClub",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_4.A.2",
        "mechanism": "L2_research_vs_enterprise",
        "text": "你是科技社团的骨干。这学期社团得到了一笔5000元的赞助费，你最希望用这笔钱来：",
        "options": [
            {"val": "A", "text": "全部用来购买最顶级的实验传感器和服务器算力，搞一个硬核技术项目", "weights": [("Holland_R", 1.0), ("Holland_I", 1.5)]},
            {"val": "B", "text": "拿出一大半钱办一场全校规模的“科技创新大赛”，拉拢更多赞助并扩大影响力", "weights": [("Holland_E", 1.5)]},
            {"val": "C", "text": "请校外的专业导师来给全社团开几场系统的技术培训讲座，提升大家的平均水平", "weights": [("Holland_S", 1.0), ("Holland_C", 1.0)]}
        ]
    },
    {
        "q_id": "Q_Holland_Lab",
        "mother_source": "ONET_IP",
        "mother_id": "ONET_2.A.1",
        "mechanism": "L2_logic_vs_feeling",
        "text": "在物理实验室，你的搭档不小心摔碎了一个昂贵的仪器。老师问起时，你会：",
        "options": [
            {"val": "A", "text": "如实向老师陈述刚才发生的所有细节（角度、力度等），帮忙分析仪器损坏的物理原因", "weights": [("Holland_I", 1.5)]},
            {"val": "B", "text": "主动替搭档承担一半责任，并在事后安慰他不要太难过", "weights": [("Holland_S", 1.0)]},
            {"val": "C", "text": "赶紧去器材室看看有没有备用的零件，尝试自己动手把它修好", "weights": [("Holland_R", 1.5)]}
        ]
    },

    # ── Module 2: Pure MBTI Scenarios (IPIP Jungian Translated) ──
    {
        "q_id": "Q_MBTI_1",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_1",
        "mechanism": "E_vs_I",
        "text": "学校组织“未来城市”设计大赛，需要提交一份创意方案。在构思阶段，你会倾向于：",
        "options": [
            {"val": "A", "text": "立刻拉上几个同学去食堂边吃边聊，在激烈的头脑风暴和思想碰撞中寻找灵感。", "weights": [("MBTI_E", 1.5)]},
            {"val": "B", "text": "一个人去图书馆找个安静的角落，查阅资料并独自深思熟虑，直到构思完整。", "weights": [("MBTI_I", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_2",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_2",
        "mechanism": "J_vs_P",
        "text": "你作为社团长负责主持新学期的第一次全员大会。在会议进行时，你会：",
        "options": [
            {"val": "A", "text": "严格按照提前写好的议程表推进，控制每个人的发言时间，确保按时结束。", "weights": [("MBTI_J", 1.5)]},
            {"val": "B", "text": "保持灵活，如果大家对某个话题很感兴趣，就顺着聊下去，哪怕偏离了原定计划。", "weights": [("MBTI_P", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_3",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_3",
        "mechanism": "T_vs_F",
        "text": "你和一个同学组队做项目，但他最近经常迟到且任务敷衍。这时候你会：",
        "options": [
            {"val": "A", "text": "直接找他严肃谈话，指出他的行为拖慢了进度，要求他立刻改正。", "weights": [("MBTI_T", 1.5)]},
            {"val": "B", "text": "觉得当面指出太伤和气，试着委婉地问他最近是不是压力大，或者干脆自己多做一点。", "weights": [("MBTI_F", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_6",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_6",
        "mechanism": "S_vs_N",
        "text": "在参加一场关于“人工智能未来”的校园讲座时，你最感兴趣的部分通常是：",
        "options": [
            {"val": "A", "text": "AI 现在具体能帮我们自动写代码、做作业或者提高多少效率等实际应用。", "weights": [("MBTI_S", 1.5)]},
            {"val": "B", "text": "AI 是否会产生自我意识、如何重塑人类社会结构等深层次的思想和理论。", "weights": [("MBTI_N", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_9",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_9",
        "mechanism": "E_vs_I",
        "text": "经过一上午紧张的期中考试，中午有一个半小时的休息时间。你更倾向于：",
        "options": [
            {"val": "A", "text": "和一大群朋友去热闹的餐厅聚餐，激烈讨论考试题目，放松心情。", "weights": [("MBTI_E", 1.5)]},
            {"val": "B", "text": "买个三明治回到安静的教室，或者只和一个最要好的朋友在操场散散步。", "weights": [("MBTI_I", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_12",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_12",
        "mechanism": "J_vs_P",
        "text": "周末有一整天的自由时间，没有任何硬性作业。早上醒来时，你通常会：",
        "options": [
            {"val": "A", "text": "立刻在脑海中或纸上列出今天上午、下午和晚上的具体计划，并按部就班执行。", "weights": [("MBTI_J", 1.5)]},
            {"val": "B", "text": "看心情决定，也许先玩会儿手机，顺其自然地度过这一天，看会发生什么。", "weights": [("MBTI_P", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_12_verify",
        "mother_source": "SYSTEM_RULE",
        "mother_id": "VERIFY_MBTI_J",
        "mechanism": "L3_verify_J",
        "text": "【追问】如果今天上午你计划好要去图书馆，但突然下起了倾盆大雨，你的感受是：",
        "options": [
            {"val": "X", "text": "觉得非常烦躁，计划被打乱的感觉让我很不舒服。", "weights": []},
            {"val": "Y", "text": "无所谓，那就在家看看剧，随便做点什么也行。", "weights": []},
            {"val": "Z", "text": "迅速调整计划，把下午在室内要做的作业挪到上午来做。", "weights": []}
        ]
    },
    {
        "q_id": "Q_MBTI_22",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_22",
        "mechanism": "S_vs_N",
        "text": "老师让你写一篇关于“气候变化”的读书报告。在动笔之前，你脑海中最先浮现的是：",
        "options": [
            {"val": "A", "text": "具体的图表、温度数据、受灾地区的具体案例和引用的文献出处。", "weights": [("MBTI_S", 1.5)]},
            {"val": "B", "text": "气候变化对人类文明生存的影响、环保理念的变迁等宏大的整体概念。", "weights": [("MBTI_N", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_23",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_23",
        "mechanism": "T_vs_F",
        "text": "面临文理分科或大学选专业的重大抉择时，你通常会怎么做决定？",
        "options": [
            {"val": "A", "text": "查阅各专业的就业率、薪资前景和自己的学科分数，理性客观地推导出最优解。", "weights": [("MBTI_T", 1.5)]},
            {"val": "B", "text": "抛开冷冰冰的数据，闭上眼睛问自己内心真正热爱什么，感受哪条路会让自己更快乐。", "weights": [("MBTI_F", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_32",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_32",
        "mechanism": "J_vs_P",
        "text": "班主任交给你一项全新的班级墙报任务。你更希望班主任怎么安排？",
        "options": [
            {"val": "A", "text": "给你一份清晰的要求清单，明确告诉你什么时候交、版面怎么分、主题是什么。", "weights": [("MBTI_J", 1.5)]},
            {"val": "B", "text": "只告诉你“做个关于春天的墙报”，然后完全放权，让你自己去摸索和自由发挥。", "weights": [("MBTI_P", 1.5)]}
        ]
    },
    {
        "q_id": "Q_MBTI_41",
        "mother_source": "IPIP_Jungian",
        "mother_id": "MBTI_88_41",
        "mechanism": "E_vs_I",
        "text": "如果有同学要向别人描述你，你觉得他们最可能会用以下哪种描述？",
        "options": [
            {"val": "A", "text": "一个充满活力的团队活跃分子，喜欢在人群中表达和互动。", "weights": [("MBTI_E", 1.5)]},
            {"val": "B", "text": "一个安静、深思熟虑的人，更喜欢独自思考或进行深度的一对一交流。", "weights": [("MBTI_I", 1.5)]}
        ]
    }
]

RULES = [
    {
        "trigger_q_id": "Q_Holland_Gala",
        "trigger_option": "A",
        "verify_q_id": "Q_Holland_Gala_verify",
        "expected_option": "Y",
        "penalty_dimension": "Holland_E",
        "penalty_weight": -2.0
    },
    {
        "trigger_q_id": "Q_Holland_Poster",
        "trigger_option": "B",
        "verify_q_id": "Q_Holland_Poster_verify",
        "expected_option": "Y",
        "penalty_dimension": "Holland_S",
        "penalty_weight": -2.0
    },
    {
        "trigger_q_id": "Q_MBTI_12",
        "trigger_option": "A",
        "verify_q_id": "Q_MBTI_12_verify",
        "expected_option": "Y",
        "penalty_dimension": "MBTI_J",
        "penalty_weight": -2.0
    }
]

def populate():
    print("Populating independent dual-track (MBTI & Holland) question bank into DuckDB...")
    con = duckdb.connect(DB_PATH)
    
    con.execute("DELETE FROM sjt_responses")
    con.execute("DELETE FROM sjt_weights")
    con.execute("DELETE FROM sjt_consistency_rules")
    con.execute("DELETE FROM sjt_item_bank")
    
    questions_for_frontend = {}
    
    for item in BANK:
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

    for rule in RULES:
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

    print(f"✅ Successfully inserted {len(BANK)} independent questions, mapped weights, and {len(RULES)} rules.")

if __name__ == "__main__":
    populate()
