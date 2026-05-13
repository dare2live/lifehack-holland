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

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEED_DIR.mkdir(parents=True, exist_ok=True)

# ── DuckDB ─────────────────────────────────────────────────────────
DB_PATH = str(DATA_DIR / "holland.duckdb")

# ── FastAPI ────────────────────────────────────────────────────────
API_HOST = os.getenv("SJT_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SJT_PORT", "8600"))

# ── CORS (allow Lifehack frontend) ─────────────────────────────────
CORS_ORIGINS = [
    "http://localhost:*",
    "http://127.0.0.1:*",
    "*",  # tighten in production
]
