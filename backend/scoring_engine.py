"""
scoring_engine.py — The Rule-Model-Strategy three-layer scoring engine.

Implements the blueprint's core SQL pipeline:
  1. Flatten JSON answers  (CTE: flattened_answers)
  2. Model Layer — extract inherited weights from mother-template (CTE: base_scores)
  3. Rule Layer — detect contradictions & generate penalties  (CTE: penalty_scores)
  4. Strategy Layer — aggregate final scores per dimension     (final SELECT)

All scoring is pure SQL executed inside DuckDB — zero application-layer loops.
"""
import duckdb
from typing import Any
from backend.config import DB_PATH
from backend.models import DimensionScore, ReportResponse


# ═══════════════════════════════════════════════════════════════════
# Core scoring SQL — directly from the blueprint with minor tweaks
# for DuckDB 1.x compatibility (json_each instead of UNNEST/from_json)
# ═══════════════════════════════════════════════════════════════════

SCORING_SQL = """
WITH flattened_answers AS (
    -- 1. 解包：展平用户的 JSON 答案
    SELECT
        r.submission_id,
        j.key   AS sjt_q_id,
        j.value AS option_val
    FROM sjt_responses r,
         LATERAL (
             SELECT unnest(json_keys(r.raw_answers))  AS key,
                    unnest(json_extract_string(r.raw_answers, json_keys(r.raw_answers))) AS value
         ) j
    WHERE r.submission_id = $1
),
base_scores AS (
    -- 2. 模型层映射：提取底层基础参数
    SELECT
        w.dimension_code,
        SUM(w.inherited_weight) AS score
    FROM flattened_answers fa
    JOIN sjt_weights w
      ON fa.sjt_q_id  = w.sjt_q_id
     AND fa.option_val = w.option_val
    GROUP BY w.dimension_code
),
penalty_scores AS (
    -- 3. 规则层判定：激活测谎与惩罚中间参数
    SELECT
        cr.penalty_dimension AS dimension_code,
        SUM(cr.penalty_weight) AS score
    FROM sjt_consistency_rules cr
    JOIN flattened_answers fa_trigger
      ON fa_trigger.sjt_q_id  = cr.trigger_q_id
     AND fa_trigger.option_val = cr.trigger_option
    JOIN flattened_answers fa_verify
      ON fa_verify.sjt_q_id  = cr.verify_q_id
     AND fa_verify.option_val = cr.expected_option
    GROUP BY cr.penalty_dimension
)
-- 4. 策略层：聚合输出最终打分
SELECT
    COALESCE(b.dimension_code, p.dimension_code) AS final_dimension,
    COALESCE(b.score, 0)                         AS base_score,
    COALESCE(p.score, 0)                         AS penalty_score,
    COALESCE(b.score, 0) + COALESCE(p.score, 0)  AS final_total_score
FROM base_scores b
FULL OUTER JOIN penalty_scores p
  ON b.dimension_code = p.dimension_code
ORDER BY final_total_score DESC;
"""

