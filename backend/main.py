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

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import DB_PATH, CORS_ORIGINS, API_HOST, API_PORT
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


# ═══════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "db_path": DB_PATH}


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
