> 接手说明：本文件保留原始需求和初版蓝图；当前执行状态、验收口径和下一步顺序见 `goal.md`。文件名中的 `hollad` 为历史拼写，暂不重命名，避免外部引用失效。

双核生涯测评引擎 (Integrated SJT Assessment Engine) 实施蓝图0. 原始用户需求追踪 (User Requirements Traceability)以下为该项目发起人的所有原始需求记录（按时间顺序归档），本蓝图的所有架构、顶层设计与业务逻辑均严格响应以下需求："MBTI和霍兰德测试是啥""有官方模版吗？问题是啥样的？适合作为问卷向高中生发放吗""有哪些github的项目在做简化版题库，是否可以优化，比如【问题示例 1（R型）： 你是否喜欢修理机械设备？问题示例 2（I型）： 你是否喜欢研究某种复杂的科学理论？问题示例 3（S型）： 你是否喜欢教别人做某件事或发表演说？】这种属于自我判断，可是问卷的目的就是得出结论，如果已经能自我判断了，还要这玩意干啥，应该有那种做成生活场景类的问题，也就是把这种枯燥的自我判断的问题转换成代入感强的问题，这样才能得出更贴近实际的答案""为了避免重复造轮子，我可以借助哪些github项目呢，具体应该怎么优化问题呢""你结合我们的对话写个详细的方案""我用的是duckdb，pandas退役了，前端是html，后端是fastapi，怎么最小改动实现这个项目""请你按照这个思路设计一个完整的可落地的方案，先把架构搭起来，这个项目会是我现有项目的一个功能，我的设想是这个项目只做问卷数据库和后端计算以及输出结果之类的，主项目（lifehack）是前端用于展示问卷和显示结果，你先给我出完整的方案，然后我切换到antigravity做实施。""可以，但不要重复造轮子，我们可以找到成熟的评价体系题目作为母版，在此基础上适配高三学生的情景，这样权重参数就不用拍脑门了，请你研究一下""把这些补充到方案里。越详细越好，能让在antigravity里的你直接上手""我有个想法，可以用一套问卷把两种测试整合到一起""在canvas里把所有这些内容都整合用markdown写成非常细致的实施方案""母版怎么抓没写啊，你完整的写一个""扫描聊天记录，把遗漏的都补进去""SJT 题目设计的“被迫选择（Ipsative）”原则（如何设计对冲选项）。这是啥意思，跟在母版上优化有冲突么？倒不一定非得和母版问题一一对应，最后可以综合母版题目来设计，说到这里，是不是可以设计成多级的数据血缘追踪，比如母版肯定是不动的，第一级是合并相似的，第二级是适配高中生活场景，第三级是mbti与holland整合到同一个题目，第四级是生成题库，不一定以我说的为准啊，你发挥你的知识和经验来设计分层等级，你是专家""还有一个注意事项，就是场景题目设计不要有那种一眼看出来题目意图的问题，填写人会据此写出有利于自己的答案，应该尽量开放式并且设计后续的关联题目来验证，但最后都要通过数据血缘回溯到母版的打分参数，至于前后回答不一致的中间参数倒是可以设置一下，用于判断到底回到母版题目时算怎么样的答案，也就是说问卷题目的答案要最终能够回答母版问题，但要注意我不会引入大模型来判断，所以要设计规则来实现，也就是规则（判断题目答案）、模型（母版参数标准）、策略（最终结论）这么个体系""你把这个补充进方案里啊""你把我发出的所有的对话原封不动的都整理出来作为用户需求放到最前面""3. 多级数据血缘追溯体系 (Data Lineage) 这里没有写考生回答问卷后怎么用于回答母版题目并借助母版参数进行打分和输出结果，缺少太多细节，请你补充""补充，并且把我说的题目设计原则的对应方案也写进去，就是“就是场景题目设计不要有那种一眼看出来题目意图的问题，”这一段，请你仔细点，详细的针对我的每一个问题里的细节设计方案，然后从顶层设计的角度来规划整体的架构"1. 顶层架构设计：解耦与专家决策系统本系统从顶层设计上摒弃了传统的“问卷加减分”单线逻辑，构建了一个左侧轻量交互、右侧重度数据回溯的专家决策网。大模型（LLM）绝对不进入线上业务核心，线上判决全部依靠纯净的数据驱动。1.1 物理与逻辑双解耦架构左半场 (Lifehack 前端 - UI与交互): 基于 HTML/JS 和 SurveyJS 引擎。职责极致单一：渲染题干、收集用户点击、利用 visibleIf 触发验证题，将扁平的 JSON 丢给后端。不包含任何算分逻辑。右半场 (微服务后端 - 算力与判定): 基于 FastAPI + DuckDB。接收 JSON 后，不写 if/else 代码，而是将数据流引入“规则-模型-策略”的数据库决策网中。1.2 专家系统三层决策网 (核心算分哲学)所有前端传来的数据，必须依次穿透以下三层，才能输出最终结果：规则层 (Rule Layer) - 【过滤与惩罚】： 扮演“测谎仪”。拦截前端传来的 JSON 答案，判断是否存在“主场景装作高尚，但在关联验证题中暴露退缩”的前后不一致行为。如果触发，生成“惩罚中间变量”。模型层 (Model Layer) - 【血缘映射】： 扮演“翻译官”。经过规则层幸存的答案，在这里严格对照底层数据词典，映射回 O*NET 或 IPIP 母版参数，提取对应的维度与因子载荷（基础权重），生成“基础中间变量”。策略层 (Strategy Layer) - 【聚合输出】： 扮演“法官”。利用 DuckDB 的关系代数，将基础变量与惩罚变量聚合，得出最终各个维度的净得分，并按排名组装成结构化 JSON 报告。2. 题库防伪装设计详案 (SJT 设计范式)为了彻底根除用户“一眼看穿测试意图并据此自我修饰”的问题，题目设计必须严格遵循以下三大机制：2.1 隐匿测试意图 (Intention Obfuscation)原则： 永远不要问态度，只问极端情境下的第一反应。错误示范（一眼看穿）： “作为班委，你喜欢站在讲台上发表演说吗？”（为了显得有领导力，学生大概率选“喜欢”）。正确示范（隐匿意图）： “迎新晚会彩排时，音响突然烧坏了，距离开场还有10分钟。作为负责人的你，第一反应是：”（学生此时的注意力被紧急情境转移，无暇去思考这道题到底在测 E 还是 I，从而暴露出更真实的本能反应）。2.2 价值对冲与被迫选择 (Ipsative Method)原则： 废除“好坏之分”。由于我们把两套测试整合（MBTI + Holland），每一个选项都必须代表不同的心理机制，且具有不可避免的代价。让不同的母题在选项中“打架”。在上述“音响坏了”的情境中设置对冲选项：选项 A： 马上安抚前排焦躁的观众，让主持人临场互动拖延时间。（收益： 危机公关，影响他人；代价： 不解决物理问题。指向母版： Holland_E 企业型，MBTI_E 外向型）。选项 B： 立刻冲到总电闸处排查物理线路和保险丝。（收益： 解决核心问题；代价： 可能导致现场失控。指向母版： Holland_R 现实型，MBTI_T 思考型）。说明： 这种设计使得任何选择都有合理的逻辑支撑，彻底消除了社会期望带来的“好学生偏见”。2.3 动态追问与规则惩罚 (Dynamic Probing & Lie Detection)原则： 假设用户可能会为了虚荣心选择看似“光鲜”的选项，必须配置隐藏的验证题。主场景触发： 学生在某题中选择了“拿着商业计划书去拉赞助”（试图表现出强大的 E 型外向特质）。隐藏验证激活： SurveyJS 捕捉到该选项，动态在后续页面插入验证题：“当你走进第一家店，老板态度很不耐烦地让你出去，你此刻心里的真实感受和下一步行动是？”真实本能暴露： 如果学生选了“觉得丢脸，决定回学校发传单算了吧”（暴露了脆弱或内向的真实本能）。中间参数生成： 该生的答卷进入后端“规则层”时，前后不一致的特征被捕获，系统生成惩罚参数（如：Holland_E -2.0 分），直接抵消其在主场景中骗取的高分。3. 多级数据血缘架构与回溯打分 (Data Lineage & Backward Scoring)题目的设计必须能倒推回科学依据，得分的计算必须能沿原路返回母版。3.1 题库生成的 5 级正向血缘 (开发期)L0_Raw (母版原点): O*NET (RIASEC) 任务载荷与 IPIP (MBTI) 原始题库。L1_Cluster (语义聚合): 合并相似底层特质。例如“修理汽车”与“电工布线”聚合成“物理与机械实操”。L2_Matrix (双核交汇): 寻找 MBTI 与 Holland 的共性。例如 (MBTI_I 内向) + (Holland_I 研究) = 深度独立钻研。L3_SJT_Draft (情境转译): 将 L2 的特征放入高三场景中碰撞（对冲选项草稿）。L4_ItemBank (生产题库): 最终进入 DuckDB sjt_weights 表的固定 JSON 与权重系数。3.2 答案倒推回溯算分流 (线上运行期)当学生提交答卷后，数据如何通过“规则-模型-策略”体系倒推回 L0 母版参数并得出结论：输入接收： Lifehack 前端传来扁平 JSON（如 {"Q_Gala": "A", "Q_Gala_verify": "C"}）。过检规则层 (Rule Layer - 中间参数生成)：DuckDB 扫描 sjt_consistency_rules 表。检查该 JSON 中是否命中了规则组合。判定结果： 命中前后矛盾规则，生成扣分项（如：维度 MBTI_E，扣分 -1.5）。穿透模型层 (Model Layer - 提取底层参数)：DuckDB 扫描 sjt_weights 表。根据用户的有效选项，向上追溯到 L4->L0 的映射关系。判定结果： 提取底层母版赋予该选项的原始权重（如：选项 A 对应 Holland_C，底层参数 +2.0）。策略层合并输出 (Strategy Layer)：通过 SQL 的聚合计算公式：最终维度得分 = Σ(模型层提取的基础参数) + Σ(规则层生成的惩罚参数)。按最终得分高低对维度进行排序，输出最终结论结构体给前端呈现。4. 数据库基建方案 (DuckDB DDL)这三层逻辑被物理固化在以下数据库结构中。-- ==========================================
-- 【审计底稿】题库元数据表 (正向血缘 L4 -> L0)
-- ==========================================
CREATE TABLE IF NOT EXISTS sjt_item_bank (
    sjt_q_id VARCHAR PRIMARY KEY,      
    mother_source VARCHAR,             -- L0来源 (如 ONET_IP, IPIP_Jung)
    mother_id VARCHAR,                 -- L0原始题号
    core_mechanism VARCHAR,            -- L1/L2 核心机制
    scenario_text VARCHAR              -- 情境描述 (隐藏意图)
);