# Simpler fallback SQL using json_each (wider DuckDB compatibility)
SCORING_SQL_FALLBACK = """
WITH answer_keys AS (
    SELECT
        r.submission_id,
        unnest(json_keys(r.raw_answers)) AS sjt_q_id
    FROM sjt_responses r
    WHERE r.submission_id = $1
),
flattened_answers AS (
    SELECT
        ak.submission_id,
        ak.sjt_q_id,
        CAST(json_extract_string(r.raw_answers, '$.' || ak.sjt_q_id) AS VARCHAR) AS option_val
    FROM answer_keys ak
    JOIN sjt_responses r ON r.submission_id = ak.submission_id
),
base_scores AS (
    SELECT
        w.dimension_code,
        SUM(w.inherited_weight) AS score
    FROM flattened_answers fa
    JOIN sjt_weights w
      ON fa.sjt_q_id  = w.sjt_q_id
     AND fa.option_val = w.option_val
    GROUP BY w.dimension_code
),
penalty_scores AS (
    SELECT
        cr.penalty_dimension AS dimension_code,
        SUM(cr.penalty_weight) AS score
    FROM sjt_consistency_rules cr
    JOIN flattened_answers fa_trigger
      ON fa_trigger.sjt_q_id  = cr.trigger_q_id
     AND fa_trigger.option_val = cr.trigger_option
    JOIN flattened_answers fa_verify
      ON fa_verify.sjt_q_id  = cr.verify_q_id
     AND fa_verify.option_val = cr.expected_option
    GROUP BY cr.penalty_dimension
)
SELECT
    COALESCE(b.dimension_code, p.dimension_code) AS final_dimension,
    COALESCE(b.score, 0)                         AS base_score,
    COALESCE(p.score, 0)                         AS penalty_score,
    COALESCE(b.score, 0) + COALESCE(p.score, 0)  AS final_total_score
FROM base_scores b
FULL OUTER JOIN penalty_scores p
  ON b.dimension_code = p.dimension_code
ORDER BY final_total_score DESC;
"""


# ═══════════════════════════════════════════════════════════════════
# Python interface
# ═══════════════════════════════════════════════════════════════════

import os
import json

