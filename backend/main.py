"""
main.py — FastAPI entry point for the SJT Assessment Engine.

Endpoints:
    POST /api/submit              — Save a SurveyJS answer JSON, return submission_id
    GET  /api/report/{id}         — Run scoring engine, return structured report
    GET  /api/questions           — Return question bank for SurveyJS dynamic loading
    GET  /api/health              — Health check
"""
import uuid
import json
from pathlib import Path
from typing import Any, Optional

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import DB_PATH, CORS_ORIGINS, API_HOST, API_PORT, CORE_READINESS_CONFIG_PATH
from backend.models import SubmitRequest, SubmitResponse, ReportResponse
from backend.scoring_engine import compute_report
from backend.init_db import init_database

# ── App setup ──────────────────────────────────────────────────────

app = FastAPI(
    title="SJT Assessment Engine",
    description="双核生涯测评引擎 — MBTI + Holland integrated situational judgement test",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup event ─────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Ensure DB tables exist on startup."""
    init_database()


# ── Helper ─────────────────────────────────────────────────────────

def _get_db(read_only: bool = False):
    return duckdb.connect(DB_PATH, read_only=read_only)


DEFAULT_CORE_READINESS = {
    "version": "fallback",
    "minimums": {
        "production_questions": 1,
        "options": 1,
        "consistency_rules": 1,
        "occupation_bridge_rows": 1,
    },
    "report_required_fields": [
        "submission_id",
        "source_version",
        "dimensions",
        "holland_top3",
        "mbti_type",
        "cross_insight",
        "recommended_cn_occupations",
        "consistency_issues",
        "source_lineage",
        "decision_inputs",
    ],
}


def _load_core_readiness_config() -> tuple[dict[str, Any], Optional[str]]:
    config = {
        **DEFAULT_CORE_READINESS,
        "minimums": dict(DEFAULT_CORE_READINESS["minimums"]),
        "report_required_fields": list(DEFAULT_CORE_READINESS["report_required_fields"]),
    }
    try:
        with open(CORE_READINESS_CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        config.update({key: value for key, value in loaded.items() if key != "minimums"})
        config["minimums"].update(loaded.get("minimums", {}))
        return config, None
    except Exception as exc:
        return config, str(exc)


def _table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    return bool(
        con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()[0]
    )


def _table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    if not _table_exists(con, table_name):
        return set()
    return {
        row[1]
        for row in con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    }


def _approved_count(con: duckdb.DuckDBPyConnection, table_name: str) -> int:
    if not _table_exists(con, table_name):
        return 0
    if "review_status" in _table_columns(con, table_name):
        return int(
            con.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE lower(coalesce(review_status, '')) LIKE 'approved%'
                """
            ).fetchone()[0]
        )
    return int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _source_versions(con: duckdb.DuckDBPyConnection, table_name: str) -> list[str]:
    if "source_version" not in _table_columns(con, table_name):
        return []
    rows = con.execute(
        f"""
        SELECT DISTINCT source_version
        FROM {table_name}
        WHERE source_version IS NOT NULL
          AND trim(CAST(source_version AS VARCHAR)) <> ''
        ORDER BY source_version
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def _occupation_bridge_status(con: duckdb.DuckDBPyConnection, minimum_rows: int) -> dict[str, Any]:
    table_name = "cn_occupation_riasec_map"
    status: dict[str, Any] = {
        "table": table_name,
        "table_exists": False,
        "ready": False,
        "status": "missing",
        "mapped_count": 0,
        "minimum_required": minimum_rows,
        "source_versions": [],
        "riasec_codes": [],
    }
    if not _table_exists(con, table_name):
        return status

    columns = _table_columns(con, table_name)
    mapped_count = int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
    source_versions = _source_versions(con, table_name) if "source_version" in columns else []
    riasec_codes = []
    if "primary_riasec" in columns:
        riasec_codes = [
            str(row[0])
            for row in con.execute(
                f"""
                SELECT DISTINCT primary_riasec
                FROM {table_name}
                WHERE primary_riasec IS NOT NULL
                  AND trim(CAST(primary_riasec AS VARCHAR)) <> ''
                ORDER BY primary_riasec
                """
            ).fetchall()
        ]

    ready = mapped_count >= minimum_rows
    status.update({
        "table_exists": True,
        "ready": ready,
        "status": "ready" if ready else "insufficient_rows",
        "mapped_count": mapped_count,
        "source_versions": source_versions,
        "riasec_codes": riasec_codes,
    })
    return status


def _build_core_health_payload() -> dict[str, Any]:
    readiness_config, config_error = _load_core_readiness_config()
    minimums = readiness_config.get("minimums", {})
    db_status: dict[str, Any] = {
        "path": DB_PATH,
        "read": {"ok": False},
        "write": {"ok": False},
    }
    question_bank: dict[str, Any] = {
        "production_question_count": 0,
        "option_count": 0,
        "consistency_rule_count": 0,
        "source_version": "",
        "source_versions": [],
        "minimums": {
            "production_questions": minimums.get("production_questions", 0),
            "options": minimums.get("options", 0),
            "consistency_rules": minimums.get("consistency_rules", 0),
        },
    }
    occupation_bridge: dict[str, Any] = {
        "table": "cn_occupation_riasec_map",
        "table_exists": False,
        "ready": False,
        "status": "not_checked",
        "mapped_count": 0,
        "minimum_required": minimums.get("occupation_bridge_rows", 0),
        "source_versions": [],
        "riasec_codes": [],
    }

    try:
        con = _get_db(read_only=True)
        try:
            db_status["read"] = {"ok": True}
            question_bank["production_question_count"] = _approved_count(con, "sjt_item_bank")
            question_bank["option_count"] = _approved_count(con, "sjt_options")
            question_bank["consistency_rule_count"] = _approved_count(con, "sjt_consistency_rules")
            question_bank["source_versions"] = _source_versions(con, "sjt_item_bank")
            question_bank["source_version"] = ",".join(question_bank["source_versions"])
            occupation_bridge = _occupation_bridge_status(
                con,
                int(minimums.get("occupation_bridge_rows", 0)),
            )
        finally:
            con.close()
    except Exception as exc:
        db_status["read"] = {"ok": False, "error": str(exc)}

    try:
        con = _get_db(read_only=False)
        try:
            con.execute("CREATE TEMP TABLE __holland_health_write_probe (ok INTEGER)")
            con.execute("INSERT INTO __holland_health_write_probe VALUES (1)")
            con.execute("SELECT COUNT(*) FROM __holland_health_write_probe").fetchone()
            db_status["write"] = {"ok": True}
        finally:
            con.close()
    except Exception as exc:
        db_status["write"] = {"ok": False, "error": str(exc)}

    checks = {
        "db_readable": bool(db_status["read"].get("ok")),
        "db_writable": bool(db_status["write"].get("ok")),
        "production_questions": question_bank["production_question_count"] >= int(minimums.get("production_questions", 0)),
        "options": question_bank["option_count"] >= int(minimums.get("options", 0)),
        "consistency_rules": question_bank["consistency_rule_count"] >= int(minimums.get("consistency_rules", 0)),
        "question_bank_source_version": bool(question_bank["source_versions"]),
        "occupation_bridge": bool(occupation_bridge.get("ready")),
    }
    ready_for_core = all(checks.values())
    payload = {
        "status": "ok",
        "service": "lifehack-holland",
        "ready_for_core": ready_for_core,
        "source_version": question_bank["source_version"],
        "checks": checks,
        "question_bank": question_bank,
        "db": db_status,
        "occupation_bridge": occupation_bridge,
        "readiness_config": {
            "version": readiness_config.get("version", ""),
            "path": str(CORE_READINESS_CONFIG_PATH),
        },
        "report_contract": {
            "endpoint": "/api/report/{submission_id}",
            "required_fields": readiness_config.get("report_required_fields", []),
        },
    }
    if config_error:
        payload["readiness_config"]["error"] = config_error
    return payload


# ═══════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Health check with the core handoff readiness contract."""
    return _build_core_health_payload()


@app.get("/api/config")
async def get_config():
    """Return the dimensions configuration (metadata, colors, text)."""
    import os
    import json
    config_path = os.path.join(os.path.dirname(__file__), "dimensions_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)



@app.post("/api/submit", response_model=SubmitResponse)
async def submit_answers(req: SubmitRequest):
    """
    Accept a flat JSON answer map from SurveyJS and persist it.
    Returns the generated submission_id.
    """
    submission_id = str(uuid.uuid4())
    con = _get_db()
    try:
        con.execute(
            """
            INSERT INTO sjt_responses (submission_id, user_id, raw_answers)
            VALUES (?, ?, ?)
            """,
            [submission_id, req.user_id, json.dumps(req.answers)],
        )
        return SubmitResponse(submission_id=submission_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save submission: {e}")
    finally:
        con.close()


@app.get("/api/report/{submission_id}", response_model=ReportResponse)
async def get_report(submission_id: str):
    """
    Run the three-layer scoring engine on a submission and return the report.
    """
    # Verify submission exists
    con = _get_db(read_only=True)
    try:
        exists = con.execute(
            "SELECT COUNT(*) FROM sjt_responses WHERE submission_id = ?",
            [submission_id],
        ).fetchone()[0]
        if not exists:
            raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found")
    finally:
        con.close()

    try:
        report = compute_report(submission_id)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring engine error: {e}")


@app.get("/api/questions")
async def get_questions(include_lineage: bool = False):
    """
    Return the question bank formatted for SurveyJS consumption.
    Includes scenario_text, options, and visibleIf rules for verification questions.
    """
    con = _get_db(read_only=True)
    try:
        # Fetch all items
        items = con.execute(
            """
            SELECT sjt_q_id, scenario_text, core_mechanism, mother_source, mother_id,
                   source_version, transform_level, review_status, lineage_json
            FROM sjt_item_bank
            ORDER BY sjt_q_id
            """
        ).fetchall()

        # Fetch reviewed option text per question.
        option_rows = con.execute(
            """
            SELECT sjt_q_id, option_val, option_text, source_version, review_status, lineage_json
            FROM sjt_options
            ORDER BY sjt_q_id, option_val
            """
        ).fetchall()

        # Fetch option scoring rows per question.
        weights = con.execute(
            """
            SELECT sjt_q_id, option_val, dimension_code, inherited_weight,
                   source_version, review_status, lineage_json
            FROM sjt_weights
            ORDER BY sjt_q_id, option_val
            """
        ).fetchall()

        # Fetch consistency rules for visibleIf logic
        rules = con.execute(
            "SELECT trigger_q_id, trigger_option, verify_q_id FROM sjt_consistency_rules"
        ).fetchall()

        option_map: dict = {}
        for row in option_rows:
            q_id, opt, text, source_version, review_status, lineage_json = row
            option_map.setdefault(q_id, {})[opt] = {
                "text": text,
                "source_version": source_version or "",
                "review_status": review_status or "",
                "lineage": _json_loads(lineage_json, {}),
            }

        weight_map: dict = {}
        for w in weights:
            q_id, opt, dim, wt, source_version, review_status, lineage_json = w
            if q_id not in weight_map:
                weight_map[q_id] = {}
            if opt not in weight_map[q_id]:
                weight_map[q_id][opt] = []
            weight_payload = {"dimension": dim, "weight": wt}
            if include_lineage:
                weight_payload.update({
                    "source_version": source_version or "",
                    "review_status": review_status or "",
                    "lineage": _json_loads(lineage_json, {}),
                })
            weight_map[q_id][opt].append(weight_payload)

        # Build visibleIf map: {verify_q_id: "trigger_q_id = trigger_option"}
        visible_map: dict = {}
        for r in rules:
            trigger_q, trigger_opt, verify_q = r
            visible_map[verify_q] = f"{{{trigger_q}}} = '{trigger_opt}'"

        # Assemble SurveyJS-compatible questions
        questions = []
        for item in items:
            (
                q_id,
                scenario,
                mechanism,
                mother_source,
                mother_id,
                source_version,
                transform_level,
                review_status,
                lineage_json,
            ) = item
            opts = option_map.get(q_id, {})
            option_weights = weight_map.get(q_id, {})
            option_values = sorted(set(opts.keys()) | set(option_weights.keys()))

            q = {
                "name": q_id,
                "title": scenario,
                "type": "radiogroup",
                "isRequired": True,
                "choices": [],
            }

            # Add visibleIf for verification questions
            if q_id in visible_map:
                q["visibleIf"] = visible_map[q_id]

            if include_lineage:
                q["source_version"] = source_version or ""
                q["transform_level"] = transform_level or ""
                q["review_status"] = review_status or ""
                q["lineage"] = {
                    "mother_source": mother_source,
                    "mother_id": mother_id,
                    "core_mechanism": mechanism,
                    **_json_loads(lineage_json, {}),
                }

            # Build choice list (hide dimension info from frontend)
            for opt_val in option_values:
                option_meta = opts.get(opt_val, {})
                choice = {
                    "value": opt_val,
                    "text": option_meta.get("text") or f"选项 {opt_val}",
                }
                if include_lineage:
                    choice["source_version"] = option_meta.get("source_version", "")
                    choice["review_status"] = option_meta.get("review_status", "")
                    choice["lineage"] = option_meta.get("lineage", {})
                    choice["weights"] = option_weights.get(opt_val, [])
                q["choices"].append(choice)

            questions.append(q)

        return {"questions": questions, "total": len(questions), "include_lineage": include_lineage}

    finally:
        con.close()

def _json_loads(value, fallback):
    if not value:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return fallback

# ── Static files — serve frontend ──────────────────────────────────

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@app.get("/")
async def root():
    """Redirect root to the survey page."""
    return RedirectResponse(url="/app/index.html")

app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ── Run with uvicorn ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)
