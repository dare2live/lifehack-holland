"""
main.py — FastAPI entry point for the SJT Assessment Engine.

Endpoints:
    POST /api/submit              — Save a SurveyJS answer JSON, return submission_id
    GET  /api/report/{id}         — Run scoring engine, return structured report
    GET  /api/questions           — Return question bank for SurveyJS dynamic loading
    GET  /api/health              — Health check
"""
import json
import uuid

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    allow_origins=["*"],
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
async def get_questions():
    """
    Return the question bank formatted for SurveyJS consumption.
    Includes scenario_text, options, and visibleIf rules for verification questions.
    """
    con = _get_db(read_only=True)
    try:
        # Fetch all items
        items = con.execute(
            "SELECT sjt_q_id, scenario_text, core_mechanism FROM sjt_item_bank ORDER BY sjt_q_id"
        ).fetchall()

        # Fetch options per question
        weights = con.execute(
            """
            SELECT sjt_q_id, option_val, dimension_code, inherited_weight
            FROM sjt_weights
            ORDER BY sjt_q_id, option_val
            """
        ).fetchall()

        # Fetch consistency rules for visibleIf logic
        rules = con.execute(
            "SELECT trigger_q_id, trigger_option, verify_q_id FROM sjt_consistency_rules"
        ).fetchall()

        # Build option map: {q_id: [{"val": "A", "dimensions": [...]}, ...]}
        option_map: dict = {}
        for w in weights:
            q_id, opt, dim, wt = w
            if q_id not in option_map:
                option_map[q_id] = {}
            if opt not in option_map[q_id]:
                option_map[q_id][opt] = []
            option_map[q_id][opt].append({"dimension": dim, "weight": wt})

        # Build visibleIf map: {verify_q_id: "trigger_q_id = trigger_option"}
        visible_map: dict = {}
        for r in rules:
            trigger_q, trigger_opt, verify_q = r
            visible_map[verify_q] = f"{{{trigger_q}}} = '{trigger_opt}'"

        # Assemble SurveyJS-compatible questions
        questions = []
        for item in items:
            q_id, scenario, mechanism = item
            opts = option_map.get(q_id, {})

            q = {
                "name": q_id,
                "title": scenario,
                "type": "radiogroup",
                "isRequired": True if q_id not in visible_map else False,
                "choices": [],
            }

            # Add visibleIf for verification questions
            if q_id in visible_map:
                q["visibleIf"] = visible_map[q_id]

            # Build choice list (hide dimension info from frontend)
            for opt_val in sorted(opts.keys()):
                q["choices"].append({
                    "value": opt_val,
                    "text": _get_option_text(q_id, opt_val),
                })

            questions.append(q)

        return {"questions": questions, "total": len(questions)}

    finally:
        con.close()


# ── Option text lookup (seed data descriptions) ───────────────────
# In production these would live in the DB; for now, hardcoded for seed data.

_OPTION_TEXTS = {
    "Q_Gala": {
        "A": "马上安抚前排焦躁的观众，让主持人临场互动拖延时间",
        "B": "立刻冲到总电闸处排查物理线路和保险丝",
        "C": "打电话叫有经验的学长来帮忙处理",
    },
    "Q_Gala_verify": {
        "X": "算了不求他了，自己直接冲上台暖场",
        "Y": "那就让灯光师放点背景音乐，大家安静等着吧",
        "Z": "转身去找音控组的同学一起排查问题",
    },
    "Q_Poster": {
        "A": "各做各的方案，明天让全班投票决定",
        "B": "主动约TA去奶茶店聊聊，找个折中方案",
        "C": "上网搜历年获奖海报的数据和风格来说服TA",
        "D": "算了，让TA做吧，我去忙别的事情",
    },
    "Q_Poster_verify": {
        "X": "尊重大家意见，就用TA的方案吧",
        "Y": "有点不服气，觉得他们不懂审美，但嘴上不说",
        "Z": "坚持提出修改意见，用对比图展示两种方案的优劣",
    },
}


def _get_option_text(q_id: str, opt_val: str) -> str:
    """Get human-readable option text for seed data."""
    return _OPTION_TEXTS.get(q_id, {}).get(opt_val, f"Option {opt_val}")

# ── Static files — serve frontend ──────────────────────────────────
from pathlib import Path
from fastapi.responses import RedirectResponse

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