-- ==========================================
-- 【模型层】绝对标准映射 (底层参数提取)
-- ==========================================
CREATE TABLE IF NOT EXISTS sjt_weights (
    sjt_q_id VARCHAR,
    option_val VARCHAR,                
    dimension_code VARCHAR,            -- 如 'Holland_I', 'MBTI_J'
    inherited_weight FLOAT,            -- 继承自母版的因子载荷基础分
    FOREIGN KEY (sjt_q_id) REFERENCES sjt_item_bank(sjt_q_id)
);

-- ==========================================
-- 【规则层】关联验证与惩罚 (判断前后矛盾)
-- ==========================================
CREATE TABLE IF NOT EXISTS sjt_consistency_rules (
    rule_id VARCHAR PRIMARY KEY,
    trigger_q_id VARCHAR,        -- 主场景题
    trigger_option VARCHAR,      -- 试图伪装的高光选项
    verify_q_id VARCHAR,         -- 隐藏验证题
    expected_option VARCHAR,     -- 暴露原形的退缩选项
    penalty_dimension VARCHAR,   -- 要剥夺的特质分 (如 Holland_E)
    penalty_weight FLOAT         -- 惩罚扣分值 (如 -2.0)
);

-- ==========================================
-- 事实表 (记录答卷)
-- ==========================================
CREATE TABLE IF NOT EXISTS sjt_responses (
    submission_id UUID DEFAULT uuid(),
    user_id VARCHAR,                   
    raw_answers JSON,                  -- SurveyJS 传来的原始作答
    created_at TIMESTAMP DEFAULT current_timestamp
);
5. 核心算分引擎 (SQL 纯算力实现策略层)FastAPI 后端的 GET /report 接口被调用时，通过以下聚合视图完成打分流：WITH flattened_answers AS (
    -- 1. 解包：展平用户的 JSON 答案
    SELECT 
        r.submission_id,
        ans.key AS sjt_q_id,
        ans.value AS option_val
    FROM sjt_responses r,
         UNNEST(from_json(r.raw_answers, 'MAP(VARCHAR, VARCHAR)')) AS ans
    WHERE r.submission_id = ?
),
base_scores AS (
    -- 2. 模型层映射：提取底层基础参数
    SELECT 
        w.dimension_code,
        SUM(w.inherited_weight) AS score
    FROM flattened_answers fa
    JOIN sjt_weights w ON fa.sjt_q_id = w.sjt_q_id AND fa.option_val = w.option_val
    GROUP BY w.dimension_code
),
penalty_scores AS (
    -- 3. 规则层判定：激活测谎与惩罚中间参数
    SELECT 
        cr.penalty_dimension AS dimension_code,
        SUM(cr.penalty_weight) AS score
    FROM sjt_consistency_rules cr
    JOIN flattened_answers fa_trigger 
      ON fa_trigger.sjt_q_id = cr.trigger_q_id AND fa_trigger.option_val = cr.trigger_option
    JOIN flattened_answers fa_verify 
      ON fa_verify.sjt_q_id = cr.verify_q_id AND fa_verify.option_val = cr.expected_option
    GROUP BY cr.penalty_dimension
)
-- 4. 策略层：聚合输出最终打分
SELECT 
    COALESCE(b.dimension_code, p.dimension_code) AS final_dimension,
    COALESCE(b.score, 0) + COALESCE(p.score, 0) AS final_total_score
