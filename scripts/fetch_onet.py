"""
fetch_onet.py — Download O*NET Database master files for Holland (RIASEC) weights.

According to the blueprint:
We need:
1. Interests.txt (Contains the RIASEC scale values for occupations)
2. Task Statements.txt (Contains the tasks for occupations, used as LLM prompt material)

Data Source: https://www.onetcenter.org/database.html
Current Version: 30.2
"""

import os
import urllib.request
import zipfile
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ONET_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "onet"

ONET_INTERESTS_URL = "https://www.onetcenter.org/dl_files/database/db_30_2_text/Interests.txt"
ONET_TASKS_URL = "https://www.onetcenter.org/dl_files/database/db_30_2_text/Task%20Statements.txt"

def download_file(url: str, dest_path: Path):
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        dest_path.write_bytes(response.read())
    print(f"✅ Saved to {dest_path} ({os.path.getsize(dest_path)} bytes)")

def fetch_onet_data():
    ONET_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    interests_path = ONET_DATA_DIR / "Interests.txt"
    tasks_path = ONET_DATA_DIR / "Task_Statements.txt"
    
    try:
        download_file(ONET_INTERESTS_URL, interests_path)
        download_file(ONET_TASKS_URL, tasks_path)
        print("\n🎉 O*NET master data successfully fetched!")
        print("Next step (Phase 4): Use `llm_translate.py` to pass these statements to the LLM to generate SJT scenarios.")
    except Exception as e:
        print(f"❌ Failed to fetch O*NET data: {e}")

if __name__ == "__main__":
    fetch_onet_data()
