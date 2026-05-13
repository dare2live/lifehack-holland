"""
init_db.py — Create the 4 core DuckDB tables for the SJT Assessment Engine.

Tables:
  1. sjt_item_bank          — Question metadata with data lineage (L4 → L0)
  2. sjt_weights             — Option → dimension → weight mapping (Model Layer)
  3. sjt_consistency_rules   — Contradiction detection & penalty rules (Rule Layer)
  4. sjt_responses           — Student submission fact table

Usage:
    python -m backend.init_db          # from project root
    python backend/init_db.py          # direct execution
"""
import duckdb
from backend.config import DB_PATH


DDL_STATEMENTS = [
    # ──────────────────────────────────────────────────────────────
    # 【审计底稿】题库元数据表 (正向血缘 L4 → L0)
    # ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sjt_item_bank (
        sjt_q_id       VARCHAR PRIMARY KEY,   -- 题目唯一ID, e.g. 'Q_Gala'
        mother_source  VARCHAR,               -- L0来源 (如 ONET_IP, IPIP_Jung)
        mother_id      VARCHAR,               -- L0原始题号
        core_mechanism VARCHAR,               -- L1/L2 核心机制
        scenario_text  VARCHAR,               -- 情境描述 (隐藏意图)
        source_version VARCHAR,               -- 母版/题库版本
        transform_level VARCHAR,              -- L0/L1/L2/L3/L4 转化层级
        review_status  VARCHAR,               -- 审核状态
        lineage_json   VARCHAR                -- 完整血缘 JSON
    );
    """,

    # ──────────────────────────────────────────────────────────────
    # 【模型层】绝对标准映射 (底层参数提取)
    # ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sjt_weights (
        sjt_q_id         VARCHAR,
        option_val       VARCHAR,              -- 选项值, e.g. 'A', 'B', 'C'
        dimension_code   VARCHAR,              -- 维度代码, e.g. 'Holland_I', 'MBTI_J'
        inherited_weight FLOAT,                -- 继承自母版的因子载荷基础分
        source_version   VARCHAR,              -- 该权重的来源版本
        review_status    VARCHAR,              -- 该权重的审核状态
        lineage_json     VARCHAR,              -- 选项/权重级血缘 JSON
        FOREIGN KEY (sjt_q_id) REFERENCES sjt_item_bank(sjt_q_id)
    );
    """,

    # ──────────────────────────────────────────────────────────────
    # 【规则层】关联验证与惩罚 (判断前后矛盾)
    # ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sjt_consistency_rules (
        rule_id           VARCHAR PRIMARY KEY,
        trigger_q_id      VARCHAR,             -- 主场景题
        trigger_option    VARCHAR,             -- 主场景选项
        verify_q_id       VARCHAR,             -- 隐藏验证题
        expected_option   VARCHAR,             -- 验证场景选项
        penalty_dimension VARCHAR,             -- 要剥夺的特质分 (如 Holland_E)
        penalty_weight    FLOAT,               -- 惩罚扣分值 (如 -2.0)
        source_version    VARCHAR,             -- 规则来源版本
        review_status     VARCHAR,             -- 规则审核状态
        lineage_json      VARCHAR              -- 规则完整血缘 JSON
    );
    """,

    # ──────────────────────────────────────────────────────────────
    # 事实表 (记录答卷)
    # ──────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS sjt_responses (
        submission_id  VARCHAR DEFAULT (uuid()::VARCHAR),
        user_id        VARCHAR,
        raw_answers    JSON,                   -- SurveyJS 传来的原始作答
        created_at     TIMESTAMP DEFAULT current_timestamp
    );
    """,
]


def _ensure_columns(con: duckdb.DuckDBPyConnection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing:
            con.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def init_database(db_path: str = DB_PATH) -> None:
    """Create all tables (idempotent — safe to re-run)."""
    con = duckdb.connect(db_path)
    try:
        for ddl in DDL_STATEMENTS:
            con.execute(ddl)
        _ensure_columns(
            con,
            "sjt_item_bank",
            {
                "source_version": "VARCHAR",
                "transform_level": "VARCHAR",
                "review_status": "VARCHAR",
                "lineage_json": "VARCHAR",
            },
        )
        _ensure_columns(
            con,
            "sjt_weights",
            {
                "source_version": "VARCHAR",
                "review_status": "VARCHAR",
                "lineage_json": "VARCHAR",
            },
        )
        _ensure_columns(
            con,
            "sjt_consistency_rules",
            {
                "source_version": "VARCHAR",
                "review_status": "VARCHAR",
                "lineage_json": "VARCHAR",
            },
        )
        print(f"[init_db] ✅ All 4 tables created/verified in: {db_path}")

        # Quick sanity check
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        print(f"[init_db]    Tables present: {[t[0] for t in tables]}")
    finally:
        con.close()


if __name__ == "__main__":
    init_database()