FROM base_scores b
FULL OUTER JOIN penalty_scores p ON b.dimension_code = p.dimension_code
ORDER BY final_total_score DESC;
6. 母版数据抓取与 LLM 批量转译工作流 (线下准备期)为了填充系统，必须建立自动化的“母题转译”管道，大模型仅在此环节发挥作用。数据源获取： 编写 Python 脚本从 O*NET Database (如 Task Statements 表) 和 IPIP 开源代码库中抓取含有相关系数的源数据（导出为 source.csv）。LLM 批量生产 (Offline)：编写 Python 脚本循环调用 LLM API，使用严密的 Prompt 指导转译：Prompt 约束 1： 设定为高三或大学迎新/考试等日常场景。Prompt 约束 2： 严格执行“被迫选择”，把传入的 2-3 个特质设计为合理的 A/B/C 选项。Prompt 约束 3： 如果某选项带有“高光伪装”属性，必须生成一道后置的“追问题”和扣分规则。要求输出格式： 严格的 JSON，包含题目、选项及对应权重。落表入库： 人工抽检这批 JSON 后，利用 seed_data.py 将其解析并灌入 DuckDB 的三个元数据表中。7. 阶段实施路线图 (Roadmap for Antigravity)在切换至开发环境后的具体执行步骤：Phase 1: 基础设施与数据播种 (Days 1-2)在 antigravity 创建 init_db.py 建立上述 4 张核心数据表。创建 seed_data.py，手工编造 2 组完整的测试题（包含主场景+隐匿验证+惩罚规则+底层参数映射），模拟 L4 到 L0 的完整血缘关系并落库。Phase 2: 微服务接口与算分闭环 (Days 3-4)开发 FastAPI 后端 main.py。实现 /submit 接口以接收并保存 JSON。实现 /report 接口，调通复杂的 SQL 聚合视图，确保惩罚规则能正确抵消基础分数。Phase 3: 前端联调与防伪装交互 (Days 5-7)在主项目 Lifehack 中配置 SurveyJS。配置 visibleIf 逻辑实现“动态追问”（如果选了特定装逼选项，才显示隐藏验证题）。将后端返回的最终维度得分渲染为动态图表。Phase 4: 题库批量生成与试运行 (Ongoing)启动线下 LLM 转译管道，生成 30-40 道高质量题目入库。开启小样本灰度测试，观察常模分布。