def _load_dimensions_config():
    config_path = os.path.join(os.path.dirname(__file__), "dimensions_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

DIMENSIONS_CONFIG = _load_dimensions_config()
HOLLAND_CODES = set(d["code"] for d in DIMENSIONS_CONFIG["holland"]["dimensions"])
MBTI_PAIRS = {p["name"]: tuple(p["codes"]) for p in DIMENSIONS_CONFIG["mbti"]["pairs"]}



def compute_report(submission_id: str, db_path: str = DB_PATH) -> ReportResponse:
    """
    Run the three-layer scoring engine and return a structured report.

    Args:
        submission_id: UUID string of the submission to score.
        db_path: Path to the DuckDB database.

    Returns:
        ReportResponse with per-dimension scores, Holland top-3, and MBTI type.
    """
    con = duckdb.connect(db_path, read_only=True)
    try:
        # Try primary SQL first, fall back if syntax issues
        try:
            rows = con.execute(SCORING_SQL, [submission_id]).fetchall()
        except Exception:
            rows = con.execute(SCORING_SQL_FALLBACK, [submission_id]).fetchall()

        # Build dimension scores
        dimensions: list[DimensionScore] = []
        for row in rows:
            dimensions.append(DimensionScore(
                dimension_code=row[0],
                base_score=float(row[1]),
                penalty_score=float(row[2]),
                final_score=float(row[3]),
            ))

        # Derive Holland top-3
        holland_scores = sorted(
            [d for d in dimensions if d.dimension_code in HOLLAND_CODES],
            key=lambda d: d.final_score,
            reverse=True,
        )
        holland_top3 = [d.dimension_code.replace("Holland_", "") for d in holland_scores[:3]]

        # Derive MBTI 4-letter type
        mbti_type = _derive_mbti_type(dimensions)

        # Generate Cross Insight (Strategy Layer Fusion)
        cross_insight = _generate_cross_insight(mbti_type, holland_top3)
        source_lineage = _load_source_lineage(con, submission_id)
        consistency_issues = _load_consistency_issues(con, submission_id)
        source_version = source_lineage.get("question_bank", {}).get("source_version", "")

        # Fetch recommended Chinese occupations from the local bridge. Try the
        # full Holland top-3 so a sparse bridge still returns useful matches.
        recommended_cn_occupations = []
        if holland_top3:
            try:
                placeholders = ", ".join(["?"] * len(holland_top3))
                occ_rows = con.execute(
                    f"""
                    SELECT occupation_code, occupation_name, primary_riasec
                    FROM cn_occupation_riasec_map
                    WHERE primary_riasec IN ({placeholders})
                    """,
                    holland_top3,
                ).fetchall()
                rank_order = {code: idx for idx, code in enumerate(holland_top3)}
                occ_rows = sorted(occ_rows, key=lambda row: (rank_order.get(row[2], 99), row[0]))[:5]
                for row in occ_rows:
                    recommended_cn_occupations.append({
                        "occupation_code": row[0],
                        "occupation_name": row[1],
                        "matched_riasec": row[2],
                    })
            except Exception:
                # Table might not exist yet if mapping script hasn't run
                pass

        return ReportResponse(
            submission_id=submission_id,
            source_version=source_version,
            dimensions=dimensions,
            holland_top3=holland_top3,
            mbti_type=mbti_type,
            cross_insight=cross_insight,
            recommended_cn_occupations=recommended_cn_occupations,
            consistency_issues=consistency_issues,
            source_lineage=source_lineage,
        )
    finally:
        con.close()


def _load_answers(con: duckdb.DuckDBPyConnection, submission_id: str) -> dict[str, str]:
    row = con.execute(
        "SELECT raw_answers FROM sjt_responses WHERE submission_id = ?",
        [submission_id],
    ).fetchone()
    if not row:
        return {}
    raw_answers = row[0]
    if isinstance(raw_answers, str):
        try:
            value = json.loads(raw_answers)
        except json.JSONDecodeError:
            return {}
    else:
        value = raw_answers
    if not isinstance(value, dict):
        return {}
    return {str(key): str(option) for key, option in value.items()}


def _json_loads(value: Any, fallback: Any) -> Any:
    if not value:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return fallback


def _load_source_lineage(con: duckdb.DuckDBPyConnection, submission_id: str) -> dict[str, Any]:
    answers = _load_answers(con, submission_id)
    if not answers:
        return {
            "service": "lifehack-holland",
            "scoring_engine": "rule_model_strategy_sql",
            "question_bank": {"answered_count": 0, "source_version": ""},
            "answered_items": [],
        }

    answered_items = []
    source_versions: set[str] = set()
    lineage_quality: set[str] = set()
    for q_id, option_val in answers.items():
        row = con.execute(
            """
            SELECT sjt_q_id, mother_source, mother_id, core_mechanism, scenario_text,
                   source_version, transform_level, review_status, lineage_json
            FROM sjt_item_bank
            WHERE sjt_q_id = ?
            """,
            [q_id],
        ).fetchone()
        if not row:
            continue
        weights = con.execute(
            """
            SELECT dimension_code, inherited_weight, source_version, review_status, lineage_json
            FROM sjt_weights
            WHERE sjt_q_id = ? AND option_val = ?
            ORDER BY dimension_code
            """,
            [q_id, option_val],
        ).fetchall()
        item_lineage = _json_loads(row[8], {})
        source_version = str(row[5] or item_lineage.get("source_version") or "")
        if source_version:
            source_versions.add(source_version)
        if item_lineage.get("lineage_quality"):
            lineage_quality.add(str(item_lineage["lineage_quality"]))
        answered_items.append({
            "question_id": row[0],
            "selected_option": option_val,
            "mother_source": row[1],
            "mother_id": row[2],
            "core_mechanism": row[3],
            "source_version": source_version,
            "transform_level": row[6] or item_lineage.get("transform_level"),
            "review_status": row[7] or item_lineage.get("review_status"),
            "weights": [
                {
                    "dimension_code": weight_row[0],
                    "inherited_weight": float(weight_row[1]),
                    "source_version": weight_row[2] or "",
                    "review_status": weight_row[3] or "",
                    "lineage": _json_loads(weight_row[4], {}),
                }
                for weight_row in weights
            ],
            "lineage": item_lineage,
        })

    version = ",".join(sorted(source_versions))
    return {
        "service": "lifehack-holland",
        "scoring_engine": "rule_model_strategy_sql",
        "question_bank": {
            "source_version": version,
            "answered_count": len(answered_items),
            "lineage_quality": sorted(lineage_quality),
        },
        "answered_items": answered_items,
    }


def _load_consistency_issues(con: duckdb.DuckDBPyConnection, submission_id: str) -> list[dict[str, Any]]:
    answers = _load_answers(con, submission_id)
    if not answers:
        return []
    rows = con.execute(
        """
        SELECT rule_id, trigger_q_id, trigger_option, verify_q_id, expected_option,
               penalty_dimension, penalty_weight, source_version, review_status, lineage_json
        FROM sjt_consistency_rules
        ORDER BY rule_id
        """
    ).fetchall()
    issues = []
    for row in rows:
        (
            rule_id,
            trigger_q,
            trigger_option,
            verify_q,
            expected_option,
            penalty_dimension,
            penalty_weight,
            source_version,
            review_status,
            lineage_json,
        ) = row
        if answers.get(trigger_q) == trigger_option and answers.get(verify_q) == expected_option:
            issues.append({
                "rule_id": rule_id,
                "trigger_q_id": trigger_q,
                "verify_q_id": verify_q,
                "penalty_dimension": penalty_dimension,
                "penalty_weight": float(penalty_weight),
                "source_version": source_version or "",
                "review_status": review_status or "",
                "lineage": _json_loads(lineage_json, {}),
            })
    return issues


def _derive_mbti_type(dimensions: list[DimensionScore]) -> str:
    """
    Derive a 4-letter MBTI type from dimension scores.
    For each pair (E/I, S/N, T/F, J/P), the higher-scoring letter wins.
    If a dimension is missing, default to the first letter of the pair.
    """
    dim_map = {d.dimension_code: d.final_score for d in dimensions}
    result = []
    for pair_name, (code_a, code_b) in MBTI_PAIRS.items():
        score_a = dim_map.get(code_a, 0.0)
        score_b = dim_map.get(code_b, 0.0)
        # Extract the letter after "MBTI_"
        letter_a = code_a.replace("MBTI_", "")
        letter_b = code_b.replace("MBTI_", "")
        result.append(letter_a if score_a >= score_b else letter_b)
    return "".join(result)


def _generate_cross_insight(mbti_type: str, holland_top3: list[str]) -> str:
    """
    Generate a dynamic insight message combining MBTI (Core Personality)
    and Holland (Vocational Task Interest).
    """
    if not mbti_type or not holland_top3:
        return "数据不足，无法生成交叉解读。"
        
    top_holland = holland_top3[0] if len(holland_top3) > 0 else "未知"
    
    insight = f"你是典型的 {mbti_type} 型人格。从认知内核来看，你拥有独特的思维偏好。"
    
    if "E" in mbti_type and top_holland in ["I", "R"]:
        insight += f" 有趣的是，虽然你性格外向喜欢互动，但在实际任务中你最偏好【{top_holland}型】（偏向独立研究或实操）。你可能适合‘技术布道者’或‘研发团队的外部连接者’。"
    elif "I" in mbti_type and top_holland in ["E", "S"]:
        insight += f" 值得注意的是，虽然你偏好内向和独立思考，但你的任务兴趣却集中在【{top_holland}型】（偏向人际互动）。你或许是一个极其敏锐的‘幕后军师’或‘一对一深度辅导者’。"
    elif "F" in mbti_type and top_holland in ["I", "C", "R"]:
        insight += f" 你的内核非常在乎他人的感受（F），但任务兴趣却落在高度理性的【{top_holland}型】。这种反差让你在冷冰冰的数据/系统领域里，拥有一种罕见的人文关怀能力。"
    elif "T" in mbti_type and top_holland in ["S", "A"]:
        insight += f" 你极其讲究逻辑和效率（T），但外在兴趣却指向了充满感性的【{top_holland}型】。你或许擅长用极度理性的手段，去解决复杂的社会关系或艺术设计问题。"
    else:
        insight += f" 你的内核特质与你在【{top_holland}型】任务上的浓厚兴趣达成了高度的自洽与统一。在这一领域，你能够非常自然地释放你的天赋潜力。"
        
    return insight
