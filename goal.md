# lifehack-holland 接手计划

## 定位

`lifehack-holland` 是 `lifehack` 的独立生涯测评服务，负责母版资料、SJT 场景题、作答持久化、规则化评分、职业倾向桥接和报告 API。主项目只通过 HTTP API 或结果快照消费输出，不复制题库、不复算分数、不写本服务数据库。

## 验收口径

- 在线接口只做确定性计算，不调用大模型。
- O*NET/IPIP 原始资料只作为候选母版，不直接成为线上题目。
- 每条候选、每个生产题目、每个选项权重、每条一致性规则都保留血缘。
- 生产题库必须经过人工审核或受控种子文件进入 `backend/data/seed/`。
- 报告接口返回主项目可保存的稳定摘要、完整结果和 source lineage。
- 测试使用临时 DuckDB，不污染 `backend/data/holland.duckdb`。

## 当前核验结论

- 已存在 `lifehack-hollad plan.md`，内容覆盖用户原始需求、SJT 设计原则、规则-模型-策略、DuckDB 表结构和阶段路线。
- 已落地五张核心表：`sjt_item_bank`、`sjt_options`、`sjt_weights`、`sjt_consistency_rules`、`sjt_responses`。选项文案不再依赖生成的 `backend/data/questions.json`，而是和选项级血缘一起进入 `sjt_options`。
- 已落地 FastAPI：`/api/questions`、`/api/submit`、`/api/report/{submission_id}`、`/api/config`、`/api/health`。
- 已落地候选池：从 O*NET/IPIP 生成 328 条 `needs_review` 候选，其中 O*NET 240 条、IPIP 88 条。
- 已落地审核晋级：`question_review` 只允许显式 `approved` 的复核行晋级为生产 seed。
- 已落地主项目职业桥：只读 `lifehack` 的职业目录，写入本项目本地 `cn_occupation_riasec_map`。
- 已补原始母版资料快照：`import_raw_materials.py` 读取 `config/source_registry.json` 和 `config/question_generation.json`，把 O*NET Interests、O*NET Task Statements、IPIP 题项写入本地 raw 表，并为每一行保留来源版本、文件角色、文件路径、行号、源主键和 acquisition mode。
- 复核后补充核验：现有测试全 PASS，`audit_question_lineage.py` 全 PASS；生产题库 18 题、42 个选项均已补显式选项级血缘，验证题选项以 `scoring_role=consistency_check_only` 说明其只参与一致性规则、不直接计分。
- 接手复核后补齐主项目适配：独立测评前端已改为主项目一致的浅色纸面、薄荷绿和 IBM Plex/Noto Serif 风格；结果页不再展示“惩罚前”等内部计算词。后端 `/api/questions` 对动态出现的验证题也标记为必答，前端会要求每个可见情境题完成后才能继续。
- 主项目联调复核已通过：真实提交、`/api/report/{submission_id}`、core 快照同步链路可用；并列分维度现在按 `backend/dimensions_config.json` 的配置顺序稳定排序，避免同一 `submission_id` 多次请求得到不同 RIASEC top3。

## 已补的接手修正

- 候选池增加 source counts、selection policy、review priority 和 quality flags，能解释为什么从几万行母版资料中选出当前复核批次。
- 复核 CSV 增加 `review_priority` 和 `quality_flags_json`，人工审核可以按优先级处理，而不是从几百条候选里盲选。
- 新增 `question_audit` 和 `audit_question_lineage.py`，用于在候选池和生产 seed 晋级前做血缘门禁。
- 外部来源 URL 迁入 `config/source_registry.json`，抓取脚本只读取配置，不在脚本里维护来源地址。
- 旧的原始资料导入脚本已改为配置驱动和行级血缘驱动，避免几千条 O*NET/IPIP 母版材料在进入候选池前断链；真实导入已验证：`raw_onet_interests` 8307 行、`raw_onet_task_statements` 18796 行、`raw_ipip_items` 88 行。
- `/api/report/{submission_id}` 增加 `decision_inputs`，供主项目保存稳定摘要，同时保留完整 `source_lineage`。
- 生产题库种子从题目级血缘回退升级为选项级血缘；复核晋级流程会为每个 approved option 自动补齐候选来源、母版 ID、原始文本、权重和复核备注，避免从 O*NET/IPIP 候选转正式题时断链。
- 接手验证后已把选项文案纳入 `sjt_options`，`/api/questions` 直接从表读取题目、选项和审核血缘；删除旧的硬编码题库入库脚本和生成式 `questions.json`，只保留 `populate_golden_bank.py` 作为受控 seed 入库入口。
- 接手复核继续收紧前端可见文案：结果页不再展示“降低信号权重”或具体调整数值，改为“谨慎参考”的家庭可读表达，并新增单测防止“惩罚/扣分”等内部调整词回流到结果页。
- 职业桥接边界已补回归测试：`build_mapping` 使用临时 main DuckDB 和本地 Holland DuckDB 验证只读读取 `fa_dim_career_occupation`、只在本项目生成 `cn_occupation_riasec_map`，并检查 `confidence/review_status/lineage_json` 中的 `read_mode=duckdb_read_only`、source table 和 source primary key；当前 `python3 -m unittest discover -s tests -v` 为 13 项全 PASS。

## 下一步顺序

1. 先导入原始母版资料 raw snapshot，并确认 `raw_material_import_runs` 和三张 raw 表的行级血缘可追溯。
2. 再用 `audit_question_lineage.py` 和单元测试守住候选、选项文案、权重、规则和报告契约。
3. 从候选池按 `review_priority` 拆小批复核，人工把 O*NET/IPIP 母版材料改写为中文高中/大学情境题。
4. 每批只晋级少量高质量题，保持题库短、准、可解释，并通过 `populate_golden_bank.py` 入库到 `sjt_options/sjt_weights`。
5. 主项目只同步 `submission_id` 对应报告，并把 `decision_inputs`、`recommended_cn_occupations`、`source_lineage` 写入案例快照。
6. 后续如引入离线大模型，只能生成候选草稿；进入生产前仍必须通过同一复核和血缘审计。
