"""
Configuration for the SJT Assessment Engine.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DATA_DIR = BACKEND_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
CONFIG_DIR = PROJECT_ROOT / "config"
GENERATED_DIR = DATA_DIR / "generated"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEED_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# ── DuckDB ─────────────────────────────────────────────────────────
DB_PATH = str(DATA_DIR / "holland.duckdb")

# ── Main Project Integration ───────────────────────────────────────
# Path to the main project's database (read-only access for crosswalk mapping)
MAIN_PROJECT_DB_PATH = os.getenv("MAIN_PROJECT_DB_PATH", str(PROJECT_ROOT.parent / "lifehack" / "backend" / "data" / "university.db"))

# ── Config Files ──────────────────────────────────────────────────
CAREER_RIASEC_RULES_PATH = CONFIG_DIR / "career_riasec_rules.json"
QUESTION_GENERATION_CONFIG_PATH = CONFIG_DIR / "question_generation.json"

# ── FastAPI ────────────────────────────────────────────────────────
API_HOST = os.getenv("SJT_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SJT_PORT", "8600"))

# ── CORS (allow Lifehack frontend) ─────────────────────────────────
CORS_ORIGINS = [
    "http://localhost:*",
    "http://127.0.0.1:*",
    "*",  # tighten in production
]

# ── Raw Data Mappings ──────────────────────────────────────────────
# O*NET encodes "First Interest High-Point" as numeric values. This map is
# stable source decoding, not business scoring policy.
RIASEC_MAP = {
    "1.00": "R", "2.00": "I", "3.00": "A",
    "4.00": "S", "5.00": "E", "6.00": "C",
    "1": "R", "2": "I", "3": "A", "4": "S", "5": "E", "6": "C"
}