母版数据源精确查找指南为了让你的测评系统具备坚实的学术底座，以下是两个数据库的完整全称及精确的获取方法：1. O*NET Database (用于霍兰德 RIASEC 母题与权重)全称： Occupational Information Network (美国职业信息网络)背景： 由美国劳工部（US Department of Labor）主导开发的免费、权威职业特征数据库，是目前全球范围内使用最广的霍兰德兴趣常模数据库。便于查找的精确路径：搜索关键词： O*NET Resource Center Database 或 O*NET Production Database。官方数据下载页： 访问 www.onetcenter.org/database.html。推荐下载格式： 选择 Text Format (包含一系列逗号或制表符分隔的纯文本文件)，这种格式极其适合你直接用 Pandas 或 DuckDB 读取入库。你需要重点关注的表文件：Task Statements.txt：包含数千个具体职业任务的详细描述（如“使用微观技术在实验室分离细胞”），这是我们喂给大模型用来转译高中 SJT 情境题的绝佳灵感素材库。Interests.txt：这张表里记录了特定职业/任务在 RIASEC 六个维度上的精确数值权重（Scale Values），这就是你不需“拍脑门”直接继承的底稿。2. IPIP 开源代码库 (用于 MBTI/荣格心理特质母题)全称： International Personality Item Pool (国际人格项目池)背景： 由俄勒冈研究所（Oregon Research Institute）等学术机构共同维护的全球最大、基于公有领域（Public Domain，完全免费且无版权限制）的心理学问卷原题库。便于查找的精确路径：搜索关键词： IPIP ORI 或直接访问其古早但极其硬核的官方网站 ipip.ori.org。寻找 MBTI 替代量表的关键提示：注意，由于“MBTI”是 Myers-Briggs 公司的注册商业商标，正规学术开源库中绝不会直接使用 MBTI 这个词。你需要精准定位的量表名称：在 IPIP 网站中，寻找名为 "Jungian Personality Scale"（荣格人格量表）或标有 "Jungian types" 的相关量表。或者寻找测量 Big Five (大五人格) 的量表（大五人格与 MBTI 维度有极高的对应性：外向性对应 E/I，开放性对应 N/S，宜人性/尽责性对应 F/T 和 J/P）。IPIP 网站会直接提供每一道题目的文本（如 "Love large parties"）以及它对特定性格维度（如 Extraversion）的相关系数/载荷（+ 键或 - 键计分）。
